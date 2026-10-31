import React from 'react';

const NAV_ITEMS = [
  { id: 'overview', label: 'Dashboard Overview', phase: 'Phase 1' },
  { id: 'schemes', label: 'Schemes Management', phase: 'Phase 2' },
  { id: 'documents', label: 'Document Intelligence', phase: 'Phase 3' },
  { id: 'eligibility', label: 'Eligibility Rules', phase: 'Phase 4' },
  { id: 'readiness', label: 'Citizen Readiness Reports', phase: 'Phase 5' },
  { id: 'settings', label: 'System Configuration', phase: 'Phase 1' },
];

export default function Sidebar({ activeTab, onSelectTab }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h2>🏛️ JanMitra Assist</h2>
        <p className="sidebar-tagline">Administration Console</p>
      </div>

      <nav className="sidebar-nav">
        {NAV_ITEMS.map((item) => (
          <button
            key={item.id}
            className={`nav-item ${activeTab === item.id ? 'active' : ''}`}
            onClick={() => onSelectTab(item.id)}
          >
            <span>{item.label}</span>
            <span className="badge-phase">{item.phase}</span>
          </button>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div>MCA Major Project</div>
        <div style={{ color: '#64748b', marginTop: '0.2rem' }}>Version 1.0.0-phase1</div>
      </div>
    </aside>
  );
}
