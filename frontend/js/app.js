// API Configuration
const API_BASE_URL = window.location.origin + '/api';

// Conversation History (managed by chat-history.js module)
let conversationHistory = [];

// DOM Elements
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const uploadProgress = document.getElementById('uploadProgress');
const progressFill = document.getElementById('progressFill');
const uploadStatus = document.getElementById('uploadStatus');
const uploadResults = document.getElementById('uploadResults');
const searchInput = document.getElementById('searchInput');
const searchButton = document.getElementById('searchButton');
const newConversationButton = document.getElementById('newConversationButton');
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
newConversationButton.addEventListener('click', startNewConversation);
refreshButton.addEventListener('click', loadDocuments);
searchModeSelect.addEventListener('change', handleSearchModeChange);

// Chat History Event Listeners
const toggleSidebarButton = document.getElementById('toggleSidebarButton');
if (toggleSidebarButton) {
    toggleSidebarButton.addEventListener('click', () => window.ChatHistory.toggleSidebar());
}

const openSidebarButton = document.getElementById('openSidebarButton');
if (openSidebarButton) {
    openSidebarButton.addEventListener('click', () => window.ChatHistory.toggleSidebar());
}

// Handle search mode change to show/hide priority order
function handleSearchModeChange() {
    const searchMode = searchModeSelect.value;
    if (searchMode === 'both') {
        priorityOrderLabel.style.display = 'inline-block';
    } else {
        priorityOrderLabel.style.display = 'none';
    }
}

// Start a new conversation
function startNewConversation() {
    conversationHistory = window.ChatHistory.createNew();
    searchResults.innerHTML = '<div class="no-results"><p>New conversation started. Ask me anything!</p></div>';
    searchInput.value = '';
    searchInput.focus();
    showToast('New conversation started', 'success');
}

// Load conversation history (called when switching chats)
window.loadConversationHistory = function(history) {
    conversationHistory = history;
    if (history.length === 0) {
        searchResults.innerHTML = '<div class="no-results"><p>Start a conversation. Ask me anything!</p></div>';
    } else {
        // Re-render the conversation
        const lastQuery = history[history.length - 1].query;
        const lastAnswer = history[history.length - 1].answer;
        displaySearchResults({ answer: lastAnswer, query: lastQuery });
    }
    searchInput.value = '';
    searchInput.focus();
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Initialize chat history
    conversationHistory = window.ChatHistory.init();
    window.ChatHistory.render();

    // Load initial conversation if exists
    if (conversationHistory.length > 0) {
        window.loadConversationHistory(conversationHistory);
    }

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
    uploadStatus.textContent = `Preparing to upload ${files.length} file(s)...`;

    const totalFiles = files.length;
    let completed = 0;

    for (const file of files) {
        // Create upload item immediately to show status
        const uploadItemId = `upload-${Date.now()}-${Math.random()}`;
        createUploadStatusItem(uploadItemId, file.name, 'uploading');

        try {
            const formData = new FormData();
            formData.append('file', file);

            // Add conversation_id to associate file with current conversation
            const conversationId = window.ChatHistory.getCurrentId();
            if (conversationId) {
                formData.append('conversation_id', conversationId);
            }

            // Show uploading stage
            updateUploadStatus(uploadItemId, 'uploading', `Uploading ${file.name}...`);

            const uploadStartTime = Date.now();

            // After 1.5 seconds, assume upload is done and processing has started
            const processingTimeout = setTimeout(() => {
                const elapsed = ((Date.now() - uploadStartTime) / 1000).toFixed(1);
                updateUploadStatus(uploadItemId, 'processing', `Processing ${file.name}... (${elapsed}s elapsed)`);
            }, 1500);

            const response = await fetch(`${API_BASE_URL}/upload`, {
                method: 'POST',
                body: formData
            });

            // Clear the timeout if fetch completes before 1.5s
            clearTimeout(processingTimeout);

            const result = await response.json();

            if (response.ok && result.success) {
                updateUploadStatus(uploadItemId, 'complete', `${result.chunks_created} chunks created in ${result.processing_time}s`);
                showToast(`${file.name} processed successfully`, 'success');
            } else {
                updateUploadStatus(uploadItemId, 'error', result.detail || result.message || 'Upload failed');
                showToast(`Failed to process ${file.name}`, 'error');
            }

        } catch (error) {
            console.error('Upload error:', error);
            updateUploadStatus(uploadItemId, 'error', error.message);
            showToast(`Error uploading ${file.name}`, 'error');
        }

        completed++;
        const progress = (completed / totalFiles) * 100;
        progressFill.style.width = `${progress}%`;
        uploadStatus.textContent = `Processed ${completed} of ${totalFiles} file(s)`;
    }

    // Reset file input
    fileInput.value = '';

    // Refresh documents list
    setTimeout(() => {
        loadDocuments();
    }, 1000);
}

function createUploadStatusItem(itemId, fileName, stage) {
    const resultItem = document.createElement('div');
    resultItem.id = itemId;
    resultItem.className = 'upload-result-item';

    resultItem.innerHTML = `
        <div class="upload-result-info">
            <div class="upload-result-name">${fileName}</div>
            <div class="upload-result-stage" id="${itemId}-stage"></div>
            <div class="upload-result-details" id="${itemId}-details"></div>
        </div>
        <div class="upload-result-icon-container" id="${itemId}-icon">
            <div class="upload-spinner"></div>
        </div>
    `;

    uploadResults.appendChild(resultItem);
    updateUploadStatus(itemId, stage, '');
}

function updateUploadStatus(itemId, stage, message) {
    const item = document.getElementById(itemId);
    if (!item) return;

    const stageElement = document.getElementById(`${itemId}-stage`);
    const detailsElement = document.getElementById(`${itemId}-details`);
    const iconContainer = document.getElementById(`${itemId}-icon`);

    // Update stage label and icon
    if (stage === 'uploading') {
        stageElement.innerHTML = '<span style="color: #3B82F6; font-weight: 600;">📤 Uploading...</span>';
        iconContainer.innerHTML = '<div class="upload-spinner"></div>';
        item.className = 'upload-result-item uploading';
    } else if (stage === 'processing') {
        stageElement.innerHTML = '<span style="color: #F59E0B; font-weight: 600;">⚙️ Processing...</span>';
        iconContainer.innerHTML = '<div class="upload-spinner processing"></div>';
        item.className = 'upload-result-item processing';
    } else if (stage === 'complete') {
        stageElement.innerHTML = '<span style="color: #10B981; font-weight: 600;">✅ Complete</span>';
        iconContainer.innerHTML = `
            <svg class="upload-result-icon success-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
            </svg>
        `;
        item.className = 'upload-result-item complete';
    } else if (stage === 'error') {
        stageElement.innerHTML = '<span style="color: #EF4444; font-weight: 600;">❌ Error</span>';
        iconContainer.innerHTML = `
            <svg class="upload-result-icon error-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
            </svg>
        `;
        item.className = 'upload-result-item error';
    }

    // Update details message
    if (message) {
        detailsElement.textContent = message;
    }
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

        // Get current conversation ID to filter files
        const conversationId = window.ChatHistory.getCurrentId();

        const response = await fetch(`${API_BASE_URL}/search`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                query: query,
                top_k: parseInt(topKSelect.value),
                search_mode: searchMode,
                priority_order: priorityOrder,
                conversation_history: conversationHistory,
                conversation_id: conversationId
            })
        });

        const result = await response.json();

        if (response.ok && result.success) {
            // Add this turn to conversation history
            conversationHistory.push({
                query: query,
                answer: result.answer || result.online_search_response || 'No answer provided'
            });

            // Save to localStorage and update chat history sidebar
            window.ChatHistory.update(conversationHistory);

            // Clear search input
            searchInput.value = '';

            // Display results as chat interface
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

// Helper function to escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}


function displaySearchResults(result) {
    // Display as chat interface showing all conversation history
    let htmlContent = '<div class="chat-container">';

    // Pantone colors
    const pantone295U = '#003DA5';
    const pantone1505U = '#FF6900';
    const extractGreen = '#059669';
    const autoModePurple = '#7C3AED';

    // Render each conversation turn as chat messages
    for (let i = 0; i < conversationHistory.length; i++) {
        const turn = conversationHistory[i];
        const isLatest = (i === conversationHistory.length - 1);

        // USER MESSAGE
        htmlContent += `
            <div class="chat-message user-message">
                <div class="message-content">
                    <div class="message-bubble user-bubble">
                        <div class="message-avatar">
                            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path>
                            </svg>
                        </div>
                        <div class="message-text">${escapeHtml(turn.query)}</div>
                    </div>
                </div>
            </div>
        `;

        // AI MESSAGE
        htmlContent += `<div class="chat-message ai-message"><div class="message-content"><div class="message-bubble ai-bubble">`;
        htmlContent += `
            <div class="message-avatar">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"></path>
                </svg>
            </div>
            <div class="message-text">
        `;

        // For latest message, show full details with result object
        if (isLatest && result) {
            // Show mode selection info if auto mode
            if (result.selected_mode && result.mode_reasoning) {
                const modeDisplayNames = {
                    'files_only': 'Files Only',
                    'online_only': 'Online Only',
                    'both': 'Both (Files + Online)',
                    'sequential_analysis': 'Sequential Analysis'
                };
                const selectedModeDisplay = modeDisplayNames[result.selected_mode] || result.selected_mode;

                htmlContent += `
                    <div style="margin-bottom: 12px; padding: 10px; background: linear-gradient(135deg, #F3E8FF, #EDE9FE); border-left: 3px solid ${autoModePurple}; border-radius: 6px; font-size: 0.9rem;">
                        <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 4px;">
                            <strong style="color: ${autoModePurple}; font-size: 0.85rem;">Mode:</strong>
                            <span style="padding: 2px 6px; background: ${autoModePurple}; color: white; border-radius: 3px; font-size: 0.75rem; font-weight: 600;">${selectedModeDisplay}</span>
                        </div>
                        <div style="color: #4B5563; font-size: 0.8rem;">${result.mode_reasoning}</div>
                    </div>
                `;
            }

            // Show extracted info if available
            if (result.extracted_info) {
                htmlContent += `
                    <div style="margin-bottom: 12px; padding: 12px; border-left: 3px solid ${extractGreen}; background: #F0FDF4; border-radius: 6px;">
                        <div style="font-weight: 600; color: ${extractGreen}; margin-bottom: 8px; font-size: 0.9rem;">📄 Step 1: Extracted from Files</div>
                        <div style="font-size: 0.9rem;">${parseMarkdownToHTML(result.extracted_info)}</div>
                    </div>
                `;
            }

            // Show online search response
            if (result.online_search_response) {
                const onlineHeader = result.extracted_info ? 'Step 2: Online Search' : 'Online Search';
                htmlContent += `
                    <div style="margin-bottom: 12px; padding: 12px; border-left: 3px solid ${pantone295U}; background: #EFF6FF; border-radius: 6px;">
                        <div style="font-weight: 600; color: ${pantone295U}; margin-bottom: 8px; font-size: 0.9rem;">🌐 ${onlineHeader}</div>
                        <div style="font-size: 0.9rem;">${parseMarkdownToHTML(result.online_search_response)}</div>
                    </div>
                `;
            }

            // Show final answer
            if (result.answer) {
                const answerHeader = result.extracted_info ? 'Step 3: Comparative Analysis' : '';
                if (answerHeader) {
                    htmlContent += `<div style="font-weight: 600; color: ${pantone1505U}; margin-bottom: 8px; font-size: 0.9rem;">✨ ${answerHeader}</div>`;
                }
                htmlContent += `<div style="font-size: 0.95rem; line-height: 1.7;">${parseMarkdownToHTML(result.answer)}</div>`;
            }

            // Show sources toggle for latest message
            if (result.results && result.results.length > 0) {
                htmlContent += `
                    <div style="margin-top: 15px; padding-top: 12px; border-top: 1px solid #E5E7EB;">
                        <button onclick="toggleChatSources(${i})" id="chatSourcesToggle${i}" style="font-size: 0.85rem; color: ${pantone295U}; background: none; border: none; cursor: pointer; display: flex; align-items: center; padding: 4px 0;">
                            <svg style="width: 16px; height: 16px; margin-right: 4px;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
                            </svg>
                            View ${result.results.length} Source(s)
                        </button>
                        <div id="chatSourcesContainer${i}" style="display: none; margin-top: 10px; font-size: 0.85rem;">
                            ${renderChatSources(result.results)}
                        </div>
                    </div>
                `;
            }
        } else {
            // For older messages, show answer summary
            const answerText = turn.answer || 'No response';
            const truncated = answerText.length > 300 ? answerText.substring(0, 300) + '...' : answerText;
            htmlContent += `<div style="font-size: 0.95rem; line-height: 1.7; color: #6B7280;">${parseMarkdownToHTML(truncated)}</div>`;
        }

        htmlContent += `
            </div>
        </div></div></div>`;
    }

    htmlContent += '</div>'; // Close chat-container

    searchResults.innerHTML = htmlContent;

    // Scroll to bottom to show latest message
    setTimeout(() => {
        searchResults.scrollTop = searchResults.scrollHeight;
    }, 100);
}

// Helper function to render sources in chat
function renderChatSources(sources) {
    let html = '';
    sources.forEach((item, idx) => {
        const score = Math.round(item.score * 100);
        const fileName = item.metadata.file_name || 'Unknown';
        const fileType = item.metadata.file_type || '';
        const page = item.metadata.page ? `Page ${item.metadata.page}` : '';

        let content = item.content;
        if (content.length > 300) {
            content = content.substring(0, 300) + '...';
        }

        const retrievalMethod = item.retrieval_method || 'Dense';
        const badgeText = retrievalMethod === 'Both' ? 'Dense + BM25' : retrievalMethod;

        html += `
            <div style="margin-bottom: 10px; padding: 10px; background: #F9FAFB; border-radius: 6px; border: 1px solid #E5E7EB;">
                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 6px;">
                    <div style="font-weight: 600; color: #374151; font-size: 0.9rem;">${fileName}</div>
                    <div style="display: flex; gap: 6px; align-items: center;">
                        <span style="font-size: 0.7rem; padding: 2px 6px; background: #E0E7FF; color: #3730A3; border-radius: 3px;">${badgeText}</span>
                        <span style="color: #059669; font-weight: 600; font-size: 0.8rem;">${score}%</span>
                    </div>
                </div>
                <div style="color: #6B7280; font-size: 0.75rem; margin-bottom: 6px;">
                    ${fileType} ${page ? `• ${page}` : ''}
                </div>
                <div style="color: #4B5563; line-height: 1.5; font-size: 0.85rem;">${content}</div>
            </div>
        `;
    });
    return html;
}

// Toggle chat sources visibility
function toggleChatSources(index) {
    const container = document.getElementById(`chatSourcesContainer${index}`);
    const button = document.getElementById(`chatSourcesToggle${index}`);
    if (container) {
        const isHidden = container.style.display === 'none';
        container.style.display = isHidden ? 'block' : 'none';
        // Rotate the arrow icon
        const svg = button.querySelector('svg');
        if (svg) {
            svg.style.transform = isHidden ? 'rotate(180deg)' : 'rotate(0deg)';
            svg.style.transition = 'transform 0.3s ease';
        }
    }
}

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
