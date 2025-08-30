#!/usr/bin/env python3
"""
IMAP Server Discovery Script
Extracts domains from email lists and discovers IMAP servers with port scanning and banner grabbing.
"""

import dns.resolver
import socket
import ssl
import csv
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
import argparse

# Enhanced IMAP host patterns for different providers
IMAP_CANDIDATES = [
    "imap.{domain}",
    "mail.{domain}",
    "pop.{domain}",
    "imap.mail.{domain}",
    "secure.{domain}",
    "secureimap.{domain}",
    "imaps.{domain}",
    "mx.{domain}",
    "mx1.{domain}",
    "mx2.{domain}",
    "smtp.{domain}",
    "{domain}",
    "mail.{root}",
    "imap.{root}",
    "imap.mail.{root}",
    "webmail.{domain}",
    "exchange.{domain}",
    "outlook.{domain}",
    "office365.{domain}",
    # Common provider patterns
    "imap-mail.outlook.com",  # For outlook.com domains
    "outlook.office365.com",  # For custom domains on O365
    "imap.gmail.com",         # For gmail.com
    "imap.yahoo.com",         # For yahoo domains
    "imap.aol.com",           # For aol domains
    "imap.zoho.com",          # For zoho domains
    "mail.{mx_root}",         # Based on MX record root
    "imap.{mx_root}",         # Based on MX record root
]

# IMAP ports to test
IMAP_PORTS = [143, 993, 110, 995, 25, 587, 465]  # Added POP3 and SMTP for completeness

class IMAPDiscovery:
    def __init__(self, timeout=5, max_workers=50):
        self.timeout = timeout
        self.max_workers = max_workers
        self.results = []
        
    def extract_domains_from_file(self, filename):
        """Extract unique domains from email:password file"""
        domains = set()
        try:
            with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if ':' in line and '@' in line:
                        email = line.split(':')[0].strip()
                        if '@' in email:
                            domain = email.split('@')[1].lower()
                            # Skip obviously fake or invalid domains
                            if domain and '.' in domain and len(domain) > 3:
                                domains.add(domain)
        except Exception as e:
            print(f"[!] Error reading {filename}: {e}")
        return sorted(list(domains))
    
    def get_root_domain(self, hostname):
        """Extract root domain from hostname (e.g. aspmx.l.google.com -> google.com)"""
        parts = hostname.strip('.').split('.')
        if len(parts) >= 2:
            return ".".join(parts[-2:])
        return hostname
    
    def find_mx(self, domain):
        """Get MX records for a domain"""
        try:
            answers = dns.resolver.resolve(domain, 'MX')
            mx_records = sorted([(r.preference, str(r.exchange).strip('.')) for r in answers])
            return [mx for _, mx in mx_records]
        except Exception as e:
            print(f"[!] No MX for {domain}: {e}")
            return []
    
    def get_server_banner(self, host, port):
        """Get server banner to identify IMAP server type"""
        try:
            if port in [993, 995, 465]:  # SSL ports
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                with socket.create_connection((host, port), timeout=self.timeout) as sock:
                    with context.wrap_socket(sock, server_hostname=host) as ssock:
                        banner = ssock.recv(1024).decode('utf-8', errors='ignore').strip()
                        return banner
            else:
                with socket.create_connection((host, port), timeout=self.timeout) as sock:
                    banner = sock.recv(1024).decode('utf-8', errors='ignore').strip()
                    return banner
        except Exception as e:
            return f"Error: {str(e)}"
    
    def check_imap_server(self, host):
        """Check which ports are open and get server info"""
        results = []
        for port in IMAP_PORTS:
            try:
                with socket.create_connection((host, port), timeout=self.timeout):
                    banner = self.get_server_banner(host, port)
                    service_type = self.identify_service_type(port, banner)
                    results.append({
                        'port': port,
                        'banner': banner,
                        'service': service_type
                    })
            except:
                continue
        return results
    
    def identify_service_type(self, port, banner):
        """Identify service type based on port and banner"""
        banner_lower = banner.lower()
        
        if port in [143, 993]:
            return "IMAP"
        elif port in [110, 995]:
            return "POP3"
        elif port in [25, 587, 465]:
            return "SMTP"
        
        # Try to identify from banner
        if 'imap' in banner_lower:
            return "IMAP"
        elif 'pop' in banner_lower:
            return "POP3"
        elif 'smtp' in banner_lower:
            return "SMTP"
        else:
            return "Unknown"
    
    def test_single_host(self, host):
        """Test a single host for IMAP services"""
        try:
            # Resolve hostname first
            socket.gethostbyname(host)
            services = self.check_imap_server(host)
            if services:
                return host, services
        except:
            pass
        return None
    
    def discover_imap_for_domain(self, domain):
        """Discover IMAP servers for a single domain"""
        print(f"🔎 Discovering IMAP for {domain}...")
        
        # Get MX records
        mx_hosts = self.find_mx(domain)
        mx_roots = [self.get_root_domain(mx) for mx in mx_hosts]
        
        # Generate candidates
        candidates = set()
        
        # Domain-based patterns
        for pattern in IMAP_CANDIDATES:
            if '{domain}' in pattern:
                candidates.add(pattern.format(domain=domain))
            if '{root}' in pattern:
                root = self.get_root_domain(domain)
                candidates.add(pattern.format(root=root))
            if '{mx_root}' in pattern:
                for mx_root in mx_roots:
                    candidates.add(pattern.format(mx_root=mx_root))
        
        # Add MX hosts directly
        candidates.update(mx_hosts)
        
        # Add common provider-specific patterns
        if 'gmail.com' in domain or any('google' in mx for mx in mx_hosts):
            candidates.add('imap.gmail.com')
        if 'yahoo.com' in domain or any('yahoo' in mx for mx in mx_hosts):
            candidates.add('imap.mail.yahoo.com')
        if 'outlook.com' in domain or 'hotmail.com' in domain:
            candidates.add('imap-mail.outlook.com')
        if any('outlook' in mx or 'office365' in mx for mx in mx_hosts):
            candidates.add('outlook.office365.com')
        
        # Test candidates with threading
        results = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_host = {executor.submit(self.test_single_host, host): host 
                            for host in candidates}
            
            for future in as_completed(future_to_host):
                result = future.result()
                if result:
                    host, services = result
                    for service in services:
                        results.append({
                            'domain': domain,
                            'imap_host': host,
                            'port': service['port'],
                            'service': service['service'],
                            'banner': service['banner'],
                            'mx_records': mx_hosts
                        })
        
        if results:
            print(f"✅ Found {len(results)} services for {domain}")
            for r in results:
                print(f"   {r['imap_host']}:{r['port']} ({r['service']}) - {r['banner'][:50]}...")
        else:
            print(f"❌ No IMAP services found for {domain}")
        
        return results
    
    def discover_all_domains(self, domains):
        """Discover IMAP for all domains with threading"""
        print(f"🚀 Starting IMAP discovery for {len(domains)} domains...")
        
        all_results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_domain = {executor.submit(self.discover_imap_for_domain, domain): domain 
                              for domain in domains}
            
            for future in as_completed(future_to_domain):
                domain = future_to_domain[future]
                try:
                    results = future.result()
                    all_results.extend(results)
                except Exception as e:
                    print(f"[!] Error processing {domain}: {e}")
        
        self.results = all_results
        return all_results
    
    def save_results(self, csv_file=None, json_file=None):
        """Save results to CSV and/or JSON"""
        if csv_file:
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                if self.results:
                    writer = csv.DictWriter(f, fieldnames=self.results[0].keys())
                    writer.writeheader()
                    writer.writerows(self.results)
            print(f"✅ Results saved to {csv_file}")
        
        if json_file:
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, indent=2, ensure_ascii=False)
            print(f"✅ Results saved to {json_file}")
    
    def print_summary(self):
        """Print summary of discovered services"""
        if not self.results:
            print("❌ No IMAP services discovered")
            return
        
        print(f"\n📊 DISCOVERY SUMMARY")
        print(f"Total services found: {len(self.results)}")
        
        # Group by domain
        by_domain = defaultdict(list)
        for r in self.results:
            by_domain[r['domain']].append(r)
        
        print(f"Domains with services: {len(by_domain)}")
        
        # Service type breakdown
        by_service = defaultdict(int)
        for r in self.results:
            by_service[r['service']] += 1
        
        print("\nService types:")
        for service, count in by_service.items():
            print(f"  {service}: {count}")
        
        # Top providers by banner
        print(f"\nTop 10 domains with most services:")
        sorted_domains = sorted(by_domain.items(), key=lambda x: len(x[1]), reverse=True)[:10]
        for domain, services in sorted_domains:
            print(f"  {domain}: {len(services)} services")

def main():
    parser = argparse.ArgumentParser(description='IMAP Server Discovery Tool')
    parser.add_argument('--input', '-i', nargs='+', default=['Successfully 8.txt', 'Successfully 9.txt'],
                       help='Input files containing email:password lists')
    parser.add_argument('--csv', '-c', default='imap_discovery_results.csv',
                       help='Output CSV file')
    parser.add_argument('--json', '-j', default='imap_discovery_results.json',
                       help='Output JSON file')
    parser.add_argument('--timeout', '-t', type=int, default=5,
                       help='Connection timeout in seconds')
    parser.add_argument('--workers', '-w', type=int, default=50,
                       help='Maximum worker threads')
    parser.add_argument('--domains-only', action='store_true',
                       help='Only extract and show unique domains')
    
    args = parser.parse_args()
    
    # Initialize discovery tool
    discovery = IMAPDiscovery(timeout=args.timeout, max_workers=args.workers)
    
    # Extract domains from all input files
    all_domains = set()
    for input_file in args.input:
        print(f"📂 Extracting domains from {input_file}...")
        domains = discovery.extract_domains_from_file(input_file)
        all_domains.update(domains)
        print(f"   Found {len(domains)} domains")
    
    unique_domains = sorted(list(all_domains))
    print(f"\n📋 Total unique domains: {len(unique_domains)}")
    
    if args.domains_only:
        print("\nUnique domains:")
        for domain in unique_domains:
            print(f"  {domain}")
        return
    
    # Discover IMAP servers
    start_time = time.time()
    discovery.discover_all_domains(unique_domains)
    end_time = time.time()
    
    print(f"\n⏱️  Discovery completed in {end_time - start_time:.2f} seconds")
    
    # Save results
    discovery.save_results(csv_file=args.csv, json_file=args.json)
    
    # Print summary
    discovery.print_summary()

if __name__ == "__main__":
    main()
