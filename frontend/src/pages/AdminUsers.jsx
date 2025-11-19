import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { authAPI } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import './AdminUsers.css';

function AdminUsers() {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionLoading, setActionLoading] = useState(null);

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    try {
      const response = await authAPI.getUsers();
      setUsers(response.users);
    } catch (err) {
      setError('Failed to load users');
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (userId) => {
    setActionLoading(userId);
    try {
      await authAPI.approveUser(userId);
      await fetchUsers();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to approve user');
    } finally {
      setActionLoading(null);
    }
  };

  const handleRevoke = async (userId) => {
    setActionLoading(userId);
    try {
      await authAPI.revokeUser(userId);
      await fetchUsers();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to revoke user');
    } finally {
      setActionLoading(null);
    }
  };

  const handleDelete = async (userId, email) => {
    if (!confirm(`Are you sure you want to delete ${email}?`)) {
      return;
    }
    setActionLoading(userId);
    try {
      await authAPI.deleteUser(userId);
      await fetchUsers();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to delete user');
    } finally {
      setActionLoading(null);
    }
  };

  const handleToggleAdmin = async (userId) => {
    setActionLoading(userId);
    try {
      await authAPI.toggleAdmin(userId);
      await fetchUsers();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to toggle admin status');
    } finally {
      setActionLoading(null);
    }
  };

  if (loading) {
    return (
      <div className="admin-container">
        <div className="loading">Loading users...</div>
      </div>
    );
  }

  return (
    <div className="admin-container">
      <header className="admin-header">
        <div className="header-left">
          <button className="back-button" onClick={() => navigate('/')}>
            ← Back to Home
          </button>
          <h1>User Management</h1>
        </div>
        <button className="logout-button" onClick={logout}>
          Logout
        </button>
      </header>

      {error && <div className="admin-error">{error}</div>}

      <div className="users-table-container">
        <table className="users-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Status</th>
              <th>Role</th>
              <th>Registered</th>
              <th>Last Login</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map((user) => (
              <tr key={user.id}>
                <td>{user.name}</td>
                <td>{user.email}</td>
                <td>
                  <span className={`status-badge ${user.is_approved ? 'approved' : 'pending'}`}>
                    {user.is_approved ? 'Approved' : 'Pending'}
                  </span>
                </td>
                <td>
                  <span className={`role-badge ${user.is_admin ? 'admin' : 'user'}`}>
                    {user.is_admin ? 'Admin' : 'User'}
                  </span>
                </td>
                <td>{new Date(user.created_at).toLocaleDateString()}</td>
                <td>{user.last_login ? new Date(user.last_login).toLocaleString() : 'Never'}</td>
                <td className="actions-cell">
                  {!user.is_approved ? (
                    <button
                      className="action-button approve"
                      onClick={() => handleApprove(user.id)}
                      disabled={actionLoading === user.id}
                    >
                      Approve
                    </button>
                  ) : (
                    <button
                      className="action-button revoke"
                      onClick={() => handleRevoke(user.id)}
                      disabled={actionLoading === user.id}
                    >
                      Revoke
                    </button>
                  )}
                  <button
                    className="action-button toggle-admin"
                    onClick={() => handleToggleAdmin(user.id)}
                    disabled={actionLoading === user.id}
                  >
                    {user.is_admin ? 'Remove Admin' : 'Make Admin'}
                  </button>
                  <button
                    className="action-button delete"
                    onClick={() => handleDelete(user.id, user.email)}
                    disabled={actionLoading === user.id}
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="users-summary">
        Total: {users.length} users |
        Approved: {users.filter(u => u.is_approved).length} |
        Pending: {users.filter(u => !u.is_approved).length}
      </div>
    </div>
  );
}

export default AdminUsers;
