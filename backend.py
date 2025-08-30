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
        
        # Get processing parameters
        timeout = int(request.form.get('timeout', 5))
        workers = int(request.form.get('workers', 20))
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
        
        # Process emails with progress tracking (no file operations)
        results = process_emails_with_progress_simple(emails, passwords, process_id, timeout)
        
        # Calculate statistics
        successful = len([r for r in results if r.get('imap_server') and r.get('status') == 'success'])
        failed = total_emails - successful
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
                    'failed': failed,
                    'success_rate': round(success_rate, 1)
                }
            })
            
    except Exception as e:
        print(f"Processing error: {e}")
        with processing_lock:
            processing_status[process_id]['status'] = 'error'
            processing_status[process_id]['error'] = f'Processing error: {str(e)}'

def process_emails_with_progress_simple(emails, passwords, process_id, timeout):
    """Process emails with progress updates - simplified version without file operations"""
    results = []
    
    for i, email in enumerate(emails):
        try:
            # Update progress
            progress = 10 + (i / len(emails)) * 80  # 10% to 90%
            with processing_lock:
                processing_status[process_id]['progress'] = int(progress)
                processing_status[process_id]['current_email'] = email
                processing_status[process_id]['processed'] = i
            
            # Find IMAP configuration for this email using simplified method
            domain = email.split('@')[1] if '@' in email else ''
            password = passwords.get(email, '')
            
            # Use simplified IMAP discovery to avoid file I/O issues
            found_config = find_imap_simple(email, domain, timeout)
            
            if found_config:
                results.append({
                    'email': email,
                    'domain': domain,
                    'imap_server': found_config['server'],
                    'port': found_config['port'],
                    'password': password,
                    'status': 'success'
                })
            else:
                # No configuration found
                results.append({
                    'email': email,
                    'domain': domain,
                    'imap_server': '',
                    'port': '',
                    'password': password,
                    'status': 'failed'
                })
                
        except Exception as e:
            # Handle individual email processing errors
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
            print(f"Error processing {email}: {e}")
    
    return results

def find_imap_simple(email, domain, timeout):
    """Simplified IMAP discovery without file operations"""
    
    # Generate candidates
    candidates = []
    
    # Add provider-specific patterns first
    if 'gmail.com' in domain:
        candidates.append('imap.gmail.com')
    elif any(x in domain for x in ['outlook.com', 'hotmail.com', 'live.com']):
        candidates.extend(['imap-mail.outlook.com', 'outlook.office365.com'])
    elif 'yahoo' in domain:
        candidates.extend(['imap.mail.yahoo.com', 'imap.yahoo.com'])
    elif 'aol.com' in domain:
        candidates.append('imap.aol.com')
    elif 'zoho.com' in domain:
        candidates.append('imap.zoho.com')
    
    # Add common patterns
    candidates.extend([
        f"imap.{domain}",
        f"mail.{domain}",
        f"imap.mail.{domain}",
        domain
    ])
    
    # Test candidates
    for host in candidates[:5]:  # Test only first 5 candidates
        for port in [993, 143]:  # Try SSL first, then non-SSL
            try:
                with socket.create_connection((host, port), timeout=timeout):
                    return {'server': host, 'port': port}
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
        
        # Get processing parameters
        timeout = int(data.get('timeout', 5))
        workers = int(data.get('workers', 20))
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
    
    app.run(debug=True, host='0.0.0.0', port=5000)


