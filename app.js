// Global variables
let currentFile = null;
let currentTextData = null;
let currentResults = [];
let originalPasswords = new Map(); // Store original passwords
let sortDirection = 'asc';
let currentSortColumn = '';
let currentInputMethod = 'file'; // 'file' or 'text'

// DOM elements
const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('file-input');
const uploadContent = document.getElementById('upload-content');
const fileInfo = document.getElementById('file-info');
const fileName = document.getElementById('file-name');
const fileSize = document.getElementById('file-size');
const processBtn = document.getElementById('process-btn');
const progressSection = document.getElementById('progress-section');
const progressBar = document.getElementById('progress-bar');
const progressText = document.getElementById('progress-text');
const progressPercent = document.getElementById('progress-percent');
const currentEmail = document.getElementById('current-email');
const resultsSection = document.getElementById('results-section');
const resultsTable = document.getElementById('results-table');
const loadingModal = document.getElementById('loading-modal');

// Tab elements
const tabFile = document.getElementById('tab-file');
const tabText = document.getElementById('tab-text');
const methodFile = document.getElementById('method-file');
const methodText = document.getElementById('method-text');

// Text input elements
const emailTextInput = document.getElementById('email-text-input');
const clearTextBtn = document.getElementById('clear-text');
const validateTextBtn = document.getElementById('validate-text');
const lineCount = document.getElementById('line-count');
const validationResults = document.getElementById('validation-results');
const validCount = document.getElementById('valid-count');
const invalidCount = document.getElementById('invalid-count');
const totalLines = document.getElementById('total-lines');

// Settings elements
const timeoutSelect = document.getElementById('timeout');
const workersSelect = document.getElementById('workers');
const limitSelect = document.getElementById('limit');

// Results elements
const exportCsvBtn = document.getElementById('export-csv');
const copyConfigsBtn = document.getElementById('copy-configs');
const searchInput = document.getElementById('search-input');
const portFilter = document.getElementById('port-filter');
const statTotal = document.getElementById('stat-total');
const statSuccess = document.getElementById('stat-success');
const statFailed = document.getElementById('stat-failed');
const statRate = document.getElementById('stat-rate');
const visibleCount = document.getElementById('visible-count');
const totalCount = document.getElementById('total-count');
const resultsSummary = document.getElementById('results-summary');

// Initialize tab functionality
function initTabs() {
    // Tab switching
    tabFile.addEventListener('click', () => switchTab('file'));
    tabText.addEventListener('click', () => switchTab('text'));
    
    // Text input functionality
    emailTextInput.addEventListener('input', updateLineCount);
    clearTextBtn.addEventListener('click', clearTextInput);
    validateTextBtn.addEventListener('click', validateTextInput);
}

function switchTab(method) {
    currentInputMethod = method;
    
    // Update tab appearance
    if (method === 'file') {
        tabFile.classList.add('active');
        tabText.classList.remove('active');
        methodFile.classList.remove('hidden');
        methodText.classList.add('hidden');
    } else {
        tabText.classList.add('active');
        tabFile.classList.remove('active');
        methodText.classList.remove('hidden');
        methodFile.classList.add('hidden');
    }
    
    // Update process button state
    updateProcessButtonState();
}

function updateLineCount() {
    const text = emailTextInput.value;
    const lines = text.split('\n').filter(line => line.trim() !== '');
    lineCount.textContent = lines.length;
    
    // Hide validation results when text changes
    validationResults.classList.add('hidden');
    
    // Update process button
    updateProcessButtonState();
}

function clearTextInput() {
    emailTextInput.value = '';
    updateLineCount();
    validationResults.classList.add('hidden');
    currentTextData = null;
}

function validateTextInput() {
    const text = emailTextInput.value.trim();
    if (!text) {
        showAlert('Please enter some email:password pairs first.', 'error');
        return;
    }
    
    const lines = text.split('\n');
    let validEmails = 0;
    let invalidLines = 0;
    const validEmailData = [];
    
    lines.forEach(line => {
        line = line.trim();
        if (line === '') return; // Skip empty lines
        
        if (line.includes(':') && line.includes('@')) {
            const [email, password] = line.split(':');
            if (email && password && email.includes('@') && email.includes('.')) {
                validEmails++;
                validEmailData.push({
                    email: email.trim(),
                    password: password.trim(),
                    domain: email.split('@')[1].toLowerCase()
                });
                originalPasswords.set(email.trim(), password.trim());
            } else {
                invalidLines++;
            }
        } else {
            invalidLines++;
        }
    });
    
    // Update validation display
    validCount.textContent = validEmails;
    invalidCount.textContent = invalidLines;
    totalLines.textContent = lines.filter(l => l.trim() !== '').length;
    validationResults.classList.remove('hidden');
    
    // Store validated data
    currentTextData = validEmailData;
    
    // Update process button
    updateProcessButtonState();
    
    if (validEmails > 0) {
        showAlert(`Validation complete! Found ${validEmails} valid email:password pairs.`, 'success');
    } else {
        showAlert('No valid email:password pairs found. Please check your format.', 'error');
    }
}

function updateProcessButtonState() {
    if (currentInputMethod === 'file') {
        processBtn.disabled = currentFile === null;
    } else {
        processBtn.disabled = currentTextData === null || currentTextData.length === 0;
    }
}

// Initialize drag and drop functionality
function initDragDrop() {
    // Prevent default drag behaviors
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });

    // Highlight drop area when item is dragged over it
    ['dragenter', 'dragover'].forEach(eventName => {
        dropzone.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, unhighlight, false);
    });

    // Handle dropped files
    dropzone.addEventListener('drop', handleDrop, false);
    
    // Handle click to upload
    dropzone.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', handleFileSelect);
}

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

function highlight() {
    dropzone.classList.add('drag-over');
}

function unhighlight() {
    dropzone.classList.remove('drag-over');
}

function handleDrop(e) {
    const dt = e.dataTransfer;
    const files = dt.files;
    handleFiles(files);
}

function handleFileSelect(e) {
    const files = e.target.files;
    handleFiles(files);
}

function handleFiles(files) {
    if (files.length > 0) {
        const file = files[0];
        
        // Validate file type
        if (!file.name.toLowerCase().endsWith('.txt')) {
            showAlert('Please select a .txt file containing email:password pairs.', 'error');
            return;
        }
        
        currentFile = file;
        updateFileDisplay(file);
        processBtn.disabled = false;
    }
}

function updateFileDisplay(file) {
    uploadContent.classList.add('hidden');
    fileInfo.classList.remove('hidden');
    fileName.textContent = file.name;
    fileSize.textContent = formatFileSize(file.size);
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function showAlert(message, type = 'info') {
    // Create alert element
    const alert = document.createElement('div');
    alert.className = `fixed top-4 right-4 z-50 p-4 rounded-lg shadow-lg transition-all duration-300 transform translate-x-full`;
    
    if (type === 'error') {
        alert.className += ' bg-red-500 text-white';
    } else if (type === 'success') {
        alert.className += ' bg-green-500 text-white';
    } else {
        alert.className += ' bg-blue-500 text-white';
    }
    
    alert.innerHTML = `
        <div class="flex items-center space-x-2">
            <i class="fas fa-${type === 'error' ? 'exclamation-circle' : type === 'success' ? 'check-circle' : 'info-circle'}"></i>
            <span>${message}</span>
        </div>
    `;
    
    document.body.appendChild(alert);
    
    // Animate in
    setTimeout(() => {
        alert.classList.remove('translate-x-full');
    }, 100);
    
    // Remove after 5 seconds
    setTimeout(() => {
        alert.classList.add('translate-x-full');
        setTimeout(() => alert.remove(), 300);
    }, 5000);
}

// Process emails function
async function processEmails() {
    // Check input method
    if (currentInputMethod === 'file' && !currentFile) {
        showAlert('Please select a file first.', 'error');
        return;
    }
    
    if (currentInputMethod === 'text' && (!currentTextData || currentTextData.length === 0)) {
        showAlert('Please enter and validate email:password pairs first.', 'error');
        return;
    }

    try {
        // Show progress section
        progressSection.classList.remove('hidden');
        resultsSection.classList.add('hidden');
        processBtn.disabled = true;
        
        // Reset progress
        updateProgress(0, 'Preparing to process...');
        
        let response;
        
        if (currentInputMethod === 'file') {
            // File upload method
            updateProgress(5, 'Uploading file...');
            
            const formData = new FormData();
            formData.append('file', currentFile);
            formData.append('timeout', timeoutSelect.value);
            formData.append('workers', workersSelect.value);
            if (limitSelect.value) {
                formData.append('limit', limitSelect.value);
            }
            
            response = await axios.post('/api/process', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data'
                }
            });
            
            showAlert('File uploaded successfully! Processing started...', 'info');
        } else {
            // Text input method - send JSON directly to dedicated endpoint
            updateProgress(5, 'Processing text input...');
            
            const emailText = currentTextData.map(item => `${item.email}:${item.password}`).join('\n');
            const requestData = {
                email_text: emailText,
                timeout: parseInt(timeoutSelect.value),
                workers: parseInt(workersSelect.value)
            };
            
            if (limitSelect.value) {
                requestData.limit = parseInt(limitSelect.value);
            }
            
            response = await axios.post('/api/process-text', requestData, {
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            showAlert('Text input processed successfully! Processing started...', 'info');
        }
        
        const { process_id } = response.data;
        
        // Poll for status updates
        const results = await pollProcessingStatus(process_id);
        
        // Store results and display
        currentResults = results.results;
        displayResults(results.results, results.statistics);
        
        showAlert(`Processing completed! Found ${results.statistics.successful} working configurations.`, 'success');
        
    } catch (error) {
        console.error('Error processing emails:', error);
        showAlert('Error processing emails: ' + (error.response?.data?.error || error.message), 'error');
        resetUI();
    }
}

function readFileContent(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = e => resolve(e.target.result);
        reader.onerror = e => reject(new Error('Error reading file'));
        reader.readAsText(file);
    });
}

function parseEmailFile(content) {
    const lines = content.split('\n');
    const emails = [];
    
    for (let line of lines) {
        line = line.trim();
        if (line && line.includes(':') && line.includes('@')) {
            const [email, password] = line.split(':');
            if (email && password && email.includes('@')) {
                emails.push({
                    email: email.trim(),
                    password: password.trim(),
                    domain: email.split('@')[1].toLowerCase()
                });
                originalPasswords.set(email.trim(), password.trim());
            }
        }
    }
    
    return emails;
}

// Poll for processing status
async function pollProcessingStatus(processId) {
    return new Promise((resolve, reject) => {
        const pollInterval = setInterval(async () => {
            try {
                const response = await axios.get(`/api/status/${processId}`);
                const status = response.data;
                
                // Update progress display
                updateProgress(status.progress, getStatusText(status));
                
                if (status.status === 'completed') {
                    clearInterval(pollInterval);
                    resolve(status);
                } else if (status.status === 'error') {
                    clearInterval(pollInterval);
                    reject(new Error(status.error || 'Processing failed'));
                }
            } catch (error) {
                clearInterval(pollInterval);
                reject(error);
            }
        }, 1000); // Poll every second
    });
}

function getStatusText(status) {
    switch (status.status) {
        case 'starting':
            return 'Initializing processing...';
        case 'reading_file':
        case 'reading_data':
            return 'Reading email data...';
        case 'processing':
            if (status.current_email) {
                return `Processing ${status.current_email} (${status.processed}/${status.total_emails})`;
            }
            return `Processing emails... (${status.processed || 0}/${status.total_emails || 0})`;
        case 'completed':
            return 'Processing completed!';
        case 'error':
            return 'Processing failed';
        default:
            return 'Processing...';
    }
}

function simulateImapDiscovery(emailData) {
    // Simulate different outcomes based on domain patterns
    const domain = emailData.domain;
    const email = emailData.email;
    
    // Common providers
    if (domain.includes('gmail.com')) {
        return {
            email,
            domain,
            imap_server: 'imap.gmail.com',
            port: 993,
            password: originalPasswords.get(email),
            status: 'success'
        };
    }
    
    if (domain.includes('outlook.com') || domain.includes('hotmail.com') || domain.includes('live.com')) {
        return {
            email,
            domain,
            imap_server: 'imap-mail.outlook.com',
            port: 993,
            password: originalPasswords.get(email),
            status: 'success'
        };
    }
    
    if (domain.includes('yahoo.com')) {
        return {
            email,
            domain,
            imap_server: 'imap.mail.yahoo.com',
            port: 993,
            password: originalPasswords.get(email),
            status: 'success'
        };
    }
    
    // Simulate high success rate for other domains
    const successRate = 0.85; // 85% success rate
    if (Math.random() < successRate) {
        const useSSL = Math.random() > 0.1; // 90% use SSL
        return {
            email,
            domain,
            imap_server: `${Math.random() > 0.5 ? 'imap' : 'mail'}.${domain}`,
            port: useSSL ? 993 : 143,
            password: originalPasswords.get(email),
            status: 'success'
        };
    } else {
        return {
            email,
            domain,
            imap_server: '',
            port: '',
            password: originalPasswords.get(email),
            status: 'failed'
        };
    }
}

function updateProgress(percent, text) {
    progressBar.style.width = percent + '%';
    progressPercent.textContent = Math.round(percent) + '%';
    progressText.textContent = text;
    
    // Update current email display
    if (text.startsWith('Processing ')) {
        currentEmail.textContent = text;
    }
}

function displayResults(results, statistics = null) {
    // Hide progress, show results
    progressSection.classList.add('hidden');
    resultsSection.classList.remove('hidden');
    
    // Update statistics
    let stats;
    if (statistics) {
        stats = statistics;
    } else {
        const total = results.length;
        const successful = results.filter(r => r.status === 'success').length;
        const failed = total - successful;
        const successRate = total > 0 ? Math.round((successful / total) * 100) : 0;
        stats = { total, successful, failed, success_rate: successRate };
    }
    
    statTotal.textContent = stats.total;
    statSuccess.textContent = stats.successful;
    statFailed.textContent = stats.failed;
    statRate.textContent = stats.success_rate + '%';
    
    resultsSummary.textContent = `Found ${stats.successful} working configurations out of ${stats.total} emails processed (${stats.success_rate}% success rate)`;
    
    // Render table
    renderTable(results);
    
    // Update counts
    updateVisibleCount();
    
    // Reset process button
    processBtn.disabled = false;
}

function renderTable(results = currentResults) {
    resultsTable.innerHTML = '';
    
    // Apply filters
    const searchTerm = searchInput.value.toLowerCase();
    const portFilter = document.getElementById('port-filter').value;
    
    const filteredResults = results.filter(result => {
        const matchesSearch = !searchTerm || 
            result.email.toLowerCase().includes(searchTerm) ||
            result.domain.toLowerCase().includes(searchTerm) ||
            result.imap_server.toLowerCase().includes(searchTerm);
        
        const matchesPort = !portFilter || result.port.toString() === portFilter;
        
        return matchesSearch && matchesPort;
    });
    
    // Render rows
    filteredResults.forEach(result => {
        const row = document.createElement('tr');
        row.className = 'hover:bg-gray-50 transition-colors duration-200';
        
        const statusClass = result.status === 'success' ? 'text-green-600' : 'text-red-600';
        const statusIcon = result.status === 'success' ? 'fa-check-circle' : 'fa-times-circle';
        const portBadge = result.port === 993 ? 'bg-green-100 text-green-800' : 
                         result.port === 143 ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-800';
        
        const password = result.password || originalPasswords.get(result.email) || 'N/A';
        
        row.innerHTML = `
            <td class="px-6 py-4 whitespace-nowrap">
                <div class="flex items-center">
                    <i class="fas fa-envelope text-gray-400 mr-2"></i>
                    <span class="text-sm font-medium text-gray-900">${result.email}</span>
                </div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
                <span class="text-sm text-gray-600">${result.domain}</span>
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
                <div class="flex items-center">
                    <i class="fas fa-server text-gray-400 mr-2"></i>
                    <span class="text-sm font-mono text-gray-900">${result.imap_server || 'N/A'}</span>
                </div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
                ${result.port ? `<span class="inline-flex px-2 py-1 text-xs font-semibold rounded-full ${portBadge}">${result.port}</span>` : '<span class="text-gray-400">N/A</span>'}
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
                <div class="flex items-center">
                    <span class="text-sm font-mono text-gray-600">••••••••</span>
                    <button class="ml-2 text-blue-600 hover:text-blue-800 text-xs" onclick="togglePassword(this, '${password}')">
                        <i class="fas fa-eye"></i>
                    </button>
                </div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
                <div class="flex items-center">
                    <i class="fas ${statusIcon} ${statusClass} mr-2"></i>
                    <span class="text-sm font-medium ${statusClass} capitalize">${result.status}</span>
                </div>
            </td>
        `;
        
        resultsTable.appendChild(row);
    });
    
    // Update visible count
    visibleCount.textContent = filteredResults.length;
    totalCount.textContent = results.length;
}

function togglePassword(button, password) {
    const span = button.parentElement.querySelector('span');
    const icon = button.querySelector('i');
    
    if (span.textContent === '••••••••') {
        span.textContent = password;
        icon.className = 'fas fa-eye-slash';
    } else {
        span.textContent = '••••••••';
        icon.className = 'fas fa-eye';
    }
}

function updateVisibleCount() {
    const visibleRows = resultsTable.children.length;
    visibleCount.textContent = visibleRows;
    totalCount.textContent = currentResults.length;
}

function resetUI() {
    progressSection.classList.add('hidden');
    resultsSection.classList.add('hidden');
    processBtn.disabled = currentFile === null;
}

// Export functionality
function exportToCSV() {
    if (currentResults.length === 0) {
        showAlert('No data to export.', 'error');
        return;
    }
    
    const headers = ['email', 'domain', 'imap_server', 'port', 'password'];
    const csvContent = [
        headers.join(','),
        ...currentResults.map(result => [
            result.email,
            result.domain,
            result.imap_server,
            result.port,
            result.password
        ].join(','))
    ].join('\n');
    
    downloadCSV(csvContent, 'imap_configurations.csv');
    showAlert('CSV file downloaded successfully!', 'success');
}

function downloadCSV(content, filename) {
    const blob = new Blob([content], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', filename);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

function copyResults() {
    if (currentResults.length === 0) {
        showAlert('No data to copy.', 'error');
        return;
    }
    
    const text = currentResults
        .filter(r => r.status === 'success')
        .map(r => `${r.email}:${r.password} -> ${r.imap_server}:${r.port}`)
        .join('\n');
    
    navigator.clipboard.writeText(text).then(() => {
        showAlert('Results copied to clipboard!', 'success');
    });
}

// Table sorting
function setupTableSorting() {
    const headers = document.querySelectorAll('th[data-sort]');
    headers.forEach(header => {
        header.addEventListener('click', () => {
            const column = header.dataset.sort;
            sortTable(column);
        });
    });
}

function sortTable(column) {
    if (currentSortColumn === column) {
        sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
        sortDirection = 'asc';
        currentSortColumn = column;
    }
    
    currentResults.sort((a, b) => {
        let aVal = a[column] || '';
        let bVal = b[column] || '';
        
        if (column === 'port') {
            aVal = parseInt(aVal) || 0;
            bVal = parseInt(bVal) || 0;
        } else {
            aVal = aVal.toString().toLowerCase();
            bVal = bVal.toString().toLowerCase();
        }
        
        if (sortDirection === 'asc') {
            return aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
        } else {
            return aVal > bVal ? -1 : aVal < bVal ? 1 : 0;
        }
    });
    
    renderTable();
}

// Event listeners
document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    initDragDrop();
    setupTableSorting();
    
    // Process button
    processBtn.addEventListener('click', processEmails);
    
    // Export and copy buttons
    exportCsvBtn.addEventListener('click', exportToCSV);
    copyConfigsBtn.addEventListener('click', copyResults);
    
    // Search and filter
    searchInput.addEventListener('input', () => {
        renderTable();
        updateVisibleCount();
    });
    
    document.getElementById('port-filter').addEventListener('change', () => {
        renderTable();
        updateVisibleCount();
    });
    
    // Initialize process button state
    updateProcessButtonState();
});

// Make functions globally available
window.togglePassword = togglePassword;
