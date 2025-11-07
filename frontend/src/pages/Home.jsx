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
        <div className="feature-card">
          <h2>🔍 AI-Powered Search</h2>
          <p>Advanced AI algorithms to find exactly what you're looking for</p>
        </div>

        <div className="feature-card highlight">
          <h2>📊 HKEX Biotech Tracker</h2>
          <p>Track real-time stock prices for HKEX 18A biotech companies</p>
          <button
            className="tracker-button"
            onClick={() => navigate('/stock-tracker')}
          >
            Open Stock Tracker
          </button>
        </div>

        <div className="feature-card">
          <h2>📚 Document Analysis</h2>
          <p>Extract insights from your documents using advanced RAG technology</p>
        </div>
      </div>

      <footer className="footer">
        <p>&copy; 2025 AI Search Platform. All rights reserved.</p>
      </footer>
    </div>
  );
}

export default Home;
