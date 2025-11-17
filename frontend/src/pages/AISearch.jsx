import { useState, useEffect, useRef, memo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { uploadFile, searchDocuments, getDocuments, deleteDocument, getJobStatus } from '../services/api';
import { useChatHistory } from '../hooks/useChatHistory';
import { parseMarkdownToHTML, formatFileSize, formatDate } from '../utils/markdown';
import './AISearch.css';

function AISearch() {
  const navigate = useNavigate();
  const {
    conversations,
    currentConversationId,
    getCurrentHistory,
    createNewConversation,
    updateCurrentConversation,
    switchConversation,
    deleteConversation
  } = useChatHistory();

  const [conversationHistory, setConversationHistory] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [documents, setDocuments] = useState([]);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [topK, setTopK] = useState(10);
  const [searchMode, setSearchMode] = useState('auto');
  const [reasoningMode, setReasoningMode] = useState('non_reasoning');
  const [priorityOrder, setPriorityOrder] = useState('online_first');
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState({});
  const [dragOver, setDragOver] = useState(false);

  const fileInputRef = useRef(null);
  const searchResultsRef = useRef(null);
  const pollingTimersRef = useRef(new Map()); // Track active polling timers

  useEffect(() => {
    const history = getCurrentHistory();
    setConversationHistory(history);
  }, [currentConversationId]);

  useEffect(() => {
    // Only load documents when we have a valid conversation ID
    if (currentConversationId) {
      loadDocuments();
    }
  }, [currentConversationId]);

  // Cleanup polling timers on unmount
  useEffect(() => {
    return () => {
      // Clear all active polling timers
      pollingTimersRef.current.forEach((timerId) => {
        clearTimeout(timerId);
      });
      pollingTimersRef.current.clear();
    };
  }, []);

  const loadDocuments = async () => {
    // Don't load documents if we don't have a conversation ID yet
    if (!currentConversationId) {
      setDocuments([]);
      return;
    }

    try {
      // Always filter by current conversation
      const result = await getDocuments(currentConversationId);
      if (result.success) {
        setDocuments(result.documents || []);
      }
    } catch (error) {
      console.error('Failed to load documents:', error);
    }
  };

  const pollJobStatus = useCallback(async (jobId, fileId, fileName) => {
    const maxAttempts = 300; // Poll for up to 5 minutes (300 * 1s = 300s)
    let attempts = 0;

    const poll = async () => {
      try {
        const status = await getJobStatus(jobId);

        if (status.status === 'processing') {
          const progress = status.total_files > 0
            ? `Processing... (${status.processed_files}/${status.total_files} files, ${status.total_chunks} chunks)`
            : 'Processing...';

          setUploadProgress(prev => ({
            ...prev,
            [fileId]: {
              name: fileName,
              status: 'processing',
              message: progress
            }
          }));

          attempts++;
          if (attempts < maxAttempts) {
            const timerId = setTimeout(poll, 1000);
            pollingTimersRef.current.set(fileId, timerId);
          } else {
            pollingTimersRef.current.delete(fileId);
          }
        } else if (status.status === 'completed') {
          pollingTimersRef.current.delete(fileId);
          const successCount = status.processed_files - status.failed_files;

          // Build message with failed/skipped files info if any
          let message;
          if (status.total_files > 1) {
            message = `✓ Complete: ${successCount}/${status.total_files} files processed, ${status.total_chunks} chunks created`;

            // Separate skipped files from actual failures
            if (status.failed_files > 0 && status.file_results) {
              const failedFiles = status.file_results.filter(r => !r.success);

              // Categorize into skipped (expected) vs failed (unexpected errors)
              const skippedTypes = ['skipped_system_file', 'unsupported_file_type', 'nested_zip'];
              const skipped = failedFiles.filter(f => skippedTypes.includes(f.error_type));
              const actuallyFailed = failedFiles.filter(f => !skippedTypes.includes(f.error_type));

              // Add skipped files info
              if (skipped.length > 0) {
                const skippedList = skipped.map(f => `${f.filename}: ${f.error}`).join('; ');
                message += `\nℹ️ ${skipped.length} skipped: ${skippedList}`;
              }

              // Add failed files info
              if (actuallyFailed.length > 0) {
                const failedList = actuallyFailed.map(f => `${f.filename}: ${f.error}`).join('; ');
                message += `\n⚠️ ${actuallyFailed.length} failed: ${failedList}`;
              }
            }
          } else {
            message = `✓ Complete: ${status.total_chunks} chunks created`;
          }

          // Determine status - only show warning if there are actual failures (not just skipped files)
          const skippedTypes = ['skipped_system_file', 'unsupported_file_type', 'nested_zip'];
          const actuallyFailed = status.file_results ?
            status.file_results.filter(r => !r.success && !skippedTypes.includes(r.error_type)).length : 0;
          const displayStatus = actuallyFailed > 0 ? 'warning' : 'complete';

          setUploadProgress(prev => ({
            ...prev,
            [fileId]: {
              name: fileName,
              status: displayStatus,
              message
            }
          }));
          loadDocuments();
          const clearTimerId = setTimeout(() => {
            setUploadProgress(prev => {
              const { [fileId]: _, ...rest } = prev;
              return rest;
            });
            pollingTimersRef.current.delete(fileId);
          }, actuallyFailed > 0 ? 10000 : 5000);
          pollingTimersRef.current.set(fileId, clearTimerId);
        } else if (status.status === 'failed') {
          pollingTimersRef.current.delete(fileId);
          setUploadProgress(prev => ({
            ...prev,
            [fileId]: {
              name: fileName,
              status: 'error',
              message: status.error_message || 'Processing failed'
            }
          }));
        }
      } catch (error) {
        console.error('Error polling job status:', error);
        setUploadProgress(prev => ({
          ...prev,
          [fileId]: {
            name: fileName,
            status: 'error',
            message: 'Failed to check status'
          }
        }));
      }
    };

    poll();
  }, [loadDocuments]);

  const handleFileSelect = useCallback(async (files) => {
    const fileArray = Array.from(files);
    setUploading(true);

    for (const file of fileArray) {
      const fileId = `upload-${Date.now()}-${Math.random()}`;
      setUploadProgress(prev => ({
        ...prev,
        [fileId]: { name: file.name, status: 'uploading', message: 'Uploading...' }
      }));

      try {
        const result = await uploadFile(file, currentConversationId);
        if (result.success && result.job_id) {
          // File uploaded successfully, now processing in background
          setUploadProgress(prev => ({
            ...prev,
            [fileId]: {
              name: file.name,
              status: 'processing',
              message: 'File uploaded. Processing in background...'
            }
          }));
          // Start polling for job status
          pollJobStatus(result.job_id, fileId, file.name);
        } else {
          throw new Error(result.message || 'Upload failed');
        }
      } catch (error) {
        setUploadProgress(prev => ({
          ...prev,
          [fileId]: { name: file.name, status: 'error', message: error.message }
        }));
      }
    }
    setUploading(false);
  }, [currentConversationId, pollJobStatus]);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files.length > 0) {
      handleFileSelect(e.dataTransfer.files);
    }
  }, [handleFileSelect]);

  const handleSearch = useCallback(async (e) => {
    e.preventDefault();
    if (!searchQuery.trim() || loading) return;
    setLoading(true);

    try {
      const priority = priorityOrder === 'online_first' ? ['online_search', 'files'] : ['files', 'online_search'];
      const result = await searchDocuments({
        query: searchQuery.trim(),
        top_k: topK,
        search_mode: searchMode,
        reasoning_mode: reasoningMode,
        priority_order: priority,
        conversation_history: conversationHistory,
        conversation_id: currentConversationId
      });

      if (result.success) {
        const newTurn = {
          query: searchQuery,
          answer: result.answer || 'No answer provided',
          extracted_info: result.extracted_info || null,
          online_search_response: result.online_search_response || null,
          selected_mode: result.selected_mode || null,
          mode_reasoning: result.mode_reasoning || null,
          results: result.results || [],
          // Add search parameters for display
          search_params: {
            top_k: topK,
            search_mode: searchMode,
            reasoning_mode: reasoningMode,
            priority_order: priorityOrder
          }
        };
        const updated = [...conversationHistory, newTurn];
        setConversationHistory(updated);
        updateCurrentConversation(updated);
        setSearchQuery('');
        setTimeout(() => {
          if (searchResultsRef.current) {
            searchResultsRef.current.scrollTop = searchResultsRef.current.scrollHeight;
          }
        }, 100);
      }
    } catch (error) {
      console.error('Search error:', error);
      alert('Search failed: ' + error.message);
    } finally {
      setLoading(false);
    }
  }, [searchQuery, loading, topK, searchMode, reasoningMode, priorityOrder, conversationHistory, currentConversationId, updateCurrentConversation, searchResultsRef]);

  const handleNewConversation = useCallback(() => {
    createNewConversation();
    setConversationHistory([]);
    setSearchQuery('');
  }, [createNewConversation]);

  const handleDeleteDocument = useCallback(async (fileId, fileName) => {
    if (!confirm(`Delete "${fileName}"?`)) return;
    try {
      const result = await deleteDocument(fileId);
      if (result.success) {
        loadDocuments();
      }
    } catch (error) {
      alert('Failed to delete document: ' + error.message);
    }
  }, [loadDocuments]);

  return (
    <div className={`ai-search-container ${sidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
      {sidebarCollapsed && (
        <button className="open-sidebar-floating-button" onClick={() => setSidebarCollapsed(false)} title="Open Chat History">
          ☰
        </button>
      )}

      <aside className="chat-history-sidebar">
        <div className="sidebar-header">
          <h3>Chat History</h3>
          <button className="toggle-sidebar-button" onClick={() => setSidebarCollapsed(!sidebarCollapsed)} title="Toggle sidebar">
            {sidebarCollapsed ? '→' : '←'}
          </button>
        </div>
        <div className="chat-history-list">
          {conversations.length === 0 ? (
            <div className="no-chat-history"><p>No chat history yet.<br/>Start a conversation!</p></div>
          ) : (
            conversations.map(conv => (
              <div key={conv.id} className={`chat-history-item ${conv.id === currentConversationId ? 'active' : ''}`} onClick={() => switchConversation(conv.id)}>
                <div className="chat-history-content">
                  <div className="chat-history-title">{conv.title}</div>
                  <div className="chat-history-date">{formatDate(conv.updatedAt)}</div>
                  <div className="chat-history-count">{conv.history.length} message{conv.history.length !== 1 ? 's' : ''}</div>
                </div>
                <button className="chat-history-delete" onClick={(e) => { e.stopPropagation(); if (confirm('Delete this conversation?')) deleteConversation(conv.id); }} title="Delete conversation">
                  🗑️
                </button>
              </div>
            ))
          )}
        </div>
      </aside>

      <main className="main-content">
        <header className="header">
          <button className="back-home-button" onClick={() => navigate('/')}>
            ← Back to Home
          </button>
          <h1>🔍 AI Document Search</h1>
          <p className="subtitle">Upload documents and search with AI-powered semantic search</p>
        </header>

        <section className="upload-section">
          <h2>Upload Documents</h2>
          <div
            className={`upload-area ${dragOver ? 'drag-over' : ''}`}
            onClick={() => fileInputRef.current?.click()}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
          >
            <div className="upload-content">
              <div className="upload-icon">☁️</div>
              <p className="upload-text">Drag & drop files here or click to browse</p>
              <p className="upload-subtext">Supported: PDF, DOCX, TXT, MD, CSV, XLSX, PPTX, HTML, JSON</p>
              <p className="upload-subtext" style={{ color: 'var(--pantone-1505u)', fontWeight: '600', marginTop: '5px' }}>
                💡 Tip: Upload ZIP files for bulk processing with parallel embedding generation
              </p>
              <input ref={fileInputRef} type="file" multiple accept=".pdf,.txt,.md,.docx,.doc,.xlsx,.xls,.csv,.pptx,.ppt,.html,.htm,.json,.eml,.zip"
                onChange={(e) => handleFileSelect(e.target.files)} style={{ display: 'none' }} />
            </div>
          </div>

          {Object.keys(uploadProgress).length > 0 && (
            <div className="upload-results">
              {Object.entries(uploadProgress).map(([id, progress]) => (
                <div key={id} className={`upload-result-item ${progress.status}`}>
                  <div className="upload-result-info">
                    <div className="upload-result-name">{progress.name}</div>
                    <div className="upload-result-message">{progress.message}</div>
                  </div>
                  <div className="upload-result-icon">
                    {progress.status === 'uploading' && '⏳'}
                    {progress.status === 'processing' && '⚙️'}
                    {progress.status === 'complete' && '✅'}
                    {progress.status === 'warning' && '⚠️'}
                    {progress.status === 'error' && '❌'}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="search-section">
          <h2>Search Documents</h2>
          <form onSubmit={handleSearch} className="search-box">
            <input type="text" className="search-input" placeholder="Enter your search query..." value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)} disabled={loading} />
            <button type="submit" className="search-button" disabled={loading || !searchQuery.trim()}>
              {loading ? '⏳ Searching...' : '🔍 Search'}
            </button>
            <button type="button" className="new-conversation-button" onClick={handleNewConversation} title="Start a new conversation">
              ➕ New Chat
            </button>
          </form>

          <div className="search-filters">
            <label>Results: <select value={topK} onChange={(e) => setTopK(parseInt(e.target.value))} className="filter-select">
                <option value="10">10</option><option value="20">20</option><option value="50">50</option>
                <option value="100">100</option><option value="200">200</option>
              </select></label>
            <label>Search Mode: <select value={searchMode} onChange={(e) => setSearchMode(e.target.value)} className="filter-select">
                <option value="auto">Intelligent (Auto-select)</option><option value="files_only">Files Only</option>
                <option value="online_only">Online Only</option><option value="both">Both (Files + Online)</option>
                <option value="sequential_analysis">Sequential Analysis (Extract → Compare)</option>
              </select></label>
            {searchMode === 'both' && (
              <label>Priority: <select value={priorityOrder} onChange={(e) => setPriorityOrder(e.target.value)} className="filter-select">
                  <option value="online_first">Online First</option><option value="files_first">Files First</option>
                </select></label>
            )}
            {searchMode !== 'files_only' && (
              <label>Reasoning Mode: <select value={reasoningMode} onChange={(e) => setReasoningMode(e.target.value)} className="filter-select">
                  <option value="non_reasoning">Non-Reasoning (gpt-4.1)</option><option value="reasoning">Reasoning (o4-mini)</option>
                  <option value="reasoning_gpt5">Reasoning (chatgpt-4o-latest)</option>
                  <option value="deep_research">Deep Research (o3-deep-research)</option>
                </select></label>
            )}
          </div>

          <div ref={searchResultsRef} className="search-results">
            {conversationHistory.length === 0 ? (
              <div className="no-results"><p>Start a conversation. Ask me anything!</p></div>
            ) : (
              <ChatMessages history={conversationHistory} />
            )}
          </div>
        </section>

        <section className="documents-section">
          <div className="section-header">
            <h2>Uploaded Documents</h2>
            <button className="refresh-button" onClick={loadDocuments}>🔄 Refresh</button>
          </div>
          <div className="documents-list">
            {documents.length === 0 ? (
              <div className="no-results">No documents uploaded yet</div>
            ) : (
              documents.map(doc => (
                <div key={doc.file_id} className="document-item">
                  <div className="document-info">
                    <div className="document-name">{doc.file_name}</div>
                    <div className="document-meta">
                      {doc.file_type} • {formatFileSize(doc.file_size)} • {doc.chunk_count} chunks • Uploaded {new Date(doc.upload_date).toLocaleDateString()}
                    </div>
                  </div>
                  <button className="delete-button" onClick={() => handleDeleteDocument(doc.file_id, doc.file_name)}>Delete</button>
                </div>
              ))
            )}
          </div>
        </section>
      </main>
    </div>
  );
}

const ChatMessages = memo(function ChatMessages({ history }) {
  const [expandedSources, setExpandedSources] = useState({});
  const [expandedAnswers, setExpandedAnswers] = useState(() => {
    // By default, expand the most recent answer, collapse older ones
    const initial = {};
    history.forEach((_, index) => {
      initial[index] = index === history.length - 1;
    });
    return initial;
  });

  const toggleSources = (index) => {
    setExpandedSources(prev => ({ ...prev, [index]: !prev[index] }));
  };

  const toggleAnswer = (index) => {
    setExpandedAnswers(prev => ({ ...prev, [index]: !prev[index] }));
  };

  return (
    <div className="chat-container">
      {history.map((turn, index) => {
        const isExpanded = expandedAnswers[index];

        return (
        <div key={index} className="chat-turn">
          <div className="chat-message user-message">
            <div className="message-content">
              <div className="message-bubble user-bubble">
                <div className="message-avatar">👤</div>
                <div className="message-text">{turn.query}</div>
              </div>
            </div>
          </div>
          <div className="chat-message ai-message">
            <div className="message-content">
              <div className={`message-bubble ai-bubble ${isExpanded ? 'expanded' : 'collapsed'}`} onClick={() => toggleAnswer(index)}>
                <div className="message-avatar">🤖</div>
                <div className="message-text">
                  {!isExpanded && (
                    <div className="collapsed-preview">
                      <div className="collapse-hint">▶ Click to expand answer</div>
                      {turn.answer && (
                        <div className="preview-text">
                          {turn.answer.substring(0, 150)}{turn.answer.length > 150 && '...'}
                        </div>
                      )}
                    </div>
                  )}
                  {isExpanded && (
                    <div onClick={(e) => e.stopPropagation()}>
                      <div className="collapse-hint clickable" onClick={() => toggleAnswer(index)}>
                        ▼ Click to collapse
                      </div>
                      {turn.search_params && (
                        <div className="search-params-box">
                          <strong>Search Settings:</strong>
                          <div className="params-row">
                            <span className="param-item">📊 Results: <strong>{turn.search_params.top_k}</strong></span>
                            <span className="param-item">🔍 Mode: <strong>{turn.search_params.search_mode === 'auto' ? 'Intelligent (Auto-select)' :
                              turn.search_params.search_mode === 'files_only' ? 'Files Only' :
                              turn.search_params.search_mode === 'online_only' ? 'Online Only' :
                              turn.search_params.search_mode === 'both' ? 'Both (Files + Online)' :
                              turn.search_params.search_mode === 'sequential_analysis' ? 'Sequential Analysis' :
                              turn.search_params.search_mode}</strong></span>
                            <span className="param-item">🧠 Reasoning: <strong>{turn.search_params.reasoning_mode === 'non_reasoning' ? 'Non-Reasoning (gpt-4.1)' :
                              turn.search_params.reasoning_mode === 'reasoning' ? 'Reasoning (o4-mini)' :
                              turn.search_params.reasoning_mode === 'reasoning_gpt5' ? 'Reasoning (gpt-5-pro)' :
                              turn.search_params.reasoning_mode === 'deep_research' ? 'Deep Research (o3-deep-research)' :
                              turn.search_params.reasoning_mode}</strong></span>
                            {turn.search_params.search_mode === 'both' && (
                              <span className="param-item">📌 Priority: <strong>{turn.search_params.priority_order === 'online_first' ? 'Online First' : 'Files First'}</strong></span>
                            )}
                          </div>
                        </div>
                      )}
                      {turn.selected_mode && turn.mode_reasoning && (
                        <div className="mode-selection-box">
                          <strong>Mode:</strong> <span className="mode-badge">{turn.selected_mode}</span>
                          <div className="mode-reasoning">{turn.mode_reasoning}</div>
                        </div>
                      )}
                      {turn.extracted_info && (
                        <div className="extracted-info-box">
                          <div className="box-header">📄 Step 1: Extracted from Files</div>
                          <div dangerouslySetInnerHTML={{ __html: parseMarkdownToHTML(turn.extracted_info) }} />
                        </div>
                      )}
                      {turn.online_search_response && (
                        <div className="online-search-box">
                          <div className="box-header">🌐 {turn.extracted_info ? 'Step 2: Online Search' : 'Online Search'}</div>
                          <div dangerouslySetInnerHTML={{ __html: parseMarkdownToHTML(turn.online_search_response) }} />
                        </div>
                      )}
                      {turn.answer && (
                        <>
                          {turn.extracted_info && <div className="answer-header">✨ Step 3: Comparative Analysis</div>}
                          <div className="answer-content" dangerouslySetInnerHTML={{ __html: parseMarkdownToHTML(turn.answer) }} />
                        </>
                      )}
                      {turn.results && turn.results.length > 0 && (
                        <div className="sources-container">
                          <button className="sources-toggle" onClick={(e) => { e.stopPropagation(); toggleSources(index); }}>
                            {expandedSources[index] ? '▲' : '▼'} View {turn.results.length} Source(s)
                          </button>
                          {expandedSources[index] && (
                            <div className="sources-list">
                              {turn.results.map((result, idx) => (
                                <div key={idx} className="source-item">
                                  <div className="source-header">
                                    <span className="source-name">{result.metadata.file_name || 'Unknown'}</span>
                                    <span className="source-score">{Math.round(result.score * 100)}%</span>
                                  </div>
                                  <div className="source-meta">
                                    {result.metadata.file_type}
                                    {result.metadata.page && ` • Page ${result.metadata.page}`}
                                    <span className="retrieval-badge">{result.retrieval_method || 'Dense'}</span>
                                  </div>
                                  <div className="source-content">
                                    {result.content.substring(0, 300)}{result.content.length > 300 && '...'}
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )})}
    </div>
  );
});

export default AISearch;
