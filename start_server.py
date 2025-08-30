#!/usr/bin/env python3
"""
Startup script for the IMAP Discovery Web Interface
"""

import os
import sys
import subprocess
import webbrowser
import time
import socket

def check_port(port):
    """Check if a port is available"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) != 0

def install_dependencies():
    """Install required dependencies"""
    print("📦 Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        print("✅ Dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        return False

def start_server():
    """Start the Flask server"""
    print("🚀 Starting IMAP Discovery Web Interface...")
    print("=" * 60)
    print("🌐 Professional Email Configuration Discovery Tool")
    print("📧 Drag & Drop Interface with Real-time Processing")
    print("🔍 Automatic IMAP Server Discovery & Testing")
    print("📊 Professional Results Display & Export")
    print("=" * 60)
    
    # Check if port is available
    port = 5000
    if not check_port(port):
        print(f"⚠️  Port {port} is already in use. Please stop other services or change the port.")
        input("Press Enter to continue anyway...")
    
    # Start server
    print(f"\n💻 Server starting at: http://localhost:{port}")
    print("🌐 Opening web browser automatically...")
    print("\n📋 Usage Instructions:")
    print("  1. Drag & drop your email:password .txt file")
    print("  2. Adjust processing settings if needed")
    print("  3. Click 'Discover IMAP Configurations'")
    print("  4. View results and export CSV")
    print("\n⚠️  Note: Processing may take several minutes for large files")
    print("🔒 All processing is done locally - your data stays private")
    print("\n" + "=" * 60)
    
    # Auto-open browser after a short delay
    def open_browser():
        time.sleep(2)
        webbrowser.open(f'http://localhost:{port}')
    
    import threading
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    # Start Flask app
    try:
        from backend import app
        app.run(debug=False, host='0.0.0.0', port=port)
    except KeyboardInterrupt:
        print("\n\n🛑 Server stopped by user")
        print("👋 Thank you for using IMAP Discovery Tool!")
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")
        print("💡 Make sure all dependencies are installed: pip install -r requirements.txt")

def main():
    """Main function"""
    print("🚀 IMAP Discovery Tool - Web Interface")
    print("=" * 50)
    
    # Check if requirements.txt exists
    if not os.path.exists('requirements.txt'):
        print("❌ requirements.txt not found!")
        print("💡 Make sure you're running this script from the project directory")
        return
    
    # Check if backend.py exists
    if not os.path.exists('backend.py'):
        print("❌ backend.py not found!")
        print("💡 Make sure all project files are present")
        return
    
    # Check if dependencies are installed
    try:
        import flask
        import flask_cors
        import dns.resolver
    except ImportError:
        print("📦 Some dependencies are missing. Installing...")
        if not install_dependencies():
            print("❌ Failed to install dependencies. Please run:")
            print("   pip install -r requirements.txt")
            return
    
    # Start the server
    start_server()

if __name__ == "__main__":
    main()
