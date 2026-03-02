import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { icSimulatorAPI } from '../services/api';
import { parseMarkdownToHTML } from '../utils/markdown';
import './ICSimulator.css';

function ICSimulator() {
  const navigate = useNavigate();
  const { user } = useAuth();

  // Data management state
  const [meetings, setMeetings] = useState([]);
  const [stats, setStats] = useState({ total_segments: 0, total_meetings: 0 });
  const [syncStatus, setSyncStatus] = useState(null);
  const [isSyncing, setIsSyncing] = useState(false);
  const [extractionStatus, setExtractionStatus] = useState(null);
  const [isExtracting, setIsExtracting] = useState(false);

  // Date range filter for selecting which meetings to use as learning base
  const [historyDateFrom, setHistoryDateFrom] = useState('');
  const [historyDateTo, setHistoryDateTo] = useState('');

  // Upload meeting note state
  const [meetingDate, setMeetingDate] = useState('');
  const [uploadingMeeting, setUploadingMeeting] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const meetingFileRef = useRef(null);

  // Question generation state
  const [projectDescription, setProjectDescription] = useState('');
  const [projectFiles, setProjectFiles] = useState([]);
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [generationMode, setGenerationMode] = useState('cognitive');
  const [selectedModel, setSelectedModel] = useState('gpt-5.2');

  const projectFileRef = useRef(null);
  const syncTimerRef = useRef(null);
  const extractionTimerRef = useRef(null);

  // Load meetings and check extraction status on mount
  useEffect(() => {
    loadMeetings();
    // Resume extraction polling if an extraction was running before page load
    (async () => {
      try {
        const status = await icSimulatorAPI.getExtractionStatus();
        if (status && status.is_running) {
          setExtractionStatus(status);
          setIsExtracting(true);
        }
      } catch {
        // ignore — extraction status endpoint may not be available
      }
    })();
  }, []);

  // Poll sync status when syncing
  useEffect(() => {
    if (isSyncing) {
      syncTimerRef.current = setInterval(async () => {
        try {
          const status = await icSimulatorAPI.getSyncStatus();
          setSyncStatus(status);
          if (!status.is_syncing) {
            setIsSyncing(false);
            clearInterval(syncTimerRef.current);
            loadMeetings();
            // Start polling extraction if auto-triggered
            if (status.auto_extraction_triggered) {
              setIsExtracting(true);
            }
          }
        } catch {
          // ignore polling errors
        }
      }, 2000);
    }
    return () => {
      if (syncTimerRef.current) clearInterval(syncTimerRef.current);
    };
  }, [isSyncing]);

  // Poll extraction status when extracting
  useEffect(() => {
    if (isExtracting) {
      extractionTimerRef.current = setInterval(async () => {
        try {
          const status = await icSimulatorAPI.getExtractionStatus();
          setExtractionStatus(status);
          if (!status.is_running) {
            setIsExtracting(false);
            clearInterval(extractionTimerRef.current);
          }
        } catch {
          // ignore polling errors
        }
      }, 3000);
    }
    return () => {
      if (extractionTimerRef.current) clearInterval(extractionTimerRef.current);
    };
  }, [isExtracting]);

  const loadMeetings = async () => {
    try {
      const data = await icSimulatorAPI.getMeetings();
      setMeetings(data.meetings || []);
      setStats(data.stats || { total_segments: 0, total_meetings: 0 });
    } catch (err) {
      console.error('Failed to load meetings:', err);
    }
  };

  // ─── Confluence Sync ───────────────────────────────────────────────
  const handleSync = async () => {
    try {
      setError(null);
      setIsSyncing(true);
      const res = await icSimulatorAPI.syncConfluence(200, historyDateFrom, historyDateTo);
      if (res.status === 'already_syncing') {
        setSyncStatus(res.progress);
      }
    } catch (err) {
      setError(err.message || 'Failed to start Confluence sync');
      setIsSyncing(false);
    }
  };

  // ─── Upload Meeting Note ──────────────────────────────────────────
  const handleMeetingUpload = async (file) => {
    if (!file) return;
    setUploadingMeeting(true);
    setError(null);
    try {
      await icSimulatorAPI.uploadMeeting(file, meetingDate);
      setMeetingDate('');
      await loadMeetings();
    } catch (err) {
      setError(err.message || 'Failed to upload meeting note');
    } finally {
      setUploadingMeeting(false);
    }
  };

  const handleMeetingFileDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleMeetingUpload(file);
  };

  // ─── Delete Meeting ───────────────────────────────────────────────
  const handleDeleteMeeting = async (pageId) => {
    try {
      await icSimulatorAPI.deleteMeeting(pageId);
      await loadMeetings();
    } catch (err) {
      setError(err.message || 'Failed to delete meeting');
    }
  };

  // ─── Project File Selection ───────────────────────────────────────
  const handleProjectFileSelect = (e) => {
    const files = Array.from(e.target.files || []);
    setProjectFiles(prev => [...prev, ...files]);
  };

  const removeProjectFile = (index) => {
    setProjectFiles(prev => prev.filter((_, i) => i !== index));
  };

  // ─── Generate IC Questions ────────────────────────────────────────
  const handleGenerate = async () => {
    if (!projectDescription.trim() && projectFiles.length === 0) return;

    setGenerating(true);
    setError(null);
    setResult(null);

    try {
      const data = await icSimulatorAPI.generateQuestions(
        projectDescription, projectFiles, historyDateFrom, historyDateTo, generationMode, selectedModel
      );
      setResult(data);
    } catch (err) {
      setError(err.message || 'Failed to generate IC questions');
    } finally {
      setGenerating(false);
    }
  };

  // ─── Copy to clipboard ───────────────────────────────────────────
  const handleCopy = useCallback(() => {
    if (result?.questions_markdown) {
      navigator.clipboard.writeText(result.questions_markdown);
    }
  }, [result]);

  return (
    <div className="ic-simulator-container">
      {/* Header */}
      <div className="ic-header-section">
        <button className="ic-back-button" onClick={() => navigate('/')}>
          ← Back
        </button>
        <div className="ic-title-block">
          <div className="ic-icon-wrapper">
            <span className="ic-icon">&#x1F9E0;</span>
          </div>
          <h1>IC Question Simulator</h1>
          <p className="ic-subtitle">
            Anticipate Investment Committee questions using historical meeting patterns
          </p>
        </div>
      </div>

      <div className="ic-main">
        {/* Left Panel — Data Management */}
        <div className="ic-data-panel">
          {/* Stats */}
          <div className="ic-panel-card">
            <h3>Knowledge Base</h3>
            <div className="ic-stats-row">
              <span className="ic-stats-label">Meetings indexed</span>
              <span className="ic-stats-value">{stats.total_meetings}</span>
            </div>
            <div className="ic-stats-row">
              <span className="ic-stats-label">Q&A segments</span>
              <span className="ic-stats-value">{stats.total_segments}</span>
            </div>
          </div>

          {/* Date Range Filter */}
          <div className="ic-panel-card">
            <h3>Meeting Date Range</h3>
            <p className="ic-date-range-hint">
              Filter which IC meetings to sync from Confluence and use as the learning base for question generation.
            </p>
            <div className="ic-date-range-row">
              <div className="ic-date-field">
                <label className="ic-date-label">From</label>
                <input
                  type="date"
                  className="ic-date-input"
                  value={historyDateFrom}
                  onChange={(e) => setHistoryDateFrom(e.target.value)}
                />
              </div>
              <div className="ic-date-field">
                <label className="ic-date-label">To</label>
                <input
                  type="date"
                  className="ic-date-input"
                  value={historyDateTo}
                  onChange={(e) => setHistoryDateTo(e.target.value)}
                />
              </div>
            </div>
            {(historyDateFrom || historyDateTo) && (
              <button
                className="ic-clear-dates-btn"
                onClick={() => { setHistoryDateFrom(''); setHistoryDateTo(''); }}
              >
                Clear dates (use all meetings)
              </button>
            )}
          </div>

          {/* Confluence Sync */}
          <div className="ic-panel-card">
            <h3>Sync from Confluence</h3>
            <button
              className="ic-sync-btn"
              onClick={handleSync}
              disabled={isSyncing}
            >
              {isSyncing ? 'Syncing...' : 'Sync Meeting Notes'}
            </button>
            {syncStatus && isSyncing && (
              <div className="ic-sync-progress">
                <div className="ic-progress-bar">
                  <div
                    className="ic-progress-fill"
                    style={{ width: `${syncStatus.progress || 0}%` }}
                  />
                </div>
                <span className="ic-progress-text">
                  {syncStatus.pages_processed || 0} / {syncStatus.total_pages || '?'} pages
                </span>
              </div>
            )}
            {syncStatus?.error && (
              <div className="ic-error" style={{ marginTop: '0.75rem' }}>
                {syncStatus.error}
              </div>
            )}
            {/* Auto-extraction progress */}
            {isExtracting && extractionStatus && (
              <div className="ic-sync-progress" style={{ marginTop: '0.75rem' }}>
                <span className="ic-progress-text" style={{ color: '#7c5cfc', fontWeight: 500 }}>
                  Updating IC profile: {extractionStatus.detail || extractionStatus.stage || 'starting...'}
                </span>
              </div>
            )}
            {extractionStatus && !isExtracting && extractionStatus.completed_at && syncStatus?.auto_extraction_triggered && (
              <div style={{ marginTop: '0.75rem', color: '#22c55e', fontSize: '0.85rem' }}>
                IC profile updated automatically with {syncStatus.new_pages_synced} new meeting{syncStatus.new_pages_synced !== 1 ? 's' : ''}.
              </div>
            )}
            {extractionStatus?.error && (
              <div className="ic-error" style={{ marginTop: '0.5rem' }}>
                Profile update failed: {extractionStatus.error}
              </div>
            )}
          </div>

          {/* Upload Meeting Note */}
          <div className="ic-panel-card">
            <h3>Upload Meeting Note</h3>
            <div
              className={`ic-upload-area ${dragOver ? 'dragging' : ''}`}
              onClick={() => meetingFileRef.current?.click()}
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleMeetingFileDrop}
            >
              {uploadingMeeting
                ? 'Processing...'
                : 'Drop a file here or click to upload'}
            </div>
            <input
              ref={meetingFileRef}
              type="file"
              style={{ display: 'none' }}
              accept=".pdf,.docx,.doc,.txt,.md,.pptx,.xlsx,.csv,.html"
              onChange={(e) => handleMeetingUpload(e.target.files[0])}
            />
            <input
              type="date"
              className="ic-date-input"
              value={meetingDate}
              onChange={(e) => setMeetingDate(e.target.value)}
              placeholder="Meeting date (optional)"
            />
          </div>

          {/* Indexed Meetings */}
          <div className="ic-panel-card">
            <h3>Indexed Meetings ({meetings.length})</h3>
            {meetings.length === 0 ? (
              <div className="ic-empty-state">
                No meetings indexed yet.<br />
                Sync from Confluence or upload notes.
              </div>
            ) : (
              <div className="ic-meeting-list">
                {meetings.map((m) => (
                  <div key={m.page_id} className="ic-meeting-item">
                    <div className="ic-meeting-info">
                      <div className="ic-meeting-title">{m.title}</div>
                      <div className="ic-meeting-date">
                        {m.meeting_date ? m.meeting_date.slice(0, 10) : 'No date'}
                        {' · '}{m.segment_count} segments
                        {' · '}{m.source}
                      </div>
                    </div>
                    <button
                      className="ic-meeting-delete"
                      onClick={() => handleDeleteMeeting(m.page_id)}
                      title="Remove from index"
                    >
                      ✕
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Panel — Question Generation */}
        <div className="ic-question-panel">
          {/* Input */}
          <div className="ic-input-card">
            <h3>New Project Materials</h3>
            <textarea
              className="ic-description-textarea"
              value={projectDescription}
              onChange={(e) => setProjectDescription(e.target.value)}
              placeholder="Describe the project, company, or deal you want the IC to review. Include key details like target, indication, stage, valuation, team background, etc."
            />

            <div className="ic-file-upload-row">
              <button
                className="ic-upload-btn"
                onClick={() => projectFileRef.current?.click()}
              >
                + Attach Files
              </button>
              <input
                ref={projectFileRef}
                type="file"
                multiple
                style={{ display: 'none' }}
                accept=".pdf,.docx,.doc,.txt,.md,.pptx,.xlsx,.csv,.html"
                onChange={handleProjectFileSelect}
              />
              {projectFiles.map((f, i) => (
                <span key={i} className="ic-file-tag">
                  {f.name}
                  <button
                    className="ic-file-tag-remove"
                    onClick={() => removeProjectFile(i)}
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>

            {/* Generation Mode + Model selectors in one row */}
            <div className="ic-options-row">
              <div className="ic-option-group">
                <label className="ic-mode-label">Generation Mode</label>
                <select
                  className="ic-select"
                  value={generationMode}
                  onChange={(e) => setGenerationMode(e.target.value)}
                >
                  <option value="cognitive">Cognitive Simulation</option>
                  <option value="legacy">Legacy RAG</option>
                </select>
              </div>
              <div className="ic-option-group">
                <label className="ic-mode-label">Model</label>
                <select
                  className="ic-select"
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                >
                  <option value="gpt-5.2">GPT-5.2</option>
                  <option value="gemini-pro-latest">Gemini Pro</option>
                </select>
              </div>
            </div>

            <button
              className="ic-generate-btn"
              onClick={handleGenerate}
              disabled={generating || (!projectDescription.trim() && projectFiles.length === 0)}
            >
              {generating ? 'Generating Questions...' : 'Generate Anticipated IC Questions'}
            </button>
          </div>

          {/* Error */}
          {error && <div className="ic-error">{error}</div>}

          {/* Loading */}
          {generating && (
            <div className="ic-results-card">
              <div className="ic-loading">
                <div className="ic-spinner" />
                <span className="ic-loading-text">
                  Analyzing project materials and historical IC patterns...
                </span>
              </div>
            </div>
          )}

          {/* Results */}
          {result && !generating && (
            <div className="ic-results-card">
              <div className="ic-results-header">
                <h3>Anticipated IC Questions</h3>
                <button className="ic-copy-btn" onClick={handleCopy}>
                  Copy
                </button>
              </div>

              <div
                className="ic-results-content"
                dangerouslySetInnerHTML={{
                  __html: parseMarkdownToHTML(result.questions_markdown),
                }}
              />

              {/* Historical References */}
              {result.historical_references && result.historical_references.length > 0 && (
                <div className="ic-references-section">
                  <h4>Referenced Historical Q&A</h4>
                  {result.historical_references.map((ref, i) => (
                    <div key={i} className="ic-reference-item">
                      <div className="ic-reference-title">{ref.meeting_title}</div>
                      {ref.question && (
                        <div className="ic-reference-question">
                          "{ref.question}"
                        </div>
                      )}
                      <div className="ic-reference-meta">
                        {ref.meeting_date ? ref.meeting_date.slice(0, 10) : ''}
                        {ref.score ? ` · Relevance: ${(ref.score * 100).toFixed(0)}%` : ''}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Metadata */}
              {result.metadata && (
                <div className="ic-reference-meta" style={{ marginTop: '1rem' }}>
                  {result.metadata.mode && (
                    <span>
                      Mode: {result.metadata.mode === 'cognitive_simulation' ? 'Cognitive Simulation' : 'Legacy RAG'}
                      {' · '}
                    </span>
                  )}
                  Model: {result.metadata.model}
                  {result.metadata.historical_segments_used != null && (
                    <span>{' · '}Historical segments used: {result.metadata.historical_segments_used}</span>
                  )}
                  {(result.metadata.date_from || result.metadata.date_to) && (
                    <span>
                      {' · '}Date range: {result.metadata.date_from || 'earliest'}
                      {' to '}{result.metadata.date_to || 'latest'}
                    </span>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default ICSimulator;
