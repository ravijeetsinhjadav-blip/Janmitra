import React from 'react';

export default function DashboardOverview() {
  const stackItems = [
    { component: 'Backend API', tech: 'Python FastAPI', status: 'Ready (Port 8000)' },
    { component: 'Admin Dashboard', tech: 'React.js + Vite', status: 'Active (Port 3000)' },
    { component: 'Mobile Application', tech: 'Flutter (Dart)', status: 'Scaffolded (Android Target)' },
    { component: 'Database', tech: 'PostgreSQL', status: 'Target (Phase 2)' },
    { component: 'Document OCR', tech: 'Tesseract OCR', status: 'Target (Phase 3)' },
    { component: 'AI Runtime', tech: 'Ollama + Llama 3.2 1B', status: 'Target (Phase 3)' },
  ];

  return (
    <div>
      <div className="welcome-card">
        <h3>JanMitra Assist – AI-Powered Government Service Eligibility</h3>
        <p>
          Welcome to the JanMitra Assist Administration Dashboard. This portal is designed to manage
          government schemes, document verification requirements, eligibility assessment criteria,
          and citizen application checklists. Final service applications are fulfilled through official government portals.
        </p>
      </div>

      <div className="metrics-grid">
        <div className="metric-card">
          <div className="metric-card-title">Development Phase</div>
          <div className="metric-card-value">Phase 1</div>
          <div className="metric-card-desc">Project Setup & Foundation</div>
        </div>

        <div className="metric-card">
          <div className="metric-card-title">Backend Status</div>
          <div className="metric-card-value" style={{ color: 'var(--success)' }}>Online</div>
          <div className="metric-card-desc">FastAPI /health verified</div>
        </div>

        <div className="metric-card">
          <div className="metric-card-title">Mobile App Target</div>
          <div className="metric-card-value">Flutter</div>
          <div className="metric-card-desc">Citizen-facing mobile client</div>
        </div>

        <div className="metric-card">
          <div className="metric-card-title">Security & Config</div>
          <div className="metric-card-value">Strict</div>
          <div className="metric-card-desc">No secrets exposed; env templated</div>
        </div>
      </div>

      <div className="info-panel">
        <h4>Technology Stack & Module Status</h4>
        <table className="info-table">
          <thead>
            <tr>
              <th>Architecture Layer</th>
              <th>Approved Technology</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {stackItems.map((item, idx) => (
              <tr key={idx}>
                <td style={{ fontWeight: 500 }}>{item.component}</td>
                <td><code>{item.tech}</code></td>
                <td>{item.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
