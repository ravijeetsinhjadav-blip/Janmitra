import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';

export default function DocumentIntelligence() {
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
      if (!res.ok) throw new Error(`HTTP Error ${res.status}: Failed to fetch document metrics`);
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

  return (
    <div className="document-intelligence-container">
      {/* Platform Boundary Advisory */}
      <div className="boundary-banner">
        <div className="boundary-icon">📄</div>
        <div className="boundary-content">
          <strong>Document Intelligence & Privacy Governance:</strong> All citizen documents are strictly isolated by citizen
          user ID. Document text extraction (OCR) and deterministic field validations are used solely to assess scheme readiness.
          Raw identity proof documents are never submitted to third-party endpoints or publicly accessible buckets.
        </div>
      </div>

      <div className="welcome-card">
        <div className="welcome-header">
          <div>
            <h3>Document Intelligence & Scheme Readiness Engine</h3>
            <p>
              Overview of uploaded citizen proofs, automated optical character recognition (OCR), text extraction pipelines,
              and AI readiness assessments.
            </p>
          </div>
          <button className="btn-refresh" onClick={fetchStats} disabled={loading} title="Refresh Metrics">
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
          <div className="metric-card-title">Total Vault Documents</div>
          <div className="metric-card-value">
            {stats ? stats.total_documents : '—'}
          </div>
          <div className="metric-card-desc">Uploaded across all citizen accounts</div>
        </div>

        <div className="metric-card success">
          <div className="metric-card-title">OCR Text Extracted</div>
          <div className="metric-card-value">
            {stats ? stats.ocr_completed_documents : '—'}
          </div>
          <div className="metric-card-desc">Processed via PDF text / Vision OCR</div>
        </div>

        <div className="metric-card warning">
          <div className="metric-card-title">Manual Review Queue</div>
          <div className="metric-card-value">
            {stats ? stats.manual_review_documents : '—'}
          </div>
          <div className="metric-card-desc">Flagged for blur or low confidence</div>
        </div>

        <div className="metric-card info">
          <div className="metric-card-title">Readiness Assessments</div>
          <div className="metric-card-value">
            {stats ? stats.total_assessments : '—'}
          </div>
          <div className="metric-card-desc">Evaluated against scheme requirements</div>
        </div>
      </div>

      {/* Pipeline Specifications */}
      <div className="scheme-details-card" style={{ marginTop: '1.5rem', background: '#ffffff', borderRadius: '12px', padding: '1.5rem', border: '1px solid #e2e8f0' }}>
        <h4 style={{ color: '#1e293b', marginBottom: '1rem' }}>⚙️ Document Processing Pipeline Architecture</h4>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
          <div style={{ padding: '1rem', background: '#f8fafc', borderRadius: '8px', border: '1px solid #cbd5e1' }}>
            <h5 style={{ color: '#0f172a', marginBottom: '0.5rem' }}>📥 Ingestion & Validation</h5>
            <ul style={{ paddingLeft: '1.2rem', color: '#475569', fontSize: '0.9rem', lineHeight: '1.6' }}>
              <li><strong>Accepted Formats:</strong> PDF, PNG, JPEG, JPG</li>
              <li><strong>Max Payload Size:</strong> 10 MB per document</li>
              <li><strong>File Integrity:</strong> SHA-256 integrity hash on upload</li>
              <li><strong>Storage Isolation:</strong> UUID per-citizen isolated paths</li>
            </ul>
          </div>

          <div style={{ padding: '1rem', background: '#f8fafc', borderRadius: '8px', border: '1px solid #cbd5e1' }}>
            <h5 style={{ color: '#0f172a', marginBottom: '0.5rem' }}>🔍 Optical Character Recognition (OCR)</h5>
            <ul style={{ paddingLeft: '1.2rem', color: '#475569', fontSize: '0.9rem', lineHeight: '1.6' }}>
              <li><strong>Digital PDF:</strong> Direct vector font text extraction via PyPDF2</li>
              <li><strong>Scanned / Images:</strong> Google Cloud Vision API with Tesseract local fallback</li>
              <li><strong>Confidence Scoring:</strong> Threshold checks with manual review flags</li>
              <li><strong>Redaction:</strong> Aadhaar / Sensitive PII masked in log streams</li>
            </ul>
          </div>

          <div style={{ padding: '1rem', background: '#f8fafc', borderRadius: '8px', border: '1px solid #cbd5e1' }}>
            <h5 style={{ color: '#0f172a', marginBottom: '0.5rem' }}>🤖 AI Scheme Readiness & Matching</h5>
            <ul style={{ paddingLeft: '1.2rem', color: '#475569', fontSize: '0.9rem', lineHeight: '1.6' }}>
              <li><strong>Deterministic Rules:</strong> Age, income, land holding & category criteria</li>
              <li><strong>Document Completeness:</strong> Mandatory document checklist verification</li>
              <li><strong>Advisory Readiness Score:</strong> 0–100% readiness indicator (Advisory only)</li>
              <li><strong>Disclaimer Enforcement:</strong> Never claims official government approval</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}

