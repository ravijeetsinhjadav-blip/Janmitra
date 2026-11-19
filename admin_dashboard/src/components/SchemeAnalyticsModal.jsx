import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';

export default function SchemeAnalyticsModal({ scheme, onClose }) {
  const { token, apiBase } = useAuth();
  const [activeTab, setActiveTab] = useState('analytics'); // 'analytics', 'import', 'audit', 'rules'
  const [datasets, setDatasets] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [categoryRules, setCategoryRules] = useState([]);
  const [categoryDocs, setCategoryDocs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [message, setMessage] = useState(null);

  // Import form state
  const [importForm, setImportForm] = useState({
    source_name: '',
    source_url: '',
    report_title: '',
    geographic_scope: 'National',
    reporting_period: 'FY 2024-25',
    metric_type: 'unique_beneficiaries',
    metric_definition: '',
    total_beneficiaries: '',
    notes: '',
    female_count: '',
    male_count: '',
    state_breakdown_name: '',
    state_breakdown_count: '',
  });

  const fetchData = async () => {
    setLoading(true);
    setMessage(null);
    try {
      // 1. Fetch datasets
      const dsRes = await fetch(`${apiBase}/admin/schemes/${scheme.id}/analytics`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (dsRes.ok) {
        const data = await dsRes.json();
        setDatasets(data || []);
      }

      // 2. Fetch audit logs
      const auditRes = await fetch(`${apiBase}/admin/schemes/${scheme.id}/analytics/history`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (auditRes.ok) {
        const data = await auditRes.json();
        setAuditLogs(data || []);
      }

      // 3. Fetch category rules
      const rulesRes = await fetch(`${apiBase}/schemes/${scheme.id}/category-rules`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (rulesRes.ok) {
        const data = await rulesRes.json();
        setCategoryRules(data || []);
      }

      // 4. Fetch category documents
      const docsRes = await fetch(`${apiBase}/schemes/${scheme.id}/documents`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (docsRes.ok) {
        const data = await docsRes.json();
        setCategoryDocs(data || []);
      }
    } catch (err) {
      console.error('Error fetching scheme intelligence data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (scheme?.id) {
      fetchData();
    }
  }, [scheme]);

  const handlePublish = async (datasetId) => {
    setActionLoading(true);
    try {
      const res = await fetch(`${apiBase}/admin/schemes/${scheme.id}/analytics/${datasetId}/publish`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        setMessage({ type: 'success', text: 'Dataset successfully published for citizens.' });
        fetchData();
      } else {
        const err = await res.json();
        setMessage({ type: 'error', text: err.detail || 'Failed to publish dataset' });
      }
    } catch (e) {
      setMessage({ type: 'error', text: e.message });
    } finally {
      setActionLoading(false);
    }
  };

  const handleUnpublish = async (datasetId) => {
    setActionLoading(true);
    try {
      const res = await fetch(`${apiBase}/admin/schemes/${scheme.id}/analytics/${datasetId}/unpublish`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        setMessage({ type: 'success', text: 'Dataset unpublished from citizen view.' });
        fetchData();
      } else {
        const err = await res.json();
        setMessage({ type: 'error', text: err.detail || 'Failed to unpublish dataset' });
      }
    } catch (e) {
      setMessage({ type: 'error', text: e.message });
    } finally {
      setActionLoading(false);
    }
  };

  const handleValidate = async (datasetId) => {
    setActionLoading(true);
    try {
      const res = await fetch(`${apiBase}/admin/schemes/${scheme.id}/analytics/${datasetId}/validate`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        setMessage({ type: 'success', text: 'Dataset marked as Verified.' });
        fetchData();
      }
    } catch (e) {
      setMessage({ type: 'error', text: e.message });
    } finally {
      setActionLoading(false);
    }
  };

  const handleImportSubmit = async (e) => {
    e.preventDefault();
    setActionLoading(true);
    setMessage(null);

    const total = parseInt(importForm.total_beneficiaries, 10) || 0;
    const breakdowns = [];

    if (importForm.female_count) {
      const count = parseInt(importForm.female_count, 10);
      breakdowns.push({
        dimension: 'gender',
        category_name: 'Female Beneficiaries',
        metric_value: count,
        percentage: total > 0 ? (count / total) * 100 : null,
      });
    }
    if (importForm.male_count) {
      const count = parseInt(importForm.male_count, 10);
      breakdowns.push({
        dimension: 'gender',
        category_name: 'Male Beneficiaries',
        metric_value: count,
        percentage: total > 0 ? (count / total) * 100 : null,
      });
    }
    if (importForm.state_breakdown_name && importForm.state_breakdown_count) {
      const count = parseInt(importForm.state_breakdown_count, 10);
      breakdowns.push({
        dimension: 'state',
        category_name: importForm.state_breakdown_name.trim(),
        metric_value: count,
        percentage: total > 0 ? (count / total) * 100 : null,
      });
    }

    try {
      const res = await fetch(`${apiBase}/admin/schemes/${scheme.id}/analytics/import`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          source_name: importForm.source_name,
          source_url: importForm.source_url,
          report_title: importForm.report_title || undefined,
          geographic_scope: importForm.geographic_scope,
          reporting_period: importForm.reporting_period,
          metric_type: importForm.metric_type,
          metric_definition: importForm.metric_definition || undefined,
          total_beneficiaries: total,
          notes: importForm.notes,
          breakdowns: breakdowns,
        }),
      });

      if (res.ok) {
        setMessage({ type: 'success', text: 'New dataset imported! Please review and publish.' });
        setActiveTab('analytics');
        fetchData();
      } else {
        const err = await res.json();
        setMessage({ type: 'error', text: err.detail || 'Failed to import dataset' });
      }
    } catch (e) {
      setMessage({ type: 'error', text: e.message });
    } finally {
      setActionLoading(false);
    }
  };

  const formatNumber = (num) => {
    if (num >= 10000000) return `${(num / 10000000).toFixed(1)} Crore`;
    if (num >= 100000) return `${(num / 100000).toFixed(1)} Lakh`;
    return num.toLocaleString();
  };

  return (
    <div className="modal-backdrop">
      <div className="modal-dialog" style={{ maxWidth: '850px', width: '95%' }}>
        <div className="modal-header">
          <div>
            <h4 style={{ margin: 0 }}>📊 Scheme Intelligence & Analytics</h4>
            <span style={{ fontSize: '13px', color: '#64748b' }}>{scheme.scheme_name}</span>
          </div>
          <button className="btn-close" onClick={onClose}>✕</button>
        </div>

        {/* Tab Navigation */}
        <div style={{ display: 'flex', borderBottom: '1px solid #e2e8f0', background: '#f8fafc', padding: '0 16px' }}>
          {[
            { id: 'analytics', label: 'Beneficiary Analytics' },
            { id: 'import', label: 'Import Dataset' },
            { id: 'rules', label: 'Category Rules & Documents' },
            { id: 'audit', label: 'Audit History' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                padding: '12px 18px',
                border: 'none',
                background: 'transparent',
                fontWeight: activeTab === tab.id ? 'bold' : 'normal',
                color: activeTab === tab.id ? '#1e3a8a' : '#64748b',
                borderBottom: activeTab === tab.id ? '2px solid #1e3a8a' : 'none',
                cursor: 'pointer',
                fontSize: '13px',
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="modal-body" style={{ maxHeight: '65vh', overflowY: 'auto' }}>
          {message && (
            <div style={{
              padding: '10px 14px',
              marginBottom: '16px',
              borderRadius: '6px',
              background: message.type === 'success' ? '#dcfce7' : '#fee2e2',
              color: message.type === 'success' ? '#15803d' : '#b91c1c',
              fontSize: '13px',
            }}>
              {message.text}
            </div>
          )}

          {loading ? (
            <div style={{ textAlign: 'center', padding: '40px' }}>Loading scheme intelligence...</div>
          ) : (
            <>
              {/* TAB 1: Beneficiary Analytics */}
              {activeTab === 'analytics' && (
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                    <h5 style={{ margin: 0 }}>Verified Government Datasets ({datasets.length})</h5>
                    <button className="btn-secondary" onClick={() => setActiveTab('import')} style={{ fontSize: '12px' }}>
                      + Import New Dataset
                    </button>
                  </div>

                  {datasets.length === 0 ? (
                    <div style={{ textAlign: 'center', padding: '30px', color: '#64748b' }}>
                      No beneficiary datasets uploaded yet for this scheme.
                    </div>
                  ) : (
                    datasets.map((ds) => (
                      <div key={ds.id} style={{
                        border: '1px solid #e2e8f0',
                        borderRadius: '8px',
                        padding: '16px',
                        marginBottom: '16px',
                        background: ds.is_published ? '#f0fdf4' : '#ffffff',
                      }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                          <div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                              <strong style={{ fontSize: '16px' }}>{formatNumber(ds.total_beneficiaries)} Beneficiaries</strong>
                              <span style={{
                                padding: '2px 8px',
                                borderRadius: '10px',
                                fontSize: '11px',
                                fontWeight: 'bold',
                                background: ds.is_published ? '#bbf7d0' : '#e2e8f0',
                                color: ds.is_published ? '#166534' : '#475569',
                              }}>
                                {ds.is_published ? '✓ Published (Visible to Citizens)' : 'Draft / Unpublished'}
                              </span>
                              <span style={{
                                padding: '2px 8px',
                                borderRadius: '10px',
                                fontSize: '11px',
                                background: '#dbeafe',
                                color: '#1e40af',
                              }}>
                                {ds.verification_status}
                              </span>
                            </div>
                            <div style={{ fontSize: '12px', color: '#64748b', marginTop: '4px' }}>
                              Period: <strong>{ds.reporting_period}</strong> | Scope: <strong>{ds.geographic_scope || 'National'}</strong> | Metric: <strong>{ds.metric_type}</strong> | Version: v{ds.dataset_version}
                            </div>
                            {ds.report_title && (
                              <div style={{ fontSize: '12px', color: '#1e293b', marginTop: '2px' }}>
                                Report: <strong>{ds.report_title}</strong>
                              </div>
                            )}
                            {ds.metric_definition && (
                              <div style={{ fontSize: '11px', color: '#475569', fontStyle: 'italic', marginTop: '2px' }}>
                                Definition: {ds.metric_definition}
                              </div>
                            )}
                            <div style={{ fontSize: '12px', color: '#334155', marginTop: '4px' }}>
                              Source: <strong>{ds.source_name}</strong> ({ds.source_url})
                            </div>
                          </div>

                          <div style={{ display: 'flex', gap: '8px' }}>
                            {ds.verification_status !== 'Verified' && (
                              <button
                                className="btn-secondary"
                                onClick={() => handleValidate(ds.id)}
                                disabled={actionLoading}
                                style={{ fontSize: '11px', padding: '4px 10px' }}
                              >
                                Validate
                              </button>
                            )}
                            {ds.is_published ? (
                              <button
                                className="btn-secondary"
                                onClick={() => handleUnpublish(ds.id)}
                                disabled={actionLoading}
                                style={{ fontSize: '11px', padding: '4px 10px', color: '#b91c1c' }}
                              >
                                Unpublish
                              </button>
                            ) : (
                              <button
                                className="btn-primary"
                                onClick={() => handlePublish(ds.id)}
                                disabled={actionLoading}
                                style={{ fontSize: '11px', padding: '4px 10px' }}
                              >
                                Approve & Publish
                              </button>
                            )}
                          </div>
                        </div>

                        {/* Breakdowns table */}
                        {ds.breakdowns && ds.breakdowns.length > 0 && (
                          <div style={{ marginTop: '14px', borderTop: '1px solid #e2e8f0', paddingTop: '10px' }}>
                            <div style={{ fontSize: '12px', fontWeight: 'bold', color: '#475569', marginBottom: '6px' }}>
                              Breakdowns ({ds.breakdowns.length} dimensions):
                            </div>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                              {ds.breakdowns.map((b) => (
                                <span key={b.id} style={{
                                  background: '#f1f5f9',
                                  padding: '4px 8px',
                                  borderRadius: '4px',
                                  fontSize: '11px',
                                  color: '#1e293b',
                                }}>
                                  <strong>{b.category_name}</strong> ({b.dimension}): {formatNumber(b.metric_value)}
                                  {b.percentage ? ` (${b.percentage.toFixed(1)}%)` : ''}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        {(!ds.breakdowns || ds.breakdowns.length === 0 || !ds.breakdowns.some(b => b.dimension === 'caste_category')) && (
                          <div style={{ marginTop: '8px', padding: '6px 10px', background: '#fffbeb', border: '1px solid #fef3c7', borderRadius: '4px', fontSize: '11px', color: '#92400e' }}>
                            ℹ️ Caste-wise beneficiary data is not available from the verified official source.
                          </div>
                        )}
                      </div>
                    ))
                  )}
                </div>
              )}

              {/* TAB 2: Import Dataset */}
              {activeTab === 'import' && (
                <form onSubmit={handleImportSubmit}>
                  <h5 style={{ marginTop: 0, marginBottom: '14px' }}>Import Official Government Dataset</h5>
                  
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '12px' }}>
                    <div>
                      <label style={{ fontSize: '12px', fontWeight: 'bold', display: 'block', marginBottom: '4px' }}>
                        Source Government Body / Dashboard *
                      </label>
                      <input
                        type="text"
                        required
                        className="form-control"
                        placeholder="e.g. Ministry of Agriculture, PM-KISAN Portal"
                        value={importForm.source_name}
                        onChange={(e) => setImportForm({ ...importForm, source_name: e.target.value })}
                      />
                    </div>
                    <div>
                      <label style={{ fontSize: '12px', fontWeight: 'bold', display: 'block', marginBottom: '4px' }}>
                        Official Source URL *
                      </label>
                      <input
                        type="url"
                        required
                        className="form-control"
                        placeholder="https://pmkisan.gov.in"
                        value={importForm.source_url}
                        onChange={(e) => setImportForm({ ...importForm, source_url: e.target.value })}
                      />
                    </div>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '12px', marginBottom: '12px' }}>
                    <div>
                      <label style={{ fontSize: '12px', fontWeight: 'bold', display: 'block', marginBottom: '4px' }}>
                        Official Report / Publication Document Title *
                      </label>
                      <input
                        type="text"
                        required
                        className="form-control"
                        placeholder="e.g. PM-KISAN National MIS Dashboard & 16th Installment Release Report"
                        value={importForm.report_title}
                        onChange={(e) => setImportForm({ ...importForm, report_title: e.target.value })}
                      />
                    </div>
                    <div>
                      <label style={{ fontSize: '12px', fontWeight: 'bold', display: 'block', marginBottom: '4px' }}>
                        Geographic Scope *
                      </label>
                      <select
                        className="form-control"
                        value={importForm.geographic_scope}
                        onChange={(e) => setImportForm({ ...importForm, geographic_scope: e.target.value })}
                      >
                        <option value="National">National (All India)</option>
                        <option value="State: Maharashtra">State: Maharashtra</option>
                        <option value="State: Gujarat">State: Gujarat</option>
                        <option value="State: Uttar Pradesh">State: Uttar Pradesh</option>
                      </select>
                    </div>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px', marginBottom: '12px' }}>
                    <div>
                      <label style={{ fontSize: '12px', fontWeight: 'bold', display: 'block', marginBottom: '4px' }}>
                        Reporting Period *
                      </label>
                      <input
                        type="text"
                        required
                        className="form-control"
                        placeholder="e.g. FY 2024-25"
                        value={importForm.reporting_period}
                        onChange={(e) => setImportForm({ ...importForm, reporting_period: e.target.value })}
                      />
                    </div>
                    <div>
                      <label style={{ fontSize: '12px', fontWeight: 'bold', display: 'block', marginBottom: '4px' }}>
                        Metric Type (Distinct Metric) *
                      </label>
                      <select
                        className="form-control"
                        value={importForm.metric_type}
                        onChange={(e) => setImportForm({ ...importForm, metric_type: e.target.value })}
                      >
                        <option value="unique_farmer_households">Unique Farmer Households (PM-KISAN)</option>
                        <option value="ayushman_cards_issued">Ayushman Cards Issued (PM-JAY)</option>
                        <option value="houses_sanctioned">Houses Sanctioned (PMAY-G)</option>
                        <option value="houses_completed">Houses Completed</option>
                        <option value="hospital_admissions">Hospital Admissions</option>
                        <option value="students_awarded_scholarship">Students Awarded Scholarship</option>
                        <option value="covered_families">Covered Families</option>
                        <option value="unique_beneficiaries">Unique Beneficiaries</option>
                      </select>
                    </div>
                    <div>
                      <label style={{ fontSize: '12px', fontWeight: 'bold', display: 'block', marginBottom: '4px' }}>
                        Total Metric Count *
                      </label>
                      <input
                        type="number"
                        required
                        className="form-control"
                        placeholder="e.g. 110000000"
                        value={importForm.total_beneficiaries}
                        onChange={(e) => setImportForm({ ...importForm, total_beneficiaries: e.target.value })}
                      />
                    </div>
                  </div>

                  <div style={{ marginBottom: '12px' }}>
                    <label style={{ fontSize: '12px', fontWeight: 'bold', display: 'block', marginBottom: '4px' }}>
                      Operational Metric Definition *
                    </label>
                    <input
                      type="text"
                      required
                      className="form-control"
                      placeholder="e.g. Total verified unique operational landholder farmer families receiving DBT assistance"
                      value={importForm.metric_definition}
                      onChange={(e) => setImportForm({ ...importForm, metric_definition: e.target.value })}
                    />
                  </div>

                  <div style={{ borderTop: '1px solid #e2e8f0', paddingTop: '12px', marginTop: '12px' }}>
                    <div style={{ fontSize: '12px', fontWeight: 'bold', color: '#475569', marginBottom: '4px' }}>
                      Verified Demographic / Geographic Breakdowns (Optional):
                    </div>
                    <div style={{ fontSize: '11px', color: '#64748b', marginBottom: '8px' }}>
                      ⚠️ Audit Mandate: Do not record synthetic or estimated distributions. Only input counts directly reported in the official document.
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '10px' }}>
                      <div>
                        <label style={{ fontSize: '11px', display: 'block' }}>Female Count</label>
                        <input
                          type="number"
                          className="form-control"
                          placeholder="e.g. 30000000"
                          value={importForm.female_count}
                          onChange={(e) => setImportForm({ ...importForm, female_count: e.target.value })}
                        />
                      </div>
                      <div>
                        <label style={{ fontSize: '11px', display: 'block' }}>Male Count</label>
                        <input
                          type="number"
                          className="form-control"
                          placeholder="e.g. 80000000"
                          value={importForm.male_count}
                          onChange={(e) => setImportForm({ ...importForm, male_count: e.target.value })}
                        />
                      </div>
                      <div>
                        <label style={{ fontSize: '11px', display: 'block' }}>State Name</label>
                        <input
                          type="text"
                          className="form-control"
                          placeholder="e.g. Uttar Pradesh"
                          value={importForm.state_breakdown_name}
                          onChange={(e) => setImportForm({ ...importForm, state_breakdown_name: e.target.value })}
                        />
                      </div>
                      <div>
                        <label style={{ fontSize: '11px', display: 'block' }}>State Beneficiary Count</label>
                        <input
                          type="number"
                          className="form-control"
                          placeholder="e.g. 26000000"
                          value={importForm.state_breakdown_count}
                          onChange={(e) => setImportForm({ ...importForm, state_breakdown_count: e.target.value })}
                        />
                      </div>
                    </div>
                  </div>

                  <div style={{ marginTop: '12px' }}>
                    <label style={{ fontSize: '12px', fontWeight: 'bold', display: 'block', marginBottom: '4px' }}>
                      Administrative Notes
                    </label>
                    <textarea
                      rows={2}
                      className="form-control"
                      placeholder="Methodology notes, gazette notification number, or data limits..."
                      value={importForm.notes}
                      onChange={(e) => setImportForm({ ...importForm, notes: e.target.value })}
                    />
                  </div>

                  <div style={{ marginTop: '16px', display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
                    <button type="button" className="btn-secondary" onClick={() => setActiveTab('analytics')}>
                      Cancel
                    </button>
                    <button type="submit" className="btn-primary" disabled={actionLoading}>
                      {actionLoading ? 'Importing...' : 'Save & Import Dataset'}
                    </button>
                  </div>
                </form>
              )}

              {/* TAB 3: Category Rules & Documents */}
              {activeTab === 'rules' && (
                <div>
                  <h5 style={{ marginTop: 0, marginBottom: '10px' }}>Category-Specific Eligibility Criteria ({categoryRules.length})</h5>
                  <div style={{ marginBottom: '20px' }}>
                    {categoryRules.map((r) => (
                      <div key={r.id} style={{
                        padding: '10px 12px',
                        border: '1px solid #e2e8f0',
                        borderRadius: '6px',
                        marginBottom: '8px',
                        background: '#f8fafc',
                      }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <div>
                            <span style={{
                              padding: '2px 6px',
                              borderRadius: '4px',
                              background: '#ede9fe',
                              color: '#6d28d9',
                              fontSize: '11px',
                              fontWeight: 'bold',
                              marginRight: '8px',
                            }}>
                              {r.category}
                            </span>
                            <strong style={{ fontSize: '13px' }}>{r.condition_name}</strong>
                          </div>
                          <span style={{ fontSize: '11px', color: '#64748b' }}>
                            {r.field} {r.operator} {JSON.stringify(r.expected_value)}
                          </span>
                        </div>
                        {r.special_conditions && (
                          <div style={{ fontSize: '11px', color: '#475569', marginTop: '4px' }}>
                            {r.special_conditions}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>

                  <h5 style={{ marginBottom: '10px' }}>Category Document Requirements ({categoryDocs.length})</h5>
                  <div>
                    {categoryDocs.map((d) => (
                      <div key={d.id} style={{
                        padding: '10px 12px',
                        border: '1px solid #e2e8f0',
                        borderRadius: '6px',
                        marginBottom: '8px',
                      }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <div>
                            <span style={{
                              padding: '2px 6px',
                              borderRadius: '4px',
                              background: '#f1f5f9',
                              color: '#334155',
                              fontSize: '11px',
                              fontWeight: 'bold',
                              marginRight: '8px',
                            }}>
                              {d.category}
                            </span>
                            <strong style={{ fontSize: '13px' }}>{d.document_name}</strong>
                          </div>
                          <span style={{
                            fontSize: '11px',
                            color: d.is_mandatory ? '#b91c1c' : '#15803d',
                            fontWeight: 'bold',
                          }}>
                            {d.is_mandatory ? 'Mandatory' : 'Optional'}
                          </span>
                        </div>
                        <div style={{ fontSize: '11px', color: '#64748b', marginTop: '2px' }}>
                          Authority: {d.issuing_authority} | Formats: {d.accepted_formats}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* TAB 4: Audit History */}
              {activeTab === 'audit' && (
                <div>
                  <h5 style={{ marginTop: 0, marginBottom: '12px' }}>Administrative Action Ledger</h5>
                  {auditLogs.length === 0 ? (
                    <div style={{ color: '#64748b', fontSize: '13px' }}>No audit entries recorded yet.</div>
                  ) : (
                    <div style={{ border: '1px solid #e2e8f0', borderRadius: '6px', overflow: 'hidden' }}>
                      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
                        <thead>
                          <tr style={{ background: '#f8fafc', borderBottom: '1px solid #e2e8f0', textAlign: 'left' }}>
                            <th style={{ padding: '8px 12px' }}>Timestamp</th>
                            <th style={{ padding: '8px 12px' }}>Action</th>
                            <th style={{ padding: '8px 12px' }}>Admin</th>
                            <th style={{ padding: '8px 12px' }}>Details</th>
                          </tr>
                        </thead>
                        <tbody>
                          {auditLogs.map((log) => (
                            <tr key={log.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                              <td style={{ padding: '8px 12px', color: '#64748b' }}>
                                {new Date(log.created_at).toLocaleString()}
                              </td>
                              <td style={{ padding: '8px 12px', fontWeight: 'bold' }}>
                                <span style={{
                                  padding: '2px 6px',
                                  borderRadius: '4px',
                                  background: log.action === 'published' ? '#bbf7d0' : '#e2e8f0',
                                  color: log.action === 'published' ? '#166534' : '#334155',
                                }}>
                                  {log.action.toUpperCase()}
                                </span>
                              </td>
                              <td style={{ padding: '8px 12px' }}>{log.admin_id ? log.admin_id.slice(0, 8) : 'System Seed'}</td>
                              <td style={{ padding: '8px 12px', color: '#475569' }}>
                                {JSON.stringify(log.details)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>

        <div className="modal-footer">
          <button className="btn-secondary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

