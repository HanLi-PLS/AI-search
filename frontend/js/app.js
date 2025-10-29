// API Configuration
const API_BASE_URL = window.location.origin + '/api';

// Conversation History (stored in browser session)
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
    conversationHistory = [];
    searchResults.innerHTML = '<div class="no-results"><p>New conversation started. Ask me anything!</p></div>';
    searchInput.value = '';
    searchInput.focus();
    showToast('New conversation started', 'success');
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
                priority_order: priorityOrder,
                conversation_history: conversationHistory
            })
        });

        const result = await response.json();

        if (response.ok && result.success) {
            // Add this turn to conversation history
            conversationHistory.push({
                query: query,
                answer: result.answer || result.online_search_response || 'No answer provided'
            });

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
                        <button onclick="toggleSources(${i})" id="sourcesToggle${i}" style="font-size: 0.85rem; color: ${pantone295U}; background: none; border: none; cursor: pointer; display: flex; align-items: center; padding: 4px 0;">
                            <svg style="width: 16px; height: 16px; margin-right: 4px;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
                            </svg>
                            View ${result.results.length} Source(s)
                        </button>
                        <div id="sourcesContainer${i}" style="display: none; margin-top: 10px; font-size: 0.85rem;">
                            ${renderSources(result.results)}
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

// Helper function to render sources
function renderSources(sources) {
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

// Toggle sources visibility
function toggleSources(index) {
    const container = document.getElementById(`sourcesContainer${index}`);
    const button = document.getElementById(`sourcesToggle${index}`);
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
