#!/usr/bin/env python3
"""
Email IMAP Configuration Finder
Processes individual email addresses and finds working IMAP server configurations.
"""

import dns.resolver
import socket
import ssl
import csv
import imaplib
import time
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse

# Common IMAP host patterns
IMAP_PATTERNS = [
    "imap.{domain}",
    "mail.{domain}",
    "imap.mail.{domain}",
    "secure.{domain}",
    "secureimap.{domain}",
    "imaps.{domain}",
    "{domain}",
    "webmail.{domain}",
    "exchange.{domain}",
    "outlook.{domain}",
    # Provider-specific patterns
    "imap.gmail.com",
    "imap-mail.outlook.com",
    "outlook.office365.com", 
    "imap.mail.yahoo.com",
    "imap.yahoo.com",
    "imap.aol.com",
    "imap.zoho.com",
    "imap.{mx_root}",
    "mail.{mx_root}"
]

# IMAP ports to test (prioritize secure ports)
IMAP_PORTS = [993, 143]  # Focus on IMAP only

class EmailIMAPFinder:
    def __init__(self, timeout=10, connection_timeout=5):
        self.timeout = timeout
        self.connection_timeout = connection_timeout
        self.results = []
        
    def extract_emails_from_file(self, filename):
        """Extract email addresses from email:password file"""
        emails = []
        try:
            # Check if file exists
            if not os.path.exists(filename):
                print(f"[!] File not found: {filename}")
                return []
            
            # Try different encodings
            encodings = ['utf-8', 'latin-1', 'cp1252']
            file_content = None
            
            for encoding in encodings:
                try:
                    with open(filename, 'r', encoding=encoding) as f:
                        file_content = f.read()
                    break
                except UnicodeDecodeError:
                    continue
            
            if file_content is None:
                print(f"[!] Could not decode file {filename} with any supported encoding")
                return []
            
            # Process lines
            for line_num, line in enumerate(file_content.split('\n'), 1):
                line = line.strip()
                if ':' in line and '@' in line:
                    email = line.split(':')[0].strip()
                    if '@' in email and '.' in email:
                        emails.append(email.lower())
                        
        except Exception as e:
            print(f"[!] Error reading {filename}: {e}")
            import traceback
            traceback.print_exc()
        return emails
    
    def get_domain(self, email):
        """Extract domain from email"""
        return email.split('@')[1]
    
    def get_root_domain(self, hostname):
        """Extract root domain from hostname"""
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
        except Exception:
            return []
    
    def test_imap_connection(self, host, port, email=None):
        """Test actual IMAP connection to verify server works"""
        try:
            if port == 993:
                # SSL connection
                with imaplib.IMAP4_SSL(host, port, timeout=self.connection_timeout) as imap:
                    # Just check if we can connect and get greeting
                    return True
            else:
                # Non-SSL connection
                with imaplib.IMAP4(host, port, timeout=self.connection_timeout) as imap:
                    return True
        except Exception as e:
            return False
    
    def check_port_open(self, host, port):
        """Quick port connectivity check"""
        try:
            with socket.create_connection((host, port), timeout=self.timeout):
                return True
        except:
            return False
    
    def find_imap_for_email(self, email):
        """Find working IMAP configuration for a specific email"""
        domain = self.get_domain(email)
        print(f"🔍 Finding IMAP for {email} (domain: {domain})")
        
        # Get MX records for additional patterns
        mx_hosts = self.find_mx(domain)
        mx_roots = [self.get_root_domain(mx) for mx in mx_hosts] if mx_hosts else []
        
        # Generate IMAP server candidates (prioritized order)
        candidates = []
        
        # Add provider-specific patterns first (most likely to work)
        if 'gmail.com' in domain or any('google' in str(mx).lower() for mx in mx_hosts):
            candidates.append('imap.gmail.com')
        
        if any(x in domain for x in ['outlook.com', 'hotmail.com', 'live.com']):
            candidates.extend(['imap-mail.outlook.com', 'outlook.office365.com'])
            
        if any('outlook' in str(mx).lower() or 'office365' in str(mx).lower() for mx in mx_hosts):
            candidates.extend(['outlook.office365.com', 'imap-mail.outlook.com'])
            
        if 'yahoo' in domain or any('yahoo' in str(mx).lower() for mx in mx_hosts):
            candidates.extend(['imap.mail.yahoo.com', 'imap.yahoo.com'])
            
        if 'aol.com' in domain:
            candidates.append('imap.aol.com')
            
        if 'zoho.com' in domain or any('zoho' in str(mx).lower() for mx in mx_hosts):
            candidates.append('imap.zoho.com')
        
        # Add common patterns
        candidates.extend([
            f"imap.{domain}",
            f"mail.{domain}",
            f"imap.mail.{domain}",
            domain
        ])
        
        # Add MX-based patterns
        for mx_root in mx_roots:
            candidates.extend([f"imap.{mx_root}", f"mail.{mx_root}"])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_candidates = []
        for candidate in candidates:
            if candidate not in seen:
                seen.add(candidate)
                unique_candidates.append(candidate)
        
        # Test each candidate - prioritize SSL port 993
        working_configs = []
        
        for host in unique_candidates:
            # Try SSL first (993), then non-SSL (143)
            for port in [993, 143]:
                try:
                    # First check if port is open
                    if self.check_port_open(host, port):
                        # Then test actual IMAP connection
                        if self.test_imap_connection(host, port, email):
                            working_configs.append({
                                'email': email,
                                'domain': domain,
                                'imap_server': host,
                                'port': port,
                                'mx_records': mx_hosts
                            })
                            print(f"  ✅ {host}:{port} - Connection successful")
                            # Found working config, stop testing this host
                            break
                except Exception as e:
                    continue
            
            # If we found a working config for this email, we can stop
            if working_configs:
                break
        
        if not working_configs:
            print(f"  ❌ No working IMAP configuration found for {email}")
            # Still add entry with empty IMAP info for tracking
            working_configs.append({
                'email': email,
                'domain': domain,
                'imap_server': '',
                'port': '',
                'mx_records': mx_hosts
            })
        
        return working_configs
    
    def process_emails(self, emails, max_workers=200):
        """Process multiple emails with threading"""
        print(f"🚀 Processing {len(emails)} email addresses...")
        
        all_results = []
        processed = 0
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_email = {
                executor.submit(self.find_imap_for_email, email): email 
                for email in emails
            }
            
            # Process results as they complete
            for future in as_completed(future_to_email):
                email = future_to_email[future]
                try:
                    results = future.result()
                    all_results.extend(results)
                    processed += 1
                    
                    if processed % 10 == 0:
                        print(f"📊 Processed {processed}/{len(emails)} emails...")
                        
                except Exception as e:
                    print(f"[!] Error processing {email}: {e}")
                    # Add failed entry
                    all_results.append({
                        'email': email,
                        'domain': self.get_domain(email),
                        'imap_server': 'ERROR',
                        'port': '',
                        'mx_records': []
                    })
                    processed += 1
        
        self.results = all_results
        return all_results
    
    def save_results(self, csv_file):
        """Save results to CSV file with specified columns"""
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            # Define exact columns requested
            fieldnames = ['email', 'domain', 'imap_server', 'port']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for result in self.results:
                # Write only the requested columns
                writer.writerow({
                    'email': result['email'],
                    'domain': result['domain'], 
                    'imap_server': result['imap_server'],
                    'port': result['port']
                })
        
        print(f"✅ Results saved to {csv_file}")
    
    def print_summary(self):
        """Print summary of results"""
        if not self.results:
            print("❌ No results to summarize")
            return
            
        total = len(self.results)
        successful = len([r for r in self.results if r['imap_server'] and r['imap_server'] != 'ERROR'])
        failed = total - successful
        
        print(f"\n📊 PROCESSING SUMMARY")
        print(f"Total emails processed: {total}")
        print(f"Successful IMAP configs: {successful}")
        print(f"Failed/No config found: {failed}")
        print(f"Success rate: {(successful/total*100):.1f}%")
        
        # Show breakdown by port
        if successful > 0:
            port_counts = {}
            for r in self.results:
                if r['port'] and r['port'] != '':
                    port_counts[r['port']] = port_counts.get(r['port'], 0) + 1
            
            print(f"\nPort distribution:")
            for port, count in sorted(port_counts.items()):
                print(f"  Port {port}: {count} configs")
        
        # Show top domains
        domain_counts = {}
        for r in self.results:
            if r['imap_server'] and r['imap_server'] != 'ERROR':
                domain_counts[r['domain']] = domain_counts.get(r['domain'], 0) + 1
        
        if domain_counts:
            print(f"\nTop 10 domains with working configs:")
            sorted_domains = sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            for domain, count in sorted_domains:
                print(f"  {domain}: {count} configs")

def main():
    parser = argparse.ArgumentParser(description='Email IMAP Configuration Finder')
    parser.add_argument('--input', '-i', default='Successfully 8.txt',
                       help='Input file containing email:password list')
    parser.add_argument('--output', '-o', default='email_imap_configs.csv',
                       help='Output CSV file')
    parser.add_argument('--timeout', '-t', type=int, default=10,
                       help='Connection timeout in seconds')
    parser.add_argument('--workers', '-w', type=int, default=200,
                       help='Maximum worker threads')
    parser.add_argument('--limit', '-l', type=int, 
                       help='Limit number of emails to process (for testing)')
    
    args = parser.parse_args()
    
    # Initialize finder
    finder = EmailIMAPFinder(timeout=args.timeout)
    
    # Extract emails
    print(f"📂 Reading emails from {args.input}...")
    emails = finder.extract_emails_from_file(args.input)
    
    if not emails:
        print("❌ No valid emails found in input file")
        return 1
    
    # Apply limit if specified
    if args.limit:
        emails = emails[:args.limit]
        print(f"📋 Limited to first {len(emails)} emails for testing")
    else:
        print(f"📋 Found {len(emails)} emails to process")
    
    # Process emails
    start_time = time.time()
    finder.process_emails(emails, max_workers=args.workers)
    end_time = time.time()
    
    print(f"\n⏱️  Processing completed in {end_time - start_time:.2f} seconds")
    
    # Save results
    finder.save_results(args.output)
    
    # Print summary
    finder.print_summary()
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
