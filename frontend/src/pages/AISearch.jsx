import { useState, useEffect, useRef, memo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { uploadFile, searchDocuments, getDocuments, deleteDocument, getJobStatus, cancelJob, getSearchJobStatus, cancelSearchJob } from '../services/api';
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

  // Search job tracking for long-running searches
  const [searchJobStatus, setSearchJobStatus] = useState(null); // { jobId, progress, currentStep, status }

  const fileInputRef = useRef(null);
  const folderInputRef = useRef(null);
  const searchResultsRef = useRef(null);
  const searchInputRef = useRef(null);
  const pollingTimersRef = useRef(new Map()); // Track active polling timers
  const abortControllersRef = useRef(new Map()); // Track abort controllers for uploads
  const searchJobTimerRef = useRef(null); // Track search job polling timer
  const searchAbortControllerRef = useRef(null); // Track abort controller for current search

  useEffect(() => {
    const history = getCurrentHistory();
    setConversationHistory(history);
  }, [currentConversationId, conversations]); // Also trigger when conversations change

  // Auto-scroll to latest message when conversation history changes
  useEffect(() => {
    if (conversationHistory.length > 0 && searchResultsRef.current) {
      // Use setTimeout to ensure DOM has updated before scrolling
      setTimeout(() => {
        searchResultsRef.current?.scrollTo({
          top: searchResultsRef.current.scrollHeight,
          behavior: 'smooth'
        });
      }, 100);
    }
  }, [conversationHistory]);

  // Auto-resize search input textarea based on content
  useEffect(() => {
    const textarea = searchInputRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
    }
  }, [searchQuery]);

  useEffect(() => {
    // Only load documents when we have a valid conversation ID
    if (currentConversationId) {
      loadDocuments();
    }
  }, [currentConversationId]);

  // Cleanup polling timers and abort controllers on unmount
  useEffect(() => {
    return () => {
      // Clear all active polling timers
      pollingTimersRef.current.forEach((timerId) => {
        clearTimeout(timerId);
      });
      pollingTimersRef.current.clear();

      // Clear search job timer
      if (searchJobTimerRef.current) {
        clearTimeout(searchJobTimerRef.current);
        searchJobTimerRef.current = null;
      }

      // Abort ongoing search
      if (searchAbortControllerRef.current) {
        searchAbortControllerRef.current.abort();
        searchAbortControllerRef.current = null;
      }

      // Abort all ongoing uploads
      abortControllersRef.current.forEach((controller) => {
        controller.abort();
      });
      abortControllersRef.current.clear();
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

  const pollSearchJobStatus = useCallback(async (jobId, queryText) => {
    let retryCount = 0;
    const maxRetries = 4;
    const retryDelays = [2000, 4000, 8000, 16000]; // Exponential backoff

    const poll = async () => {
      try {
        const status = await getSearchJobStatus(jobId);

        if (status.status === 'pending' || status.status === 'processing') {
          // Update progress
          setSearchJobStatus({
            jobId,
            query: queryText,
            progress: status.progress || 0,
            currentStep: status.current_step || 'Processing...',
            status: status.status
          });

          // Reset retry count on successful request
          retryCount = 0;

          // Continue polling every 2 seconds
          searchJobTimerRef.current = setTimeout(poll, 2000);
        } else if (status.status === 'completed') {
          // Clear polling timer
          if (searchJobTimerRef.current) {
            clearTimeout(searchJobTimerRef.current);
            searchJobTimerRef.current = null;
          }

          // Clear search job status
          setSearchJobStatus(null);

          // Add result to conversation history
          const newTurn = {
            query: queryText,
            answer: status.answer || 'No answer provided',
            extracted_info: status.extracted_info || null,
            online_search_response: status.online_search_response || null,
            selected_mode: null,
            mode_reasoning: null,
            results: status.results || [],
            search_params: {
              search_mode: status.search_mode,
              reasoning_mode: status.reasoning_mode
            }
          };

          const updated = [...conversationHistory, newTurn];
          setConversationHistory(updated);
          updateCurrentConversation(updated);
          setLoading(false);

          // Scroll to bottom
          setTimeout(() => {
            if (searchResultsRef.current) {
              searchResultsRef.current.scrollTop = searchResultsRef.current.scrollHeight;
            }
          }, 100);
        } else if (status.status === 'failed') {
          // Clear polling timer
          if (searchJobTimerRef.current) {
            clearTimeout(searchJobTimerRef.current);
            searchJobTimerRef.current = null;
          }

          setSearchJobStatus(null);
          setLoading(false);
          alert('Search failed: ' + (status.error_message || 'Unknown error'));
        } else if (status.status === 'cancelled') {
          // Clear polling timer
          if (searchJobTimerRef.current) {
            clearTimeout(searchJobTimerRef.current);
            searchJobTimerRef.current = null;
          }

          setSearchJobStatus(null);
          setLoading(false);
        }
      } catch (error) {
        console.error('Error polling search job status:', error);

        // Network resilience: Retry with exponential backoff
        if (retryCount < maxRetries) {
          const delay = retryDelays[retryCount];
          console.log(`Network error, retrying in ${delay}ms... (attempt ${retryCount + 1}/${maxRetries})`);

          // Update status to show reconnecting
          setSearchJobStatus(prev => ({
            ...prev,
            currentStep: `Reconnecting... (attempt ${retryCount + 1}/${maxRetries})`
          }));

          retryCount++;
          searchJobTimerRef.current = setTimeout(poll, delay);
        } else {
          // Max retries exceeded
          if (searchJobTimerRef.current) {
            clearTimeout(searchJobTimerRef.current);
            searchJobTimerRef.current = null;
          }

          setSearchJobStatus(null);
          setLoading(false);
          alert('Search failed: Network error. Please check your connection and try again.');
        }
      }
    };

    poll();
  }, [conversationHistory, updateCurrentConversation, searchResultsRef]);

  const handleCancelSearchJob = useCallback(async () => {
    if (!searchJobStatus?.jobId) return;

    // Show confirmation dialog
    const confirmed = window.confirm(
      'Are you sure you want to cancel this search?\n\nThis will stop the current search process and save API token usage.'
    );

    if (!confirmed) return;

    try {
      await cancelSearchJob(searchJobStatus.jobId);

      // Clear polling timer
      if (searchJobTimerRef.current) {
        clearTimeout(searchJobTimerRef.current);
        searchJobTimerRef.current = null;
      }

      setSearchJobStatus(null);
      setLoading(false);
    } catch (error) {
      console.error('Error cancelling search job:', error);
      alert('Failed to cancel search: ' + error.message);
    }
  }, [searchJobStatus]);

  const handleCancelJob = useCallback(async (jobId, fileId) => {
    try {
      // If there's an ongoing upload, abort it
      const abortController = abortControllersRef.current.get(fileId);
      if (abortController) {
        abortController.abort();
        abortControllersRef.current.delete(fileId);
      }

      // If there's a job ID, cancel the job on the server
      if (jobId) {
        await cancelJob(jobId);
      }

      // Stop polling
      const timerId = pollingTimersRef.current.get(fileId);
      if (timerId) {
        clearTimeout(timerId);
        pollingTimersRef.current.delete(fileId);
      }

      // Update UI
      setUploadProgress(prev => ({
        ...prev,
        [fileId]: {
          ...prev[fileId],
          status: 'error',
          message: 'Cancelled by user'
        }
      }));
    } catch (error) {
      console.error('Error cancelling job:', error);
    }
  }, []);

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
              message: progress,
              jobId: jobId
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
              message,
              jobId: jobId
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
              message: status.error_message || 'Processing failed',
              jobId: jobId
            }
          }));
        } else if (status.status === 'cancelled') {
          pollingTimersRef.current.delete(fileId);
          setUploadProgress(prev => ({
            ...prev,
            [fileId]: {
              name: fileName,
              status: 'error',
              message: 'Cancelled by user',
              jobId: jobId
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

  const shouldSkipFile = (fileName) => {
    // Skip hidden files (starting with .)
    if (fileName.startsWith('.')) return true;

    // Skip Microsoft Office temporary files (starting with ~$)
    if (fileName.startsWith('~$')) return true;

    // Skip macOS metadata files
    if (fileName === '.DS_Store' || fileName.includes('__MACOSX')) return true;

    return false;
  };

  const handleFileSelect = useCallback(async (files, isFolder = false) => {
    const fileArray = Array.from(files);
    setUploading(true);

    // Prepare all file info first, filtering out system/temporary files
    const fileInfos = fileArray
      .filter(file => {
        const fileName = file.name;
        if (shouldSkipFile(fileName)) {
          console.log(`Skipping system/temporary file: ${fileName}`);
          return false;
        }
        return true;
      })
      .map(file => {
        const relativePath = isFolder && file.webkitRelativePath ? file.webkitRelativePath : null;
        const displayName = relativePath || file.name;
        const fileId = `upload-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        return { file, relativePath, displayName, fileId };
      });

    // If all files were filtered out, don't proceed
    if (fileInfos.length === 0) {
      setUploading(false);
      console.log('All files were filtered out (system/temporary files)');
      return;
    }

    // Set initial upload status for all files
    setUploadProgress(prev => {
      const newProgress = { ...prev };
      fileInfos.forEach(({ displayName, fileId }) => {
        newProgress[fileId] = { name: displayName, status: 'uploading', message: 'Queued...' };
      });
      return newProgress;
    });

    // Upload files in parallel batches (5 concurrent uploads)
    const BATCH_SIZE = 5;
    for (let i = 0; i < fileInfos.length; i += BATCH_SIZE) {
      const batch = fileInfos.slice(i, i + BATCH_SIZE);

      // Process batch in parallel
      await Promise.all(batch.map(async ({ file, relativePath, displayName, fileId }) => {
        // Create abort controller for this upload
        const abortController = new AbortController();
        abortControllersRef.current.set(fileId, abortController);

        // Update status to uploading
        setUploadProgress(prev => ({
          ...prev,
          [fileId]: { name: displayName, status: 'uploading', message: 'Uploading...', canCancel: true }
        }));

        try {
          const result = await uploadFile(file, currentConversationId, relativePath, abortController.signal);

          // Remove abort controller after successful upload
          abortControllersRef.current.delete(fileId);

          if (result.success && result.job_id) {
            // File uploaded successfully, now processing in background
            setUploadProgress(prev => ({
              ...prev,
              [fileId]: {
                name: displayName,
                status: 'processing',
                message: 'File uploaded. Processing in background...',
                jobId: result.job_id,
                canCancel: true
              }
            }));
            // Start polling for job status
            pollJobStatus(result.job_id, fileId, displayName);
          } else {
            throw new Error(result.message || 'Upload failed');
          }
        } catch (error) {
          // Clean up abort controller
          abortControllersRef.current.delete(fileId);

          setUploadProgress(prev => ({
            ...prev,
            [fileId]: { name: displayName, status: 'error', message: error.message }
          }));
        }
      }));
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

  const handleCancelSearch = useCallback(() => {
    // Show confirmation dialog
    const confirmed = window.confirm(
      'Are you sure you want to cancel this search?\n\nThis will stop the current search process and save API token usage.'
    );

    if (!confirmed) return;

    // Cancel synchronous search (if in progress)
    if (searchAbortControllerRef.current) {
      searchAbortControllerRef.current.abort();
      searchAbortControllerRef.current = null;
      setLoading(false);
      console.log('Synchronous search cancelled by user');
    }

    // Cancel async search job (if in progress)
    if (searchJobStatus?.jobId) {
      handleCancelSearchJob();
    }
  }, [searchJobStatus, handleCancelSearchJob]);

  const handleSearch = useCallback(async (e) => {
    e.preventDefault();
    if (!searchQuery.trim() || loading) return;
    setLoading(true);

    // Create abort controller for this search
    const abortController = new AbortController();
    searchAbortControllerRef.current = abortController;

    try {
      const priority = priorityOrder === 'online_first' ? ['online_search', 'files'] : ['files', 'online_search'];

      // Only send query and answer in conversation history (not results/sources)
      // to avoid bloating the API request with source chunks
      const conversationHistoryForAPI = conversationHistory.map(turn => ({
        query: turn.query,
        answer: turn.answer
      }));

      const queryText = searchQuery.trim();
      const result = await searchDocuments({
        query: queryText,
        top_k: topK,
        search_mode: searchMode,
        reasoning_mode: reasoningMode,
        priority_order: priority,
        conversation_history: conversationHistoryForAPI,
        conversation_id: currentConversationId
      }, abortController.signal);

      // Clear abort controller after successful request
      searchAbortControllerRef.current = null;

      // Check if this is an async search job (long-running search)
      if (result.is_async && result.job_id) {
        // Start polling for results
        console.log(`Starting background search job ${result.job_id} for query: ${queryText}`);
        setSearchQuery(''); // Clear search box
        pollSearchJobStatus(result.job_id, queryText);
        // Note: setLoading(false) will be called when job completes or fails
      } else if (result.success) {
        // Synchronous search completed immediately
        const newTurn = {
          query: queryText,
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
        setLoading(false);
        setTimeout(() => {
          if (searchResultsRef.current) {
            searchResultsRef.current.scrollTop = searchResultsRef.current.scrollHeight;
          }
        }, 100);
      }
    } catch (error) {
      // Clear abort controller on error
      searchAbortControllerRef.current = null;

      console.error('Search error:', error);

      // Don't show alert for user-cancelled searches
      if (error.message !== 'Search cancelled by user') {
        alert('Search failed: ' + error.message);
      }

      setLoading(false);
    }
  }, [searchQuery, loading, topK, searchMode, reasoningMode, priorityOrder, conversationHistory, currentConversationId, updateCurrentConversation, searchResultsRef, pollSearchJobStatus]);

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
          <h1>🔍 Unified AI Search</h1>
          <p className="subtitle">Intelligent search across your documents and the web with multi-model reasoning</p>
        </header>

        <section className="upload-section">
          <h2>Upload Documents</h2>
          <div
            className={`upload-area ${dragOver ? 'drag-over' : ''}`}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
          >
            <div className="upload-content">
              <div className="upload-icon">☁️</div>
              <p className="upload-text">Drag & drop files here</p>
              <p className="upload-subtext">Supported: PDF, DOCX, TXT, MD, CSV, XLSX, PPTX, HTML, JSON</p>
              <div className="upload-buttons" style={{ display: 'flex', gap: '10px', marginTop: '15px', justifyContent: 'center' }}>
                <button
                  type="button"
                  onClick={(e) => { e.stopPropagation(); fileInputRef.current?.click(); }}
                  style={{
                    padding: '10px 20px',
                    backgroundColor: 'var(--pantone-1505u)',
                    color: 'white',
                    border: 'none',
                    borderRadius: '8px',
                    cursor: 'pointer',
                    fontWeight: '600',
                    fontSize: '14px'
                  }}
                >
                  📄 Select Files
                </button>
                <button
                  type="button"
                  onClick={(e) => { e.stopPropagation(); folderInputRef.current?.click(); }}
                  style={{
                    padding: '10px 20px',
                    backgroundColor: '#4a5568',
                    color: 'white',
                    border: 'none',
                    borderRadius: '8px',
                    cursor: 'pointer',
                    fontWeight: '600',
                    fontSize: '14px'
                  }}
                >
                  📁 Select Folder
                </button>
              </div>
              <p className="upload-subtext" style={{ color: 'var(--pantone-1505u)', fontWeight: '600', marginTop: '10px' }}>
                💡 Tip: Upload folders or ZIP files for bulk processing
              </p>
              <input ref={fileInputRef} type="file" multiple accept=".pdf,.txt,.md,.docx,.doc,.xlsx,.xls,.csv,.pptx,.ppt,.html,.htm,.json,.eml,.zip"
                onChange={(e) => handleFileSelect(e.target.files, false)} style={{ display: 'none' }} />
              <input ref={folderInputRef} type="file" webkitdirectory="" directory="" multiple
                onChange={(e) => handleFileSelect(e.target.files, true)} style={{ display: 'none' }} />
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
                    {(progress.status === 'uploading' || progress.status === 'processing') && progress.canCancel && (
                      <button
                        className="cancel-upload-button"
                        onClick={() => handleCancelJob(progress.jobId, id)}
                        title="Cancel upload"
                      >
                        ✕
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="conversation-section">
          <div ref={searchResultsRef} className="search-results">
            {conversationHistory.length === 0 ? (
              <div className="no-results"><p>Start a conversation. Ask me anything!</p></div>
            ) : (
              <ChatMessages history={conversationHistory} />
            )}
          </div>
        </section>

        <section className="search-section">
          <h2>Search Documents</h2>

          {/* Search Job Progress Indicator */}
          {searchJobStatus && (
            <div className="search-job-progress">
              <div className="progress-header">
                <span className="progress-query">🔍 {searchJobStatus.query}</span>
                <button className="cancel-button" onClick={handleCancelSearchJob} title="Cancel search">
                  ✕
                </button>
              </div>
              <div className="progress-bar-container">
                <div className="progress-bar" style={{ width: `${searchJobStatus.progress}%` }}></div>
              </div>
              <div className="progress-status">
                <span>{searchJobStatus.progress}% - {searchJobStatus.currentStep}</span>
              </div>
            </div>
          )}

          <form onSubmit={handleSearch} className="search-box">
            <textarea ref={searchInputRef} className="search-input" placeholder="Enter your search query..." value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  if (searchQuery.trim() && !loading) {
                    handleSearch(e);
                  }
                }
              }}
              disabled={loading}
              rows={1}
            />
            <button type="submit" className="search-button" disabled={loading || !searchQuery.trim()}>
              {loading ? '⏳ Searching...' : '🔍 Search'}
            </button>
            {loading && (
              <button type="button" className="cancel-search-button" onClick={handleCancelSearch} title="Cancel search">
                ✕ Cancel
              </button>
            )}
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
                  <option value="non_reasoning">Default (gpt-5.1)</option>
                  <option value="reasoning_gpt5">Reasoning (gpt-5-pro)</option>
                  <option value="reasoning_gemini">Reasoning (gemini-3-pro)</option>
                  <option value="deep_research">Deep Research (o3-deep-research)</option>
                </select></label>
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
  const [expandedDetails, setExpandedDetails] = useState({});

  const toggleSources = (index) => {
    setExpandedSources(prev => ({ ...prev, [index]: !prev[index] }));
  };

  const toggleAnswer = (index) => {
    setExpandedAnswers(prev => ({ ...prev, [index]: !prev[index] }));
  };

  const toggleDetails = (index) => {
    setExpandedDetails(prev => ({ ...prev, [index]: !prev[index] }));
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

                      {/* Conclusion/Answer - Prioritized at the Top */}
                      {turn.answer && (
                        <div className="conclusion-section">
                          <div className="conclusion-header">✨ Conclusion</div>
                          <div className="answer-content" dangerouslySetInnerHTML={{ __html: parseMarkdownToHTML(turn.answer) }} />
                        </div>
                      )}

                      {/* Show Details Toggle - Only show if there are details to show */}
                      {(turn.search_params || turn.selected_mode || turn.extracted_info || turn.online_search_response) && (
                        <div className="details-toggle-container">
                          <button
                            className="details-toggle-button"
                            onClick={(e) => { e.stopPropagation(); toggleDetails(index); }}
                          >
                            {expandedDetails[index] ? '▲ Hide Details' : '▼ Show Details'}
                          </button>
                        </div>
                      )}

                      {/* Supporting Steps - Hidden Behind Toggle */}
                      {expandedDetails[index] && (
                        <div className="supporting-details">
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
                                <span className="param-item">🧠 Reasoning: <strong>{turn.search_params.reasoning_mode === 'non_reasoning' ? 'Default (gpt-5.1)' :
                                  turn.search_params.reasoning_mode === 'reasoning_gpt5' ? 'Reasoning (gpt-5-pro)' :
                                  turn.search_params.reasoning_mode === 'reasoning_gemini' ? 'Reasoning (gemini-3-pro)' :
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
                          {turn.extracted_info && turn.extracted_info.trim() && (
                            <div className="extracted-info-box">
                              <div className="box-header">📄 Step 1: Extracted from Files</div>
                              <div className="box-content" dangerouslySetInnerHTML={{ __html: parseMarkdownToHTML(turn.extracted_info) }} />
                            </div>
                          )}
                          {turn.online_search_response && turn.online_search_response.trim() && (
                            <div className="online-search-box">
                              <div className="box-header">🌐 {turn.extracted_info ? 'Step 2: Online Search' : 'Online Search'}</div>
                              <div className="box-content" dangerouslySetInnerHTML={{ __html: parseMarkdownToHTML(turn.online_search_response) }} />
                            </div>
                          )}
                          {!turn.extracted_info && !turn.online_search_response && !turn.selected_mode && (
                            <div style={{ padding: '10px', color: '#6b7280', fontStyle: 'italic', textAlign: 'center' }}>
                              Only search settings available for this query
                            </div>
                          )}
                        </div>
                      )}

                      {/* Sources - Always at the Bottom */}
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
