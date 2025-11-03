/**
 * Chat History Management Module
 * Handles saving, loading, switching between conversations with localStorage persistence
 */

// Chat History State
let conversations = [];
let currentConversationId = null;

// Initialize chat history from localStorage
function initChatHistory() {
    const saved = localStorage.getItem('chatHistory');
    conversations = saved ? JSON.parse(saved) : [];
    currentConversationId = localStorage.getItem('currentConversationId') || null;

    // If there's a current conversation, load it
    if (currentConversationId) {
        const current = conversations.find(c => c.id === currentConversationId);
        if (current) {
            return current.history || [];
        }
    }

    return [];
}

// Save conversations to localStorage
function saveToLocalStorage() {
    console.log('saveToLocalStorage called');
    console.log('Saving conversations:', conversations);
    localStorage.setItem('chatHistory', JSON.stringify(conversations));
    console.log('Saved to localStorage:', localStorage.getItem('chatHistory'));
    if (currentConversationId) {
        localStorage.setItem('currentConversationId', currentConversationId);
        console.log('Saved currentConversationId:', currentConversationId);
    }
}

// Generate a unique ID
function generateId() {
    return 'conv_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}

// Generate a title from the first query
function generateTitle(query) {
    return query.length > 50 ? query.substring(0, 47) + '...' : query;
}

// Create a new conversation
function createNewConversation() {
    const newConv = {
        id: generateId(),
        title: 'New Conversation',
        history: [],
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString()
    };

    conversations.unshift(newConv); // Add to beginning
    currentConversationId = newConv.id;
    saveToLocalStorage();
    renderChatHistory();

    return [];
}

// Update current conversation
function updateCurrentConversation(conversationHistory) {
    console.log('ChatHistory.update called with:', conversationHistory);
    console.log('Current conversation ID:', currentConversationId);
    console.log('Existing conversations:', conversations);

    if (!currentConversationId) {
        // Create new conversation if none exists
        const newConv = {
            id: generateId(),
            title: conversationHistory.length > 0 ? generateTitle(conversationHistory[0].query) : 'New Conversation',
            history: conversationHistory,
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString()
        };
        conversations.unshift(newConv);
        currentConversationId = newConv.id;
        console.log('Created new conversation:', newConv);
    } else {
        const conv = conversations.find(c => c.id === currentConversationId);
        if (conv) {
            conv.history = conversationHistory;
            conv.updatedAt = new Date().toISOString();

            // Update title with first query if it's still "New Conversation"
            if (conv.title === 'New Conversation' && conversationHistory.length > 0) {
                conv.title = generateTitle(conversationHistory[0].query);
            }
            console.log('Updated existing conversation:', conv);
        }
    }

    saveToLocalStorage();
    console.log('Saved to localStorage, conversations:', conversations);
    renderChatHistory();
}

// Switch to a different conversation
function switchToConversation(conversationId) {
    const conv = conversations.find(c => c.id === conversationId);
    if (conv) {
        currentConversationId = conversationId;
        saveToLocalStorage();
        renderChatHistory();
        return conv.history || [];
    }
    return [];
}

// Delete a conversation
function deleteConversation(conversationId) {
    conversations = conversations.filter(c => c.id !== conversationId);

    // If we deleted the current conversation, switch to most recent or create new
    if (conversationId === currentConversationId) {
        if (conversations.length > 0) {
            currentConversationId = conversations[0].id;
            saveToLocalStorage();
            renderChatHistory();
            return conversations[0].history || [];
        } else {
            currentConversationId = null;
            saveToLocalStorage();
            renderChatHistory();
            return [];
        }
    }

    saveToLocalStorage();
    renderChatHistory();
    return null; // Didn't switch
}

// Format date for display
function formatDate(isoString) {
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} min ago`;
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;

    return date.toLocaleDateString();
}

// Render the chat history sidebar
function renderChatHistory() {
    const listElement = document.getElementById('chatHistoryList');
    if (!listElement) return;

    if (conversations.length === 0) {
        listElement.innerHTML = '<div class="no-chat-history"><p>No chat history yet.<br>Start a conversation!</p></div>';
        return;
    }

    listElement.innerHTML = conversations.map(conv => `
        <div class="chat-history-item ${conv.id === currentConversationId ? 'active' : ''}"
             data-conversation-id="${conv.id}">
            <div class="chat-history-content" onclick="switchChat('${conv.id}')">
                <div class="chat-history-title">${escapeHtml(conv.title)}</div>
                <div class="chat-history-date">${formatDate(conv.updatedAt)}</div>
                <div class="chat-history-count">${conv.history.length} message${conv.history.length !== 1 ? 's' : ''}</div>
            </div>
            <button class="chat-history-delete" onclick="deleteChat('${conv.id}')" title="Delete conversation">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
            </button>
        </div>
    `).join('');
}

// Global functions for onclick handlers
window.switchChat = function(conversationId) {
    const history = switchToConversation(conversationId);
    if (window.loadConversationHistory) {
        window.loadConversationHistory(history);
    }
};

window.deleteChat = function(conversationId) {
    if (confirm('Delete this conversation? This cannot be undone.')) {
        const history = deleteConversation(conversationId);
        if (history !== null && window.loadConversationHistory) {
            window.loadConversationHistory(history);
        }
    }
};

// Toggle sidebar visibility
function toggleSidebar() {
    const button = document.getElementById('toggleSidebarButton');

    console.log('toggleSidebar called');

    if (document.body.classList.contains('sidebar-collapsed')) {
        // Show sidebar
        document.body.classList.remove('sidebar-collapsed');
        localStorage.setItem('sidebarCollapsed', 'false');
        button.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
            </svg>
        `;
        console.log('Sidebar expanded');
    } else {
        // Hide sidebar
        document.body.classList.add('sidebar-collapsed');
        localStorage.setItem('sidebarCollapsed', 'true');
        button.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 5l7 7-7 7M5 5l7 7-7 7" />
            </svg>
        `;
        console.log('Sidebar collapsed');
    }
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Export functions for use in main app
window.ChatHistory = {
    init: initChatHistory,
    createNew: createNewConversation,
    update: updateCurrentConversation,
    switchTo: switchToConversation,
    delete: deleteConversation,
    render: renderChatHistory,
    toggleSidebar: toggleSidebar
};
