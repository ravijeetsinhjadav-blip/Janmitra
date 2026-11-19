import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';

export default function ApplicationMonitoring() {
  const { token, apiBase } = useAuth();
  const [applications, setApplications] = useState([]);
  const [statusSummary, setStatusSummary] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [statusFilter, setStatusFilter] = useState('');

  const statusList = [
    'Draft',
    'Submitted',
    'Under Review',
    'Approved',
    'Rejected',
    'Action Required',
  ];

  const fetchApplications = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (statusFilter && statusFilter !== 'All') params.append('status', statusFilter);

      const res = await fetch(`${apiBase}/admin/applications?${params.toString()}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error(`HTTP Error ${res.status}: Failed to fetch applications`);
      const data = await res.json();
      setApplications(data.applications || []);
      if (data.status_summary) {
        setStatusSummary(data.status_summary);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchApplications();
  }, [statusFilter]);

  return (
    <div className="applications-monitoring-container">
      {/* Explicit Platform Disclaimer */}
      <div className="boundary-banner">
        <div className="boundary-icon">🛡️</div>
        <div className="boundary-content">
          <strong>Civic Platform Boundary Disclaimer:</strong> Application tracking within JanMitra Assist is strictly
          maintained by citizens for personal reminders and record-keeping. The statuses shown below are self-reported
          by users based on their external submissions on official government portals. JanMitra Assist does not approve,
          reject, process, or verify official applications.
        </div>
      </div>

      <div className="section-header">
        <div>
          <h3>Citizen Application Tracking Oversight</h3>
          <p>
            Administrative monitoring of citizen-maintained application records across published welfare schemes.
          </p>
        </div>
        <button className="btn-secondary" onClick={fetchApplications} disabled={loading}>
          {loading ? 'Refreshing...' : '🔄 Refresh Data'}
        </button>
      </div>

      {/* Status Filter Chips */}
      <div className="status-filters-row">
        <button
          className={`filter-chip ${statusFilter === '' || statusFilter === 'All' ? 'active' : ''}`}
          onClick={() => setStatusFilter('All')}
        >
          All Applications ({Object.values(statusSummary).reduce((a, b) => a + b, 0)})
        </button>
        {statusList.map((st) => (
          <button
            key={st}
            className={`filter-chip ${statusFilter === st ? 'active' : ''}`}
            onClick={() => setStatusFilter(st)}
          >
            {st} ({statusSummary[st] || 0})
          </button>
        ))}
      </div>

      {error && <div className="alert-box error">⚠️ {error}</div>}

      {/* Applications Table */}
      <div className="table-responsive">
        <table className="data-table">
          <thead>
            <tr>
              <th>Scheme Title</th>
              <th>Category</th>
              <th>Citizen User UUID</th>
              <th>Application Ref Number</th>
              <th>Portal Submission Date</th>
              <th>Status (Citizen Self-Reported)</th>
              <th>Last Updated</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={7} className="text-center py-4">Loading tracked application entries...</td>
              </tr>
            ) : applications.length === 0 ? (
              <tr>
                <td colSpan={7} className="text-center py-4">No applications found under this status.</td>
              </tr>
            ) : (
              applications.map((app) => (
                <tr key={app.id}>
                  <td>
                    <strong>{app.scheme_name}</strong>
                  </td>
                  <td>
                    <span className="badge-category">{app.category || 'General'}</span>
                  </td>
                  <td>
                    <code className="uuid-short" title={app.user_id}>
                      {app.user_id.slice(0, 8)}...
                    </code>
                  </td>
                  <td>
                    {app.application_reference_number ? (
                      <span className="ref-number">{app.application_reference_number}</span>
                    ) : (
                      <span className="text-muted">Not Issued</span>
                    )}
                  </td>
                  <td>
                    {app.submission_date
                      ? new Date(app.submission_date).toLocaleDateString()
                      : 'Not submitted yet'}
                  </td>
                  <td>
                    <span className={`status-pill status-${app.status.toLowerCase().replace(/\s+/g, '-')}`}>
                      {app.status}
                      {(app.status === 'Approved' || app.status === 'Rejected') && (
                        <span className="status-subtag"> (Citizen Reported)</span>
                      )}
                    </span>
                  </td>
                  <td>
                    {app.updated_at
                      ? new Date(app.updated_at).toLocaleDateString()
                      : '—'}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

