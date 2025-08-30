# 🌐 IMAP Discovery Web Interface

Professional drag-and-drop web interface for discovering IMAP server configurations from email lists.

## ✨ Features

### 🎯 Professional Design
- **Modern UI** with Tailwind CSS
- **Responsive design** works on desktop and mobile
- **Professional gradient styling** and smooth animations
- **Intuitive drag-and-drop** file upload area

### 📁 File Processing
- **Drag & Drop Support** - Simply drag your .txt file onto the upload area
- **Real-time Validation** - Instant feedback on file type and format
- **Progress Tracking** - Live progress bar with current email being processed
- **Batch Processing** - Configurable worker threads and timeouts

### 🔍 IMAP Discovery
- **Real Connection Testing** - Actual IMAP server connections to verify configurations
- **Multi-threaded Processing** - Fast parallel processing of multiple emails
- **Smart Pattern Matching** - Recognizes major email providers (Gmail, Outlook, Yahoo, etc.)
- **MX Record Lookup** - Uses DNS queries to find mail servers

### 📊 Results Display
- **Organized Table** - Clean display with email, domain, IMAP server, port, and password
- **Advanced Filtering** - Search by email/domain, filter by port type
- **Sortable Columns** - Click column headers to sort results
- **Success Statistics** - Real-time stats showing success rates and counts
- **Password Protection** - Passwords hidden by default with toggle visibility

### 📤 Export Options
- **CSV Export** - Download complete results as CSV file
- **Copy to Clipboard** - Quick copy of successful configurations
- **Professional Format** - Ready-to-use configuration data

## 🚀 Quick Start

### 1. Install Dependencies
```bash
# Windows
install.bat

# Linux/Mac
pip install -r requirements.txt
```

### 2. Start the Web Interface
```bash
python start_server.py
```

### 3. Access the Interface
- **Automatic**: Browser opens automatically at `http://localhost:5000`
- **Manual**: Open `http://localhost:5000` in your web browser

### 4. Process Your Emails
1. **Upload File**: Drag & drop your email:password .txt file
2. **Configure Settings**: Adjust timeout, workers, and processing limits
3. **Start Processing**: Click "Discover IMAP Configurations"
4. **View Results**: See real-time progress and results
5. **Export Data**: Download CSV or copy configurations

## 📋 File Format

Your input file should contain email:password pairs, one per line:

```
user@gmail.com:password123
admin@company.com:secretpass
test@yahoo.com:mypassword
```

## ⚙️ Configuration Options

### Connection Timeout
- **3 seconds**: Fast processing, may miss slow servers
- **5 seconds**: Default balanced setting
- **10 seconds**: Thorough testing, slower processing

### Worker Threads
- **10 threads**: Conservative, good for slower systems
- **20 threads**: Default balanced setting
- **30 threads**: Fast processing for powerful systems
- **50 threads**: Maximum speed for high-end systems

### Test Limit
- **All emails**: Process complete file
- **First 10**: Quick test mode
- **First 50**: Sample processing
- **First 100**: Larger sample

## 📊 Results Interpretation

### Status Indicators
- **✅ Success**: Working IMAP configuration found and tested
- **❌ Failed**: No working IMAP server found
- **⚠️ Error**: Processing error occurred

### Port Information
- **Port 993**: Secure IMAP over SSL/TLS (recommended)
- **Port 143**: Standard IMAP (less secure)

### Success Rates
- **90%+**: Excellent - Most configurations working
- **70-89%**: Good - Majority of configurations working
- **50-69%**: Average - Mixed results
- **<50%**: Poor - Many failed configurations

## 🔧 Technical Details

### Backend Architecture
- **Flask Web Server**: Handles file uploads and API requests
- **Background Processing**: Non-blocking email processing
- **Real IMAP Testing**: Actual connection attempts to verify servers
- **Progress Polling**: Real-time status updates via AJAX

### Frontend Features
- **Responsive Design**: Works on all screen sizes
- **Real-time Updates**: Live progress and status updates
- **Professional UI**: Clean, modern interface design
- **Error Handling**: Graceful error messages and recovery

### Security
- **Local Processing**: All data processed on your local machine
- **No Data Storage**: Files not permanently stored on server
- **Private Processing**: No external API calls or data sharing

## 🛠️ Troubleshooting

### Common Issues

**Server Won't Start**
```bash
# Install dependencies
pip install -r requirements.txt

# Check Python version (requires 3.7+)
python --version
```

**File Upload Fails**
- Ensure file is .txt format
- Check file contains valid email:password pairs
- Verify file is not corrupted

**Processing Errors**
- Reduce worker threads if system overloaded
- Increase timeout for slow networks
- Check internet connection for DNS/IMAP tests

**No Results Found**
- Verify email format is correct
- Check if domains have valid MX records
- Try increasing connection timeout

### Performance Tips

**Faster Processing**
- Increase worker threads (30-50)
- Decrease timeout (3 seconds)
- Use test limits for large files

**More Accurate Results**
- Increase timeout (10 seconds)
- Reduce worker threads (10-20)
- Process smaller batches

## 📁 Project Structure

```
├── index.html              # Main web interface
├── app.js                  # Frontend JavaScript
├── backend.py              # Flask web server
├── start_server.py         # Startup script
├── email_imap_finder.py    # Core IMAP discovery logic
├── requirements.txt        # Python dependencies
├── install.bat            # Windows installer
└── README.md              # Documentation
```

## 🔗 Integration

### With Existing Tools
- **Command Line**: Use `email_imap_finder.py` directly
- **Scripts**: Import `EmailIMAPFinder` class
- **APIs**: Access Flask backend endpoints

### API Endpoints
- `POST /api/process` - Upload and process file
- `GET /api/status/{id}` - Get processing status
- `GET /api/export/{id}` - Export results as CSV

## 🎨 Customization

### Styling
- Modify `index.html` for layout changes
- Update Tailwind classes for appearance
- Add custom CSS for specific styling

### Functionality
- Edit `app.js` for frontend behavior
- Modify `backend.py` for server logic
- Extend `email_imap_finder.py` for processing

## 📞 Support

### Resources
- **Command Line Version**: Use `python email_imap_finder.py --help`
- **Interactive Mode**: Run `python run_discovery.py`
- **Direct Processing**: Process files directly with CLI tools

### Tips for Success
1. **Start Small**: Test with 10-50 emails first
2. **Check Format**: Ensure proper email:password format
3. **Adjust Settings**: Tune timeout and workers for your system
4. **Monitor Progress**: Watch real-time processing status
5. **Export Results**: Save successful configurations immediately

---

🚀 **Ready to discover IMAP configurations?** Run `python start_server.py` and open your browser!
