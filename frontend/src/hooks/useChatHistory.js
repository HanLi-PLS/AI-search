import { useState, useEffect } from 'react';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

/**
 * Custom hook for managing conversation history with localStorage persistence and backend sync
 */
export const useChatHistory = () => {
  const [conversations, setConversations] = useState([]);
  const [currentConversationId, setCurrentConversationId] = useState(null);
  const [loading, setLoading] = useState(true);

  // Initialize from backend and localStorage
  useEffect(() => {
    const initializeConversations = async () => {
      try {
        // Fetch conversations from backend with auth token
        const token = localStorage.getItem('authToken');
        const headers = {
          'Content-Type': 'application/json'
        };
        if (token) {
          headers['Authorization'] = `Bearer ${token}`;
        }

        const response = await fetch(`${API_BASE_URL}/conversations`, {
          headers
        });
        const data = await response.json();

        // Get current user info from backend response
        let currentUserId = null;
        if (data.user_id) {
          currentUserId = data.user_id;
        }

        // Check if localStorage belongs to a different user
        const storedUserId = localStorage.getItem('chatHistory_userId');
        if (storedUserId && currentUserId && storedUserId !== String(currentUserId)) {
          // Different user logged in - clear old localStorage data
          console.log('Different user detected, clearing old chat history');
          localStorage.removeItem('chatHistory');
          localStorage.removeItem('currentConversationId');
          localStorage.setItem('chatHistory_userId', String(currentUserId));
        } else if (currentUserId && !storedUserId) {
          // First time storing user ID
          localStorage.setItem('chatHistory_userId', String(currentUserId));
        }

        let backendConversations = [];
        if (data.success && data.conversations && data.conversations.length > 0) {
          // Convert backend format to frontend format
          backendConversations = data.conversations.map(conv => ({
            id: conv.id,
            title: conv.title,
            history: [], // Will be loaded lazily when conversation is opened
            createdAt: conv.createdAt,
            updatedAt: conv.updatedAt,
            searchCount: conv.searchCount,
            fromBackend: true
          }));
        }

        // Get localStorage conversations (only if same user)
        const saved = localStorage.getItem('chatHistory');
        const localConversations = saved ? JSON.parse(saved) : [];
        const savedCurrentId = localStorage.getItem('currentConversationId');

        // Safely merge backend and localStorage conversations
        // - Backend conversations: Filtered by user_id (secure)
        // - localStorage conversations: Per-browser, safe to show
        // - After DB reset, old contaminated backend data won't appear
        // - localStorage preserves history for non-incognito users
        const conversationMap = new Map();

        // Add backend conversations first (these are filtered by user_id)
        backendConversations.forEach(conv => {
          conversationMap.set(conv.id, conv);
        });

        // Add localStorage conversations that don't exist in backend
        // Safe because localStorage is per-browser (not shared between users)
        localConversations.forEach(conv => {
          if (!conversationMap.has(conv.id)) {
            conversationMap.set(conv.id, { ...conv, fromBackend: false });
          }
        });

        const mergedConversations = Array.from(conversationMap.values())
          .sort((a, b) => new Date(b.updatedAt) - new Date(a.updatedAt));

        if (mergedConversations.length === 0) {
          // Create initial conversation if none exist
          const initialConv = {
            id: generateId(),
            title: 'New Conversation',
            history: [],
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
            fromBackend: false
          };
          setConversations([initialConv]);
          setCurrentConversationId(initialConv.id);
          saveToLocalStorage([initialConv], initialConv.id);
        } else {
          setConversations(mergedConversations);
          // Set current conversation to saved ID or first available
          const currentId = savedCurrentId && conversationMap.has(savedCurrentId)
            ? savedCurrentId
            : mergedConversations[0].id;
          setCurrentConversationId(currentId);

          // Always load from backend to ensure complete history
          // localStorage may have incomplete data (e.g., 1 search when backend has 3)
          loadConversationHistory(currentId);
        }
      } catch (error) {
        console.error('Error loading conversations from backend:', error);

        // Fallback to localStorage only
        const saved = localStorage.getItem('chatHistory');
        const savedConversations = saved ? JSON.parse(saved) : [];
        const savedCurrentId = localStorage.getItem('currentConversationId');

        if (savedConversations.length === 0) {
          const initialConv = {
            id: generateId(),
            title: 'New Conversation',
            history: [],
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString()
          };
          setConversations([initialConv]);
          setCurrentConversationId(initialConv.id);
          saveToLocalStorage([initialConv], initialConv.id);
        } else {
          setConversations(savedConversations);
          setCurrentConversationId(savedCurrentId || savedConversations[0].id);
        }
      } finally {
        setLoading(false);
      }
    };

    initializeConversations();
  }, []);

  const loadConversationHistory = async (conversationId) => {
    try {
      const token = localStorage.getItem('authToken');
      const headers = {
        'Content-Type': 'application/json'
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${API_BASE_URL}/conversations/${conversationId}`, {
        headers
      });
      const data = await response.json();

      if (data.success && data.history) {
        // Update conversation with loaded history from backend
        setConversations(prev => prev.map(conv => {
          if (conv.id === conversationId) {
            // MERGE backend history with existing localStorage history
            // This prevents losing localStorage-only searches when backend has incomplete data
            const backendHistory = data.history.map(item => ({
              query: item.query,
              answer: item.answer,
              timestamp: item.timestamp,
              reasoning_mode: item.reasoning_mode,
              search_mode: item.search_mode,
              // Add search_params object for UI display
              search_params: {
                search_mode: item.search_mode,
                reasoning_mode: item.reasoning_mode,
                top_k: item.top_k || 10,
                priority_order: item.priority_order
              },
              fromBackend: true
            }));

            // Get existing localStorage history
            const existingHistory = conv.history || [];

            // Merge: backend searches + localStorage-only searches
            const mergedHistory = [...backendHistory];
            const backendQueries = new Set(backendHistory.map(h => h.query));

            // Add localStorage searches that aren't in backend
            existingHistory.forEach(localSearch => {
              if (!backendQueries.has(localSearch.query)) {
                mergedHistory.push({ ...localSearch, fromBackend: false });
              }
            });

            // Sort by timestamp
            mergedHistory.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

            return {
              ...conv,
              history: mergedHistory
            };
          }
          return conv;
        }));
      }
    } catch (error) {
      console.error(`Error loading history for conversation ${conversationId}:`, error);
    }
  };

  const saveToLocalStorage = (convs, currentId) => {
    localStorage.setItem('chatHistory', JSON.stringify(convs));
    if (currentId) {
      localStorage.setItem('currentConversationId', currentId);
    }
  };

  const generateId = () => {
    return 'conv_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
  };

  const generateTitle = (query) => {
    return query.length > 50 ? query.substring(0, 47) + '...' : query;
  };

  const getCurrentConversation = () => {
    return conversations.find(c => c.id === currentConversationId);
  };

  const getCurrentHistory = () => {
    const conv = getCurrentConversation();
    return conv ? conv.history : [];
  };

  const createNewConversation = () => {
    const newConv = {
      id: generateId(),
      title: 'New Conversation',
      history: [],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    };

    const updated = [newConv, ...conversations];
    setConversations(updated);
    setCurrentConversationId(newConv.id);
    saveToLocalStorage(updated, newConv.id);

    return newConv.id;
  };

  const updateCurrentConversation = (conversationHistory) => {
    const updated = conversations.map(conv => {
      if (conv.id === currentConversationId) {
        return {
          ...conv,
          history: conversationHistory,
          title: conv.title === 'New Conversation' && conversationHistory.length > 0
            ? generateTitle(conversationHistory[0].query)
            : conv.title,
          updatedAt: new Date().toISOString()
        };
      }
      return conv;
    });

    setConversations(updated);
    saveToLocalStorage(updated, currentConversationId);
  };

  const switchConversation = async (conversationId) => {
    setCurrentConversationId(conversationId);
    saveToLocalStorage(conversations, conversationId);

    // Always load from backend to ensure we have complete history
    // localStorage may have incomplete data (e.g., 1 search when backend has 3)
    await loadConversationHistory(conversationId);
  };

  const deleteConversation = (conversationId) => {
    const updated = conversations.filter(c => c.id !== conversationId);

    if (conversationId === currentConversationId) {
      if (updated.length > 0) {
        setCurrentConversationId(updated[0].id);
        saveToLocalStorage(updated, updated[0].id);
      } else {
        // Create new conversation if all deleted
        const newConv = {
          id: generateId(),
          title: 'New Conversation',
          history: [],
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString()
        };
        setConversations([newConv]);
        setCurrentConversationId(newConv.id);
        saveToLocalStorage([newConv], newConv.id);
        return;
      }
    }

    setConversations(updated);
    saveToLocalStorage(updated, currentConversationId);
  };

  return {
    conversations,
    currentConversationId,
    loading,
    getCurrentHistory,
    createNewConversation,
    updateCurrentConversation,
    switchConversation,
    deleteConversation
  };
};
