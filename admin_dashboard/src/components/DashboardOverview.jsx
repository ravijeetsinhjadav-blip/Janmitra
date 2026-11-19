import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';

export default function DashboardOverview() {
  const { token, apiBase } = useAuth();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchStats = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${apiBase}/admin/stats`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error(`HTTP Error ${res.status}: Failed to fetch admin metrics`);
      const data = await res.json();
      setStats(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  const stackItems = [
    { component: 'Backend API', tech: 'Python FastAPI', status: 'Operational (Port 8000)' },
    { component: 'Admin Dashboard', tech: 'React.js + Vite', status: 'Active (Port 3000)' },
    { component: 'Mobile Client', tech: 'Flutter 3.x (Dart)', status: 'Android & iOS Production Ready' },
    { component: 'Primary Database', tech: 'PostgreSQL + SQLAlchemy', status: 'Connected' },
    { component: 'Document OCR', tech: 'Tesseract OCR + PyPDF2', status: 'Integrated & Active' },
    { component: 'Push Notifications', tech: 'Firebase Cloud Messaging (FCM)', status: 'Integrated (Phase 8.2)' },
  ];

  return (
    <div className="overview-container">
      {/* Platform Boundary Advisory Banner */}
      <div className="boundary-banner">
        <div className="boundary-icon">ℹ️</div>
        <div className="boundary-content">
          <strong>Civic Platform Boundary Disclaimer:</strong> JanMitra Assist is strictly an AI-powered advisory,
          document intelligence, and self-reported application tracking system. JanMitra Assist does not issue official
          government decisions, approve or reject applications, or replace government portal workflows.
        </div>
      </div>

      <div className="welcome-card">
        <div className="welcome-header">
          <div>
            <h3>JanMitra Assist – Administration & Platform Governance</h3>
            <p>
              Unified administrative control room for scheme repository maintenance, citizen user oversight,
              document intelligence pipeline metrics, and citizen application tracking analytics.
            </p>
          </div>
          <button className="btn-refresh" onClick={fetchStats} disabled={loading} title="Refresh KPI Metrics">
            {loading ? 'Refreshing...' : '🔄 Refresh Metrics'}
          </button>
        </div>
      </div>

      {error && (
        <div className="alert-box error">
          <span>⚠️ {error}</span>
          <button className="btn-sm" onClick={fetchStats}>Retry</button>
        </div>
      )}

      {/* KPI Cards Grid */}
      <div className="metrics-grid">
        <div className="metric-card primary">
          <div className="metric-card-title">Registered Citizens</div>
          <div className="metric-card-value">
            {stats ? stats.total_citizens : '—'}
          </div>
          <div className="metric-card-desc">
            {stats ? `${stats.active_citizens} Active Citizens` : 'Loading citizens...'}
          </div>
        </div>

        <div className="metric-card success">
          <div className="metric-card-title">Government Schemes</div>
          <div className="metric-card-value">
            {stats ? stats.total_schemes : '—'}
          </div>
          <div className="metric-card-desc">
            {stats ? `${stats.active_schemes} Active Schemes Available` : 'Loading schemes...'}
          </div>
        </div>

        <div className="metric-card warning">
          <div className="metric-card-title">Tracked Applications</div>
          <div className="metric-card-value">
            {stats ? stats.total_applications : '—'}
          </div>
          <div className="metric-card-desc">
            Citizen Self-Reported Portals
          </div>
        </div>

        <div className="metric-card info">
          <div className="metric-card-title">Documents In Vault</div>
          <div className="metric-card-value">
            {stats ? stats.total_documents : '—'}
          </div>
          <div className="metric-card-desc">
            {stats ? `${stats.ocr_completed_documents} OCR processed` : 'Loading vault...'}
          </div>
        </div>
      </div>

      {/* Secondary Metrics Row */}
      <div className="metrics-grid secondary">
        <div className="metric-card compact">
          <div className="metric-card-title">Readiness Assessments</div>
          <div className="metric-card-value">{stats ? stats.total_assessments : '—'}</div>
          <div className="metric-card-desc">AI Evaluation Audits</div>
        </div>

        <div className="metric-card compact">
          <div className="metric-card-title">Premium Subscriptions</div>
          <div className="metric-card-value">{stats ? stats.total_active_premium_subscriptions : '—'}</div>
          <div className="metric-card-desc">Active Paid Tiers</div>
        </div>

        <div className="metric-card compact">
          <div className="metric-card-title">Captured Payments</div>
          <div className="metric-card-value">{stats ? stats.total_payments_captured : '—'}</div>
          <div className="metric-card-desc">Assisted Submissions</div>
        </div>

        <div className="metric-card compact">
          <div className="metric-card-title">Platform Status</div>
          <div className="metric-card-value" style={{ color: 'var(--success)', textTransform: 'capitalize' }}>
            {stats ? stats.system_status : 'Operational'}
          </div>
          <div className="metric-card-desc">FastAPI Backend Online</div>
        </div>
      </div>

      {/* Application Status Distribution */}
      {stats && stats.applications_by_status && (
        <div className="info-panel mb-4">
          <div className="panel-header">
            <h4>Citizen-Reported Application Status Distribution</h4>
            <span className="badge-tag info">Citizen Self-Reported</span>
          </div>
          <p className="panel-desc">
            Aggregation of government portal applications tracked by registered citizens within the JanMitra Assist mobile client.
          </p>
          <div className="status-bars-grid">
            {Object.entries(stats.applications_by_status).map(([st, cnt]) => {
              const maxVal = Math.max(...Object.values(stats.applications_by_status), 1);
              const pct = Math.round((cnt / maxVal) * 100);
              return (
                <div key={st} className="status-bar-card">
                  <div className="status-bar-meta">
                    <span className="status-label">{st}</span>
                    <span className="status-count">{cnt}</span>
                  </div>
                  <div className="progress-track">
                    <div className={`progress-fill status-${st.toLowerCase().replace(/\s+/g, '-')}`} style={{ width: `${pct}%` }}></div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Architecture & Stack Status */}
      <div className="info-panel">
        <div className="panel-header">
          <h4>Technology Stack & Subsystem Status</h4>
          <span className="badge-tag success">Phase 8 Complete</span>
        </div>
        <table className="info-table">
          <thead>
            <tr>
              <th>Architecture Subsystem</th>
              <th>Technology Stack</th>
              <th>Operational Status</th>
            </tr>
          </thead>
          <tbody>
            {stackItems.map((item, idx) => (
              <tr key={idx}>
                <td style={{ fontWeight: 600 }}>{item.component}</td>
                <td><code>{item.tech}</code></td>
                <td>
                  <span className="status-indicator">
                    <span className="status-dot"></span>
                    {item.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
