import { useNavigate } from 'react-router-dom';
import './Home.css';

function Home() {
  const navigate = useNavigate();

  return (
    <div className="home-container">
      <div className="hero-section">
        <h1>AI Search Platform</h1>
        <p className="subtitle">
          Your intelligent search companion for comprehensive information retrieval
        </p>
      </div>

      <div className="features-section">
        <div className="feature-card highlight">
          <h2>🔍 AI Document Search</h2>
          <p>Search your documents using advanced RAG and AI models</p>
          <button
            className="tracker-button"
            onClick={() => navigate('/ai-search')}
          >
            AI Search
          </button>
        </div>

        <div className="feature-card highlight">
          <h2>📊 Public Market Tracker</h2>
          <p>Track HKEX 18A biotech stocks, portfolio companies, and IPO listings</p>
          <ul className="tracker-features">
            <li>• HKEX 18A Biotech Tracker</li>
            <li>• Portfolio Public Companies</li>
            <li>• IPO Listing Tracker</li>
          </ul>
          <button
            className="tracker-button"
            onClick={() => navigate('/stock-tracker')}
          >
            Public Market Tracker
          </button>
        </div>

        <div className="feature-card">
          <h2>🧬 Company Intelligence</h2>
          <p>Extract drug pipelines, competitors, and market analysis from documents</p>
          <button
            className="tracker-button"
            onClick={() => navigate('/ai-search')}
          >
            Explore Features
          </button>
        </div>
      </div>

      <footer className="footer">
        <p>&copy; 2025 AI Search Platform. All rights reserved.</p>
      </footer>
    </div>
  );
}

export default Home;
