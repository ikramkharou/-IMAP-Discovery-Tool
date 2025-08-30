# IMAP Server Discovery Tool

This tool automatically discovers IMAP servers for domains extracted from email lists by performing MX lookups, testing common IMAP host patterns, and port scanning.

## Features

- 🔍 **Domain Extraction**: Extracts unique domains from email:password lists
- 🌐 **MX Record Lookup**: Finds mail exchange servers for each domain
- 🎯 **Smart Host Discovery**: Tests comprehensive IMAP host patterns including provider-specific ones
- 🔓 **Port Scanning**: Tests multiple IMAP/POP3/SMTP ports (143, 993, 110, 995, 25, 587, 465)
- 🏷️ **Banner Grabbing**: Identifies server types (Dovecot, Exchange, etc.)
- 📊 **Multiple Output Formats**: Saves results to CSV and JSON
- ⚡ **Multi-threaded**: Fast concurrent processing
- 📈 **Detailed Reports**: Comprehensive discovery summaries

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage
```bash
python imap_discovery.py
```

This will:
1. Extract domains from `Successfully 8.txt` and `Successfully 9.txt`
2. Discover IMAP servers for all unique domains
3. Save results to `imap_discovery_results.csv` and `imap_discovery_results.json`

### Advanced Usage

```bash
# Custom input files
python imap_discovery.py -i file1.txt file2.txt

# Custom output files
python imap_discovery.py -c my_results.csv -j my_results.json

# Adjust performance settings
python imap_discovery.py --timeout 10 --workers 100

# Only extract and show domains (no discovery)
python imap_discovery.py --domains-only
```

### Command Line Options

- `--input, -i`: Input files containing email:password lists (default: Successfully 8.txt, Successfully 9.txt)
- `--csv, -c`: Output CSV file (default: imap_discovery_results.csv)
- `--json, -j`: Output JSON file (default: imap_discovery_results.json)
- `--timeout, -t`: Connection timeout in seconds (default: 5)
- `--workers, -w`: Maximum worker threads (default: 50)
- `--domains-only`: Only extract and display unique domains

## How It Works

### 1. Domain Extraction
- Parses email:password files
- Extracts unique domains from email addresses
- Filters out invalid/fake domains

### 2. MX Record Lookup
- Queries DNS for MX records of each domain
- Identifies primary mail servers
- Extracts root domains from MX hostnames

### 3. IMAP Host Discovery
Tests comprehensive patterns including:
- `imap.domain.com`
- `mail.domain.com`
- `imap.mail.domain.com`
- `outlook.office365.com` (for O365 domains)
- `imap.gmail.com` (for Google domains)
- And many more...

### 4. Port Scanning
Tests these ports for each candidate host:
- **143**: IMAP (unencrypted)
- **993**: IMAPS (SSL/TLS)
- **110**: POP3 (unencrypted)
- **995**: POP3S (SSL/TLS)
- **25**: SMTP
- **587**: SMTP (submission)
- **465**: SMTPS (SSL/TLS)

### 5. Banner Grabbing
- Connects to open ports
- Reads server banners to identify:
  - Server software (Dovecot, Exchange, etc.)
  - Service type (IMAP, POP3, SMTP)
  - SSL/TLS support

## Output Format

### CSV Output
Contains columns:
- `domain`: Original domain
- `imap_host`: Discovered IMAP server hostname
- `port`: Open port number
- `service`: Service type (IMAP, POP3, SMTP)
- `banner`: Server banner/response
- `mx_records`: List of MX records for the domain

### JSON Output
Same data in JSON format for programmatic processing.

## Example Output

```
🔎 Discovering IMAP for gmail.com...
✅ Found 2 services for gmail.com
   imap.gmail.com:993 (IMAP) - * OK Gimap ready for requests from 192.168.1.100...
   imap.gmail.com:143 (IMAP) - * OK Gimap ready for requests from 192.168.1.100...

📊 DISCOVERY SUMMARY
Total services found: 245
Domains with services: 89

Service types:
  IMAP: 156
  SMTP: 67
  POP3: 22

Top 10 domains with most services:
  gmail.com: 8 services
  outlook.com: 6 services
  yahoo.com: 5 services
```

## Performance Tips

- **Increase workers** (`--workers`) for faster processing on powerful machines
- **Decrease timeout** (`--timeout`) for faster scanning if you don't mind missing slow servers
- **Use SSD storage** for better I/O performance with large result files

## Provider-Specific Patterns

The tool includes optimized patterns for major email providers:

- **Google/Gmail**: `imap.gmail.com`
- **Microsoft/Outlook**: `imap-mail.outlook.com`, `outlook.office365.com`
- **Yahoo**: `imap.mail.yahoo.com`
- **AOL**: `imap.aol.com`
- **Zoho**: `imap.zoho.com`

## Security Notes

- The tool only performs port scanning and banner reading
- No authentication attempts are made
- SSL certificate verification is disabled for banner grabbing
- Use responsibly and only on domains you own or have permission to test

## Troubleshooting

### DNS Resolution Issues
```bash
# Test DNS resolution manually
nslookup domain.com
dig MX domain.com
```

### High Memory Usage
- Reduce `--workers` parameter
- Process domains in smaller batches

### Slow Performance
- Increase `--workers` (up to 100-200 on powerful machines)
- Decrease `--timeout` for faster scanning
- Use faster DNS servers (8.8.8.8, 1.1.1.1)
