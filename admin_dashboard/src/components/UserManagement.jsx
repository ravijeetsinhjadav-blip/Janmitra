import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';

export default function UserManagement() {
  const { token, apiBase } = useAuth();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [selectedUser, setSelectedUser] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const fetchUsers = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (searchQuery.trim()) params.append('query', searchQuery.trim());
      if (statusFilter !== '') params.append('is_active', statusFilter);

      const res = await fetch(`${apiBase}/admin/users?${params.toString()}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error(`HTTP Error ${res.status}: Failed to fetch citizens`);
      const data = await res.json();
      setUsers(data.users || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, [statusFilter]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    fetchUsers();
  };

  const handleToggleStatus = async (user) => {
    const updatedStatus = !user.is_active;
    const identifier = user.email || user.mobile_number || user.id;
    const confirmMsg = updatedStatus
      ? `Activate citizen account ${identifier}?`
      : `Deactivate citizen account ${identifier}? The user will be barred from login and services.`;

    if (!window.confirm(confirmMsg)) return;

    try {
      const res = await fetch(`${apiBase}/admin/users/${user.id}/status`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ is_active: updatedStatus }),
      });
      if (!res.ok) throw new Error('Failed to update citizen account status');
      setUsers((prev) =>
        prev.map((u) => (u.id === user.id ? { ...u, is_active: updatedStatus } : u))
      );
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  };

  const handleViewUserDetail = async (userId) => {
    setDetailLoading(true);
    try {
      const res = await fetch(`${apiBase}/admin/users/${userId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('Failed to load citizen profile details');
      const data = await res.json();
      setSelectedUser(data);
    } catch (err) {
      alert(`Error loading citizen: ${err.message}`);
    } finally {
      setDetailLoading(false);
    }
  };

  return (
    <div className="users-management-container">
      <div className="section-header">
        <div>
          <h3>Citizen User Administration</h3>
          <p>
            Monitor registered citizen accounts, view eligibility profiles, check document vault activity, and manage access privileges.
          </p>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="filter-bar">
        <form onSubmit={handleSearchSubmit} className="search-form">
          <input
            type="text"
            placeholder="Search by citizen mobile number..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          <button type="submit" className="btn-secondary">Search</button>
        </form>

        <div className="filters-group">
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="">All Citizens</option>
            <option value="true">Active Accounts Only</option>
            <option value="false">Deactivated Accounts Only</option>
          </select>
        </div>
      </div>

      {error && <div className="alert-box error">⚠️ {error}</div>}

      {/* Citizens Table */}
      <div className="table-responsive">
        <table className="data-table">
          <thead>
            <tr>
              <th>Citizen Email / Identifier</th>
              <th>Full Name</th>
              <th>State / District</th>
              <th>System Role</th>
              <th>Joined Date</th>
              <th>Account Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={7} className="text-center py-4">Loading citizen records...</td>
              </tr>
            ) : users.length === 0 ? (
              <tr>
                <td colSpan={7} className="text-center py-4">No citizen records found.</td>
              </tr>
            ) : (
              users.map((u) => (
                <tr key={u.id}>
                  <td>
                    <strong>{u.email || u.mobile_number || 'Citizen'}</strong>
                    {u.email && u.mobile_number && (
                      <div style={{ fontSize: '0.8rem', color: '#64748b' }}>{u.mobile_number}</div>
                    )}
                  </td>
                  <td>{u.full_name || '—'}</td>
                  <td>
                    {u.state ? `${u.district || ''}, ${u.state}` : 'Profile Pending'}
                  </td>
                  <td>
                    <span className="badge-category">{u.role}</span>
                  </td>
                  <td>
                    {u.created_at ? new Date(u.created_at).toLocaleDateString() : '—'}
                  </td>
                  <td>
                    <span className={`status-pill ${u.is_active ? 'active' : 'inactive'}`}>
                      {u.is_active ? 'Active' : 'Deactivated'}
                    </span>
                  </td>
                  <td>
                    <div className="actions-cell">
                      <button
                        className="btn-action"
                        onClick={() => handleViewUserDetail(u.id)}
                        title="View Detailed Profile"
                      >
                        👁️
                      </button>
                      <button
                        className={`btn-action ${u.is_active ? 'deactivate' : 'activate'}`}
                        onClick={() => handleToggleStatus(u)}
                        title={u.is_active ? 'Deactivate Account' : 'Activate Account'}
                      >
                        {u.is_active ? '🚫' : '✅'}
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Citizen Profile Detail Modal */}
      {selectedUser && (
        <div className="modal-backdrop">
          <div className="modal-dialog">
            <div className="modal-header">
              <h4>Citizen Profile: {selectedUser.email || selectedUser.mobile_number || selectedUser.id}</h4>
              <button className="btn-close" onClick={() => setSelectedUser(null)}>✕</button>
            </div>
            <div className="modal-body">
              <div className="user-kpis-grid">
                <div className="user-kpi-item">
                  <span className="kpi-label">Vault Documents</span>
                  <span className="kpi-val">{selectedUser.documents_count}</span>
                </div>
                <div className="user-kpi-item">
                  <span className="kpi-label">Tracked Applications</span>
                  <span className="kpi-val">{selectedUser.applications_count}</span>
                </div>
                <div className="user-kpi-item">
                  <span className="kpi-label">Subscription Tier</span>
                  <span className="kpi-val">{selectedUser.subscription_plan}</span>
                </div>
              </div>

              <h5 className="mt-4 mb-2">Account & Demographic Profile</h5>
              <div className="profile-details-table mb-3">
                <div><strong>Email:</strong> {selectedUser.email || 'Not provided'}</div>
                <div><strong>Mobile:</strong> {selectedUser.mobile_number || 'Not provided'}</div>
                <div><strong>Role:</strong> {selectedUser.role}</div>
                <div><strong>Active Status:</strong> {selectedUser.is_active ? 'Active' : 'Disabled'}</div>
              </div>
              {selectedUser.profile ? (
                <div className="profile-details-table">
                  <div><strong>Full Name:</strong> {selectedUser.profile.full_name || 'Not filled'}</div>
                  <div><strong>Gender:</strong> {selectedUser.profile.gender || 'Not filled'}</div>
                  <div><strong>Date of Birth:</strong> {selectedUser.profile.date_of_birth || 'Not filled'}</div>
                  <div><strong>Annual Income:</strong> ₹{selectedUser.profile.annual_income?.toLocaleString() || '0'}</div>
                  <div><strong>Social Category:</strong> {selectedUser.profile.social_category || 'General'}</div>
                  <div><strong>Occupation:</strong> {selectedUser.profile.occupation || 'Not filled'}</div>
                  <div><strong>State:</strong> {selectedUser.profile.state || 'Not filled'}</div>
                  <div><strong>District:</strong> {selectedUser.profile.district || 'Not filled'}</div>
                </div>
              ) : (
                <p className="text-muted">Citizen has not completed demographic profile setup yet.</p>
              )}
            </div>
            <div className="modal-footer">
              <button className="btn-secondary" onClick={() => setSelectedUser(null)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

