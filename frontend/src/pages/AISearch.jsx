import { useState } from 'react';
import { searchDocuments, getIndexStatus } from '../services/api';
import './AISearch.css';

function AISearch() {
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState('');
  const [onlineResponse, setOnlineResponse] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [indexStatus, setIndexStatus] = useState(null);

  // Search parameters
  const [searchModel, setSearchModel] = useState('gpt-4.1');
  const [priorityOrder, setPriorityOrder] = useState(['jarvis_docs', 'online_search']);
  const [kBm, setKBm] = useState(50);
  const [kJd, setKJd] = useState(50);

  // Load index status on component mount
  useState(() => {
    checkIndexStatus();
  }, []);

  const checkIndexStatus = async () => {
    try {
      const status = await getIndexStatus();
      setIndexStatus(status);
    } catch (err) {
      console.error('Failed to get index status:', err);
    }
  };

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!question.trim()) return;

    setLoading(true);
    setError('');
    setAnswer('');
    setOnlineResponse('');

    try {
      const result = await searchDocuments({
        question: question.trim(),
        k_bm: kBm,
        k_jd: kJd,
        search_model: searchModel,
        priority_order: priorityOrder
      });

      setAnswer(result.answer);
      if (result.online_search_response) {
        setOnlineResponse(result.online_search_response);
      }
    } catch (err) {
      setError(err.message || 'Search failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const togglePriority = (source) => {
    if (priorityOrder.includes(source)) {
      setPriorityOrder(priorityOrder.filter(s => s !== source));
    } else {
      setPriorityOrder([...priorityOrder, source]);
    }
  };

  return (
    <div className="ai-search-container">
      <div className="ai-search-header">
        <h1>🔍 AI Document Search</h1>
        <p>Ask questions about your biotech documents using advanced RAG technology</p>

        {indexStatus && (
          <div className={`index-status ${indexStatus.status === 'ready' ? 'ready' : 'not-ready'}`}>
            <span>Status: {indexStatus.status}</span>
            <span>Vector DB: {indexStatus.vector_db_loaded ? '✓' : '✗'}</span>
            <span>BM25: {indexStatus.bm25_loaded ? '✓' : '✗'}</span>
            <span>Device: {indexStatus.device}</span>
          </div>
        )}
      </div>

      <div className="search-section">
        <form onSubmit={handleSearch} className="search-form">
          <div className="search-input-group">
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask a question about biotech companies, drug pipelines, clinical trials, etc..."
              rows={4}
              disabled={loading}
            />
          </div>

          <div className="search-controls">
            <div className="control-group">
              <label>Model:</label>
              <select
                value={searchModel}
                onChange={(e) => setSearchModel(e.target.value)}
                disabled={loading}
              >
                <option value="gpt-4.1">GPT-4.1</option>
                <option value="o4-mini">O4-Mini</option>
                <option value="o3">O3</option>
              </select>
            </div>

            <div className="control-group">
              <label>Sources:</label>
              <div className="checkbox-group">
                <label>
                  <input
                    type="checkbox"
                    checked={priorityOrder.includes('jarvis_docs')}
                    onChange={() => togglePriority('jarvis_docs')}
                    disabled={loading}
                  />
                  Internal Docs
                </label>
                <label>
                  <input
                    type="checkbox"
                    checked={priorityOrder.includes('online_search')}
                    onChange={() => togglePriority('online_search')}
                    disabled={loading}
                  />
                  Web Search
                </label>
              </div>
            </div>

            <div className="control-group">
              <label>BM25 Results: {kBm}</label>
              <input
                type="range"
                min="10"
                max="100"
                value={kBm}
                onChange={(e) => setKBm(parseInt(e.target.value))}
                disabled={loading}
              />
            </div>

            <div className="control-group">
              <label>Vector Results: {kJd}</label>
              <input
                type="range"
                min="10"
                max="100"
                value={kJd}
                onChange={(e) => setKJd(parseInt(e.target.value))}
                disabled={loading}
              />
            </div>
          </div>

          <button type="submit" disabled={loading || !question.trim()} className="search-button">
            {loading ? 'Searching...' : 'Search'}
          </button>
        </form>

        {error && (
          <div className="error-message">
            <span>⚠️</span>
            <p>{error}</p>
          </div>
        )}

        {answer && (
          <div className="results-section">
            <div className="answer-card">
              <h2>Answer</h2>
              <div
                className="answer-content"
                dangerouslySetInnerHTML={{ __html: answer.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') }}
              />
            </div>

            {onlineResponse && (
              <div className="online-response-card">
                <h3>Web Search Context</h3>
                <div className="online-response-content">
                  {onlineResponse}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="example-queries">
        <h3>Example Queries</h3>
        <div className="example-grid">
          <button onClick={() => setQuestion("What is PPInnova's drug pipeline and current development stages?")}>
            Drug Pipeline Analysis
          </button>
          <button onClick={() => setQuestion("List all competitors targeting OTOF-related deafness and their valuations")}>
            Competitor Analysis
          </button>
          <button onClick={() => setQuestion("What are the clinical trial results for EHT102?")}>
            Clinical Trial Data
          </button>
          <button onClick={() => setQuestion("Estimate the patient population for DFNB9 congenital hearing loss in China")}>
            Market Sizing
          </button>
        </div>
      </div>
    </div>
  );
}

export default AISearch;
