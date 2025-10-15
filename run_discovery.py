#!/usr/bin/env python3
"""
Simple script to run IMAP discovery on your email lists
"""

import subprocess
import sys
import os

def main():
    print("🚀 IMAP Server Discovery Tool")
    print("=" * 50)
    
    # Check if required files exist
    input_files = ['Successfully 8.txt', 'Successfully 9.txt']
    missing_files = [f for f in input_files if not os.path.exists(f)]
    
    if missing_files:
        print(f"❌ Missing input files: {missing_files}")
        return 1
    
    print(f"📂 Found input files: {input_files}")
    
    # Ask user for confirmation
    print("\nOptions:")
    print("1. Quick test (extract domains only)")
    print("2. Full discovery (may take 30+ minutes)")
    print("3. Custom discovery with settings")
    
    choice = input("\nSelect option (1-3): ").strip()
    
    if choice == "1":
        # Quick domain extraction
        cmd = ["python", "imap_discovery.py", "--domains-only"]
        
    elif choice == "2":
        # Full discovery with default settings
        cmd = ["python", "imap_discovery.py"]
        
    elif choice == "3":
        # Custom settings
        timeout = input("Connection timeout (default 5): ").strip() or "5"
        workers = input("Worker threads (default 200): ").strip() or "200"
        csv_file = input("CSV output file (default imap_discovery_results.csv): ").strip() or "imap_discovery_results.csv"
        
        cmd = [
            "python", "imap_discovery.py",
            "--timeout", timeout,
            "--workers", workers,
            "--csv", csv_file,
            "--json", csv_file.replace('.csv', '.json')
        ]
    else:
        print("❌ Invalid option selected")
        return 1
    
    print(f"\n🏃 Running: {' '.join(cmd)}")
    print("Press Ctrl+C to stop\n")
    
    try:
        # Run the discovery
        result = subprocess.run(cmd, check=True)
        print("\n✅ Discovery completed successfully!")
        
        if choice != "1":
            print("\n📊 Check the output files for results:")
            print("  - imap_discovery_results.csv")
            print("  - imap_discovery_results.json")
            
    except KeyboardInterrupt:
        print("\n⚠️  Discovery interrupted by user")
        return 1
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Discovery failed with error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
