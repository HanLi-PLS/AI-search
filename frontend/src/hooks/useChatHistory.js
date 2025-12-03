import { useState, useEffect } from 'react';

/**
 * Custom hook for managing conversation history with localStorage persistence
 */
export const useChatHistory = () => {
  const [conversations, setConversations] = useState([]);
  const [currentConversationId, setCurrentConversationId] = useState(null);

  // Initialize from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('chatHistory');
    const savedConversations = saved ? JSON.parse(saved) : [];
    const savedCurrentId = localStorage.getItem('currentConversationId');

    if (savedConversations.length === 0) {
      // Create initial conversation
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
  }, []);

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

  const switchConversation = (conversationId) => {
    setCurrentConversationId(conversationId);
    saveToLocalStorage(conversations, conversationId);
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
    getCurrentHistory,
    createNewConversation,
    updateCurrentConversation,
    switchConversation,
    deleteConversation
  };
};
