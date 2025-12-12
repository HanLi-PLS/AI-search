import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import './Home.css';

function Home() {
  const navigate = useNavigate();
  const { user, logout, isAdmin } = useAuth();

  return (
    <div className="home-container">
      <div className="user-header">
        <div className="user-info">
          Welcome, {user?.name || 'User'}
          {isAdmin && <span className="admin-badge">Admin</span>}
        </div>
        <div className="user-actions">
          {isAdmin && (
            <button className="admin-link" onClick={() => navigate('/admin/users')}>
              Manage Users
            </button>
          )}
          <button className="logout-btn" onClick={logout}>
            Logout
          </button>
        </div>
      </div>

      <div className="hero-section">
        <h1>AI Search Platform</h1>
        <p className="subtitle">
          Your intelligent search companion for comprehensive information retrieval
        </p>
      </div>

      <div className="features-section">
        <div className="feature-card highlight">
          <h2>🔍 Unified AI Search</h2>
          <p>Intelligent search across documents and web with multi-model reasoning</p>
          <ul className="tracker-features">
            <li>• Multi-source search (Files + Online)</li>
            <li>• Multi-model reasoning (GPT-5 Pro, Gemini 3 Pro)</li>
            <li>• Sequential analysis & extraction</li>
          </ul>
          <button
            className="tracker-button"
            onClick={() => navigate('/ai-search')}
          >
            Launch Search
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
      </div>

      <footer className="footer">
        <p>&copy; 2025 AI Search Platform. All rights reserved.</p>
      </footer>
    </div>
  );
}

export default Home;
