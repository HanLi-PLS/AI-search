// API Configuration
const API_BASE_URL = window.location.origin + '/api';

// DOM Elements
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const uploadProgress = document.getElementById('uploadProgress');
const progressFill = document.getElementById('progressFill');
const uploadStatus = document.getElementById('uploadStatus');
const uploadResults = document.getElementById('uploadResults');
const searchInput = document.getElementById('searchInput');
const searchButton = document.getElementById('searchButton');
const searchResults = document.getElementById('searchResults');
const topKSelect = document.getElementById('topKSelect');
const documentsList = document.getElementById('documentsList');
const refreshButton = document.getElementById('refreshButton');
const loadingSpinner = document.getElementById('loadingSpinner');

// Event Listeners
uploadArea.addEventListener('click', () => fileInput.click());
uploadArea.addEventListener('dragover', handleDragOver);
uploadArea.addEventListener('dragleave', handleDragLeave);
uploadArea.addEventListener('drop', handleDrop);
fileInput.addEventListener('change', handleFileSelect);
searchButton.addEventListener('click', performSearch);
searchInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') performSearch();
});
refreshButton.addEventListener('click', loadDocuments);

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadDocuments();
    checkHealth();
});

// Drag and Drop Handlers
function handleDragOver(e) {
    e.preventDefault();
    uploadArea.classList.add('drag-over');
}

function handleDragLeave(e) {
    e.preventDefault();
    uploadArea.classList.remove('drag-over');
}

function handleDrop(e) {
    e.preventDefault();
    uploadArea.classList.remove('drag-over');
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        uploadFiles(files);
    }
}

function handleFileSelect(e) {
    const files = e.target.files;
    if (files.length > 0) {
        uploadFiles(files);
    }
}

// File Upload
async function uploadFiles(files) {
    uploadResults.innerHTML = '';
    uploadProgress.style.display = 'block';
    progressFill.style.width = '0%';
    uploadStatus.textContent = `Uploading ${files.length} file(s)...`;

    const totalFiles = files.length;
    let completed = 0;

    for (const file of files) {
        try {
            const formData = new FormData();
            formData.append('file', file);

            const response = await fetch(`${API_BASE_URL}/upload`, {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (response.ok && result.success) {
                displayUploadResult(file.name, result, true);
                showToast(`${file.name} uploaded successfully`, 'success');
            } else {
                displayUploadResult(file.name, result, false);
                showToast(`Failed to upload ${file.name}`, 'error');
            }

        } catch (error) {
            console.error('Upload error:', error);
            displayUploadResult(file.name, { message: error.message }, false);
            showToast(`Error uploading ${file.name}`, 'error');
        }

        completed++;
        const progress = (completed / totalFiles) * 100;
        progressFill.style.width = `${progress}%`;
        uploadStatus.textContent = `Uploaded ${completed} of ${totalFiles} file(s)`;
    }

    // Reset file input
    fileInput.value = '';

    // Refresh documents list
    setTimeout(() => {
        loadDocuments();
    }, 1000);
}

function displayUploadResult(fileName, result, success) {
    const resultItem = document.createElement('div');
    resultItem.className = `upload-result-item ${success ? '' : 'error'}`;

    const icon = success ? `
        <svg class="upload-result-icon success-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
        </svg>
    ` : `
        <svg class="upload-result-icon error-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
        </svg>
    `;

    const details = success
        ? `${result.chunks_created} chunks created in ${result.processing_time}s`
        : result.detail || result.message || 'Upload failed';

    resultItem.innerHTML = `
        <div class="upload-result-info">
            <div class="upload-result-name">${fileName}</div>
            <div class="upload-result-details">${details}</div>
        </div>
        ${icon}
    `;

    uploadResults.appendChild(resultItem);
}

// Search
async function performSearch() {
    const query = searchInput.value.trim();
    if (!query) {
        showToast('Please enter a search query', 'info');
        return;
    }

    showLoading();
    searchResults.innerHTML = '';

    try {
        const response = await fetch(`${API_BASE_URL}/search`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                query: query,
                top_k: parseInt(topKSelect.value)
            })
        });

        const result = await response.json();

        if (response.ok && result.success) {
            displaySearchResults(result);
        } else {
            showToast('Search failed', 'error');
            searchResults.innerHTML = '<div class="no-results">Search failed. Please try again.</div>';
        }

    } catch (error) {
        console.error('Search error:', error);
        showToast('Search error occurred', 'error');
        searchResults.innerHTML = '<div class="no-results">An error occurred. Please try again.</div>';
    } finally {
        hideLoading();
    }
}

function displaySearchResults(result) {
    if (result.results.length === 0) {
        searchResults.innerHTML = `
            <div class="no-results">
                <p>No results found for "${result.query}"</p>
                <p style="margin-top: 10px; font-size: 0.9rem;">Try different keywords or upload more documents.</p>
            </div>
        `;
        return;
    }

    // Show answer first if available
    let htmlContent = '';
    if (result.answer) {
        htmlContent = `
            <div class="answer-box">
                <div class="answer-header">
                    <svg style="width: 20px; height: 20px; margin-right: 8px;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                    </svg>
                    Answer
                </div>
                <div class="answer-content">${result.answer.replace(/\n/g, '<br>')}</div>
            </div>
        `;
    }

    htmlContent += `
        <div class="search-info" style="margin-bottom: 15px; color: var(--text-secondary);">
            Found ${result.total_results} source(s) in ${result.processing_time}s
        </div>
        <button class="sources-toggle-button" id="sourcesToggle">
            <svg class="toggle-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
            </svg>
            Show Sources (${result.total_results})
        </button>
        <div class="sources-container" id="sourcesContainer" style="display: none;">
            <div class="sources-header">Sources:</div>
            <div id="sourcesContent"></div>
        </div>
    `;

    searchResults.innerHTML = htmlContent;

    // Get the sources content container
    const sourcesContent = document.getElementById('sourcesContent');

    result.results.forEach((item, index) => {
        const resultItem = document.createElement('div');
        resultItem.className = 'search-result-item';

        const score = Math.round(item.score * 100);
        const fileName = item.metadata.file_name || 'Unknown';
        const fileType = item.metadata.file_type || '';
        const page = item.metadata.page ? `Page ${item.metadata.page}` : '';
        const uploadDate = item.metadata.upload_date
            ? new Date(item.metadata.upload_date).toLocaleDateString()
            : '';

        // Truncate content if too long
        let content = item.content;
        if (content.length > 500) {
            content = content.substring(0, 500) + '...';
        }

        // Get retrieval method and create badge
        const retrievalMethod = item.retrieval_method || 'Dense';
        const badgeClass = retrievalMethod === 'Both' ? 'retrieval-badge-both' :
                          retrievalMethod === 'BM25' ? 'retrieval-badge-bm25' :
                          'retrieval-badge-dense';
        const badgeText = retrievalMethod === 'Both' ? 'Dense + BM25' : retrievalMethod;

        resultItem.innerHTML = `
            <div class="search-result-header">
                <div class="search-result-meta">
                    <div class="search-result-filename">${fileName}</div>
                    <div class="search-result-details">
                        ${fileType} ${page ? `• ${page}` : ''} ${uploadDate ? `• ${uploadDate}` : ''}
                    </div>
                </div>
                <div class="search-result-badges">
                    <div class="retrieval-badge ${badgeClass}">${badgeText}</div>
                    <div class="search-result-score">${score}%</div>
                </div>
            </div>
            <div class="search-result-content">${content}</div>
        `;

        sourcesContent.appendChild(resultItem);
    });

    // Add toggle functionality
    const sourcesToggle = document.getElementById('sourcesToggle');
    const sourcesContainer = document.getElementById('sourcesContainer');

    sourcesToggle.addEventListener('click', () => {
        const isVisible = sourcesContainer.style.display !== 'none';
        sourcesContainer.style.display = isVisible ? 'none' : 'block';
        sourcesToggle.innerHTML = isVisible
            ? `<svg class="toggle-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
               </svg>
               Show Sources (${result.total_results})`
            : `<svg class="toggle-icon rotate-180" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
               </svg>
               Hide Sources`;
    });
}

// Load Documents
async function loadDocuments() {
    try {
        const response = await fetch(`${API_BASE_URL}/documents`);
        const result = await response.json();

        if (response.ok && result.success) {
            displayDocuments(result.documents);
        } else {
            documentsList.innerHTML = '<div class="no-results">Failed to load documents</div>';
        }

    } catch (error) {
        console.error('Error loading documents:', error);
        documentsList.innerHTML = '<div class="no-results">Error loading documents</div>';
    }
}

function displayDocuments(documents) {
    if (documents.length === 0) {
        documentsList.innerHTML = '<div class="no-results">No documents uploaded yet</div>';
        return;
    }

    documentsList.innerHTML = '';

    documents.forEach(doc => {
        const docItem = document.createElement('div');
        docItem.className = 'document-item';

        const fileSize = formatFileSize(doc.file_size);
        const uploadDate = new Date(doc.upload_date).toLocaleDateString();

        docItem.innerHTML = `
            <div class="document-info">
                <div class="document-name">${doc.file_name}</div>
                <div class="document-meta">
                    ${doc.file_type} • ${fileSize} • ${doc.chunk_count} chunks • Uploaded ${uploadDate}
                </div>
            </div>
            <button class="delete-button" onclick="deleteDocument('${doc.file_id}', '${doc.file_name}')">
                Delete
            </button>
        `;

        documentsList.appendChild(docItem);
    });
}

// Delete Document
async function deleteDocument(fileId, fileName) {
    if (!confirm(`Are you sure you want to delete "${fileName}"?`)) {
        return;
    }

    showLoading();

    try {
        const response = await fetch(`${API_BASE_URL}/documents/${fileId}`, {
            method: 'DELETE'
        });

        const result = await response.json();

        if (response.ok && result.success) {
            showToast(`${fileName} deleted successfully`, 'success');
            loadDocuments();
        } else {
            showToast('Failed to delete document', 'error');
        }

    } catch (error) {
        console.error('Delete error:', error);
        showToast('Error deleting document', 'error');
    } finally {
        hideLoading();
    }
}

// Health Check
async function checkHealth() {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        const result = await response.json();

        if (!response.ok || result.status !== 'healthy') {
            showToast('System health check failed', 'error');
        }

    } catch (error) {
        console.error('Health check error:', error);
    }
}

// Utility Functions
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

function showLoading() {
    loadingSpinner.style.display = 'flex';
}

function hideLoading() {
    loadingSpinner.style.display = 'none';
}

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `<div class="toast-message">${message}</div>`;

    const container = document.getElementById('toastContainer');
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s ease reverse';
        setTimeout(() => {
            container.removeChild(toast);
        }, 300);
    }, 3000);
}
