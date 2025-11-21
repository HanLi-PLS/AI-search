import { lazy, Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import './App.css';

// Code splitting: Lazy load route components
const Home = lazy(() => import('./pages/Home'));
const StockTracker = lazy(() => import('./pages/StockTracker'));
const StockDetail = lazy(() => import('./pages/StockDetail'));
const Watchlist = lazy(() => import('./pages/Watchlist'));
const AISearch = lazy(() => import('./pages/AISearch'));
const Login = lazy(() => import('./pages/Login'));
const Register = lazy(() => import('./pages/Register'));
const AdminUsers = lazy(() => import('./pages/AdminUsers'));

function App() {
  return (
    <AuthProvider>
      <Router>
        <Suspense fallback={<div className="loading-spinner">Loading...</div>}>
          <Routes>
            {/* Public routes */}
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />

            {/* Protected routes */}
            <Route path="/" element={
              <ProtectedRoute>
                <Home />
              </ProtectedRoute>
            } />
            <Route path="/stock-tracker" element={
              <ProtectedRoute>
                <StockTracker />
              </ProtectedRoute>
            } />
            <Route path="/stock-tracker/:ticker" element={
              <ProtectedRoute>
                <StockDetail />
              </ProtectedRoute>
            } />
            <Route path="/watchlist" element={
              <ProtectedRoute>
                <Watchlist />
              </ProtectedRoute>
            } />
            <Route path="/ai-search" element={
              <ProtectedRoute>
                <AISearch />
              </ProtectedRoute>
            } />

            {/* Admin routes */}
            <Route path="/admin/users" element={
              <ProtectedRoute requireAdmin>
                <AdminUsers />
              </ProtectedRoute>
            } />
          </Routes>
        </Suspense>
      </Router>
    </AuthProvider>
  );
}

export default App;
