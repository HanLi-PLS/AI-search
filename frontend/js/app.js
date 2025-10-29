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
const searchModeSelect = document.getElementById('searchModeSelect');
const priorityOrderSelect = document.getElementById('priorityOrderSelect');
const priorityOrderLabel = document.getElementById('priorityOrderLabel');
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
searchModeSelect.addEventListener('change', handleSearchModeChange);

// Handle search mode change to show/hide priority order
function handleSearchModeChange() {
    const searchMode = searchModeSelect.value;
    if (searchMode === 'both') {
        priorityOrderLabel.style.display = 'inline-block';
    } else {
        priorityOrderLabel.style.display = 'none';
    }
}

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

    // Show graceful loading animation
    showSearchLoading();

    try {
        // Get search mode and priority order
        const searchMode = searchModeSelect.value;
        const priorityOrder = priorityOrderSelect.value === 'online_first'
            ? ['online_search', 'files']
            : ['files', 'online_search'];

        const response = await fetch(`${API_BASE_URL}/search`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                query: query,
                top_k: parseInt(topKSelect.value),
                search_mode: searchMode,
                priority_order: priorityOrder
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
    }
}

function displaySearchResults(result) {
    // Show answer even if no file results (for online_only mode)
    let htmlContent = '';

    // Pantone colors: 295U (blue) for online, 1505U (orange) for answer
    const pantone295U = '#003DA5';  // Blue
    const pantone1505U = '#FF6900'; // Orange
    const extractGreen = '#059669';  // Green for extracted info

    // Show extracted info if available (sequential_analysis mode)
    if (result.extracted_info) {
        htmlContent += `
            <div class="answer-box" style="margin-bottom: 20px; border-left: 4px solid ${extractGreen};">
                <div class="answer-header" style="color: ${extractGreen};">
                    <svg style="width: 20px; height: 20px; margin-right: 8px;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                    </svg>
                    Step 1: Extracted from Your Files
                </div>
                <div class="answer-content">${parseMarkdownToHTML(result.extracted_info)}</div>
            </div>
        `;
    }

    // Show online search response if available (sequential or both mode)
    if (result.online_search_response) {
        const onlineHeader = result.extracted_info ? 'Step 2: Online Search Results' : 'Online Search';
        htmlContent += `
            <div class="answer-box" style="margin-bottom: 20px; border-left: 4px solid ${pantone295U};">
                <div class="answer-header" style="color: ${pantone295U};">
                    <svg style="width: 20px; height: 20px; margin-right: 8px;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9"></path>
                    </svg>
                    ${onlineHeader}
                </div>
                <div class="answer-content">${parseMarkdownToHTML(result.online_search_response)}</div>
            </div>
        `;
    }

    // Show final answer if available
    if (result.answer) {
        const answerHeader = result.extracted_info ? 'Step 3: Comparative Analysis' : 'Answer';
        htmlContent += `
            <div class="answer-box">
                <div class="answer-header" style="color: ${pantone1505U};">
                    <svg style="width: 20px; height: 20px; margin-right: 8px;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                    </svg>
                    ${answerHeader}
                </div>
                <div class="answer-content">${parseMarkdownToHTML(result.answer)}</div>
            </div>
        `;
    }

    // If no file results and we have an answer, just show the answer
    if (result.results.length === 0) {
        if (htmlContent) {
            searchResults.innerHTML = htmlContent + `
                <div class="search-info" style="margin-top: 20px; color: var(--text-secondary);">
                    Processed in ${result.processing_time}s
                </div>
            `;
        } else {
            searchResults.innerHTML = `
                <div class="no-results">
                    <p>No results found for "${result.query}"</p>
                    <p style="margin-top: 10px; font-size: 0.9rem;">Try different keywords or upload more documents.</p>
                </div>
            `;
        }
        return;
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

// Expose deleteDocument to global scope for inline onclick handlers
window.deleteDocument = deleteDocument;

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
function parseMarkdownToHTML(text) {
    if (!text) return '';

    // Escape HTML to prevent XSS
    let html = text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

    // Parse markdown tables first (before other replacements)
    html = parseMarkdownTables(html);

    // Code blocks: ```code``` or `code`
    html = html.replace(/```(.+?)```/gs, '<pre><code>$1</code></pre>');
    html = html.replace(/`(.+?)`/g, '<code>$1</code>');

    // Bold: **text** or __text__
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/__(.+?)__/g, '<strong>$1</strong>');

    // Italic: *text* or _text_ (but not in middle of words)
    html = html.replace(/\*([^\*]+?)\*/g, '<em>$1</em>');
    html = html.replace(/\b_([^_]+?)_\b/g, '<em>$1</em>');

    // Headers: # Heading
    html = html.replace(/^#### (.+)$/gm, '<h5>$1</h5>');
    html = html.replace(/^### (.+)$/gm, '<h4>$1</h4>');
    html = html.replace(/^## (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^# (.+)$/gm, '<h2>$1</h2>');

    // Links: [text](url)
    html = html.replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');

    // Unordered lists: - item or * item
    const lines = html.split('\n');
    let inList = false;
    let listType = null;
    const processedLines = [];

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        const unorderedMatch = line.match(/^[\*\-] (.+)$/);
        const orderedMatch = line.match(/^\d+\. (.+)$/);

        if (unorderedMatch) {
            if (!inList || listType !== 'ul') {
                if (inList) processedLines.push(`</${listType}>`);
                processedLines.push('<ul>');
                inList = true;
                listType = 'ul';
            }
            processedLines.push(`<li>${unorderedMatch[1]}</li>`);
        } else if (orderedMatch) {
            if (!inList || listType !== 'ol') {
                if (inList) processedLines.push(`</${listType}>`);
                processedLines.push('<ol>');
                inList = true;
                listType = 'ol';
            }
            processedLines.push(`<li>${orderedMatch[1]}</li>`);
        } else {
            if (inList) {
                processedLines.push(`</${listType}>`);
                inList = false;
                listType = null;
            }
            processedLines.push(line);
        }
    }
    if (inList) processedLines.push(`</${listType}>`);
    html = processedLines.join('\n');

    // Paragraphs: double line breaks (but skip tables, headers, lists, code)
    html = html.split('\n\n').map(para => {
        const trimmed = para.trim();
        if (trimmed &&
            !trimmed.startsWith('<h') &&
            !trimmed.startsWith('<ul') &&
            !trimmed.startsWith('<ol') &&
            !trimmed.startsWith('<li') &&
            !trimmed.startsWith('<table') &&
            !trimmed.startsWith('<pre') &&
            !trimmed.startsWith('<code')) {
            return `<p>${para.replace(/\n/g, '<br>')}</p>`;
        }
        return para;
    }).join('\n\n');

    return html;
}

function parseMarkdownTables(text) {
    const lines = text.split('\n');
    const result = [];
    let i = 0;

    while (i < lines.length) {
        const line = lines[i];

        // Check if this line looks like a table header
        if (line.includes('|') && i + 1 < lines.length) {
            const nextLine = lines[i + 1];

            // Check if next line is a separator (|---|---|)
            if (nextLine.match(/^\|?[\s\-:|]+\|[\s\-:|]+/)) {
                // This is a table!
                const tableLines = [line, nextLine];
                let j = i + 2;

                // Collect all table rows
                while (j < lines.length && lines[j].includes('|')) {
                    tableLines.push(lines[j]);
                    j++;
                }

                // Parse and convert table
                result.push(convertMarkdownTableToHTML(tableLines));
                i = j;
                continue;
            }
        }

        result.push(line);
        i++;
    }

    return result.join('\n');
}

function convertMarkdownTableToHTML(tableLines) {
    if (tableLines.length < 2) return tableLines.join('\n');

    const headerLine = tableLines[0];
    const dataLines = tableLines.slice(2); // Skip separator line

    // Parse header
    const headers = headerLine.split('|')
        .map(h => h.trim())
        .filter(h => h.length > 0);

    // Build table HTML
    let html = '<table class="markdown-table">\n<thead>\n<tr>\n';
    headers.forEach(header => {
        html += `<th>${header}</th>\n`;
    });
    html += '</tr>\n</thead>\n<tbody>\n';

    // Parse data rows
    dataLines.forEach(line => {
        const cells = line.split('|')
            .map(c => c.trim())
            .filter(c => c.length > 0);

        if (cells.length > 0) {
            html += '<tr>\n';
            cells.forEach(cell => {
                html += `<td>${cell}</td>\n`;
            });
            html += '</tr>\n';
        }
    });

    html += '</tbody>\n</table>';
    return html;
}

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

function showSearchLoading() {
    const searchMode = searchModeSelect.value;
    let loadingMessage = 'Generating answer...';
    let loadingSubtext = 'Please wait while we process your request';

    if (searchMode === 'online_only') {
        loadingMessage = 'Searching online...';
        loadingSubtext = 'Exploring the web for the latest information';
    } else if (searchMode === 'both') {
        loadingMessage = 'Searching files and online...';
        loadingSubtext = 'Combining information from multiple sources';
    } else {
        loadingMessage = 'Searching your documents...';
        loadingSubtext = 'Analyzing relevant content to generate an answer';
    }

    searchResults.innerHTML = `
        <div class="answer-skeleton">
            <div class="skeleton-header">
                <div class="skeleton-icon"></div>
                <div class="skeleton-title"></div>
            </div>
            <div class="skeleton-line"></div>
            <div class="skeleton-line"></div>
            <div class="skeleton-line"></div>
            <div class="skeleton-line"></div>
            <div class="skeleton-line"></div>
        </div>
        <div class="search-loading">
            <div class="search-loading-content">
                <div class="search-loading-spinner"></div>
                <div class="search-loading-text">${loadingMessage}</div>
                <div class="search-loading-subtext">${loadingSubtext}</div>
            </div>
        </div>
    `;
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
