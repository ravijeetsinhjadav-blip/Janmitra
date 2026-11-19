import React from 'react';

const NAV_ITEMS = [
  { id: 'overview', label: 'Dashboard Overview', icon: '📊', phase: 'Live' },
  { id: 'schemes', label: 'Government Schemes', icon: '📜', phase: 'Active' },
  { id: 'users', label: 'Citizen Users', icon: '👥', phase: 'Active' },
  { id: 'applications', label: 'Tracked Applications', icon: '📑', phase: 'Live' },
  { id: 'subscriptions', label: 'Subscriptions & Revenue', icon: '💳', phase: 'Premium' },
  { id: 'documents', label: 'Document Intelligence', icon: '🔍', phase: 'Vault' },
  { id: 'settings', label: 'System Configuration', icon: '⚙️', phase: 'Config' },
];

export default function Sidebar({ activeTab, onSelectTab }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h2>🏛️ JanMitra Assist</h2>
        <p className="sidebar-tagline">Administration & Governance Console</p>
      </div>

      <nav className="sidebar-nav">
        {NAV_ITEMS.map((item) => (
          <button
            key={item.id}
            className={`nav-item ${activeTab === item.id ? 'active' : ''}`}
            onClick={() => onSelectTab(item.id)}
          >
            <span className="nav-label">
              <span className="nav-icon">{item.icon}</span>
              {item.label}
            </span>
            <span className="badge-phase">{item.phase}</span>
          </button>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div>MCA Major Project: JanMitra Assist</div>
        <div style={{ color: '#94a3b8', marginTop: '0.25rem' }}>Full Stack Phase 9 Complete</div>
      </div>
    </aside>
  );
}
