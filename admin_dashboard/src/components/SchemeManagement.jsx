import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import SchemeAnalyticsModal from './SchemeAnalyticsModal';

export default function SchemeManagement() {
  const { token, apiBase } = useAuth();
  const [schemes, setSchemes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [activeFilter, setActiveFilter] = useState('');

  // Pagination State
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);

  // Modal States
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [selectedScheme, setSelectedScheme] = useState(null);
  const [analyticsScheme, setAnalyticsScheme] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // New Scheme Form
  const [newScheme, setNewScheme] = useState({
    scheme_name: '',
    category: 'Agriculture',
    department: '',
    description: '',
    short_description: '',
    state_applicability: 'All India',
    eligibility_summary: '',
    official_source_url: '',
    official_application_url: '',
    benefits: '',
    required_documents: 'Income Certificate, Bank Passbook, Domicile Certificate',
  });

  const categories = [
    'Agriculture',
    'Healthcare',
    'Education',
    'Housing',
    'Financial Inclusion',
    'Social Welfare',
    'Women & Child Development',
  ];

  const fetchSchemes = async (targetPage = page, targetPageSize = pageSize) => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      params.append('page', String(targetPage));
      params.append('page_size', String(targetPageSize));
      if (searchQuery.trim()) params.append('query', searchQuery.trim());
      if (categoryFilter) params.append('category', categoryFilter);
      if (activeFilter !== '') params.append('is_active', activeFilter);

      const res = await fetch(`${apiBase}/admin/schemes?${params.toString()}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error(`HTTP Error ${res.status}: Failed to fetch schemes`);
      const data = await res.json();
      setSchemes(data.schemes || []);
      setTotalCount(data.total || 0);
      setTotalPages(data.total_pages || 1);
      setPage(data.page || targetPage);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setPage(1);
    fetchSchemes(1, pageSize);
  }, [categoryFilter, activeFilter]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setPage(1);
    fetchSchemes(1, pageSize);
  };

  const handlePageChange = (newPage) => {
    if (newPage >= 1 && newPage <= totalPages && newPage !== page) {
      setPage(newPage);
      fetchSchemes(newPage, pageSize);
    }
  };

  const handleToggleActive = async (scheme) => {
    const updatedStatus = !scheme.is_active;
    try {
      const res = await fetch(`${apiBase}/admin/schemes/${scheme.id}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ is_active: updatedStatus }),
      });
      if (!res.ok) throw new Error('Failed to update scheme status');
      setSchemes((prev) =>
        prev.map((s) => (s.id === scheme.id ? { ...s, is_active: updatedStatus } : s))
      );
    } catch (err) {
      alert(`Error updating scheme: ${err.message}`);
    }
  };

  const handleCreateScheme = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      const payload = {
        scheme_name: newScheme.scheme_name.trim(),
        category: newScheme.category,
        department: newScheme.department.trim(),
        description: newScheme.description.trim(),
        short_description: newScheme.short_description.trim() || newScheme.description.trim().slice(0, 180),
        state_applicability: newScheme.state_applicability.trim() || 'All India',
        eligibility_summary: newScheme.eligibility_summary.trim(),
        official_source_url: newScheme.official_source_url.trim(),
        official_application_url: newScheme.official_application_url.trim(),
        benefits: newScheme.benefits
          ? newScheme.benefits.split(',').map((b) => b.trim()).filter(Boolean)
          : [],
        required_documents: newScheme.required_documents
          ? newScheme.required_documents.split(',').map((d) => d.trim()).filter(Boolean)
          : [],
        eligibility_criteria: [],
        is_demo_data: false,
      };

      const res = await fetch(`${apiBase}/admin/schemes`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Failed to create government scheme');
      }

      setIsCreateOpen(false);
      setNewScheme({
        scheme_name: '',
        category: 'Agriculture',
        department: '',
        description: '',
        short_description: '',
        state_applicability: 'All India',
        eligibility_summary: '',
        official_source_url: '',
        official_application_url: '',
        benefits: '',
        required_documents: 'Voter ID / Photo ID, Bank Passbook',
      });
      fetchSchemes();
    } catch (err) {
      alert(`Creation Error: ${err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="schemes-management-container">
      <div className="section-header">
        <div>
          <h3>Government Schemes Repository</h3>
          <p>
            Publish, edit, and configure central & state welfare schemes, nodal departments, and official portal URLs.
          </p>
        </div>
        <button className="btn-primary" onClick={() => setIsCreateOpen(true)}>
          ➕ Add Government Scheme
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="filter-bar">
        <form onSubmit={handleSearchSubmit} className="search-form">
          <input
            type="text"
            placeholder="Search by scheme name or ministry..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          <button type="submit" className="btn-secondary">Search</button>
        </form>

        <div className="filters-group">
          <select value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)}>
            <option value="">All Categories</option>
            {categories.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>

          <select value={activeFilter} onChange={(e) => setActiveFilter(e.target.value)}>
            <option value="">All Statuses</option>
            <option value="true">Active Only</option>
            <option value="false">Inactive Only</option>
          </select>
        </div>
      </div>

      {error && <div className="alert-box error">⚠️ {error}</div>}

      {/* Schemes Data Table */}
      <div className="table-responsive">
        <table className="data-table">
          <thead>
            <tr>
              <th>Scheme Title</th>
              <th>Category</th>
              <th>Department / Ministry</th>
              <th>State Scope</th>
              <th>Official Portal</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={7} className="text-center py-4">Loading schemes from repository...</td>
              </tr>
            ) : schemes.length === 0 ? (
              <tr>
                <td colSpan={7} className="text-center py-4">No government schemes matched the criteria.</td>
              </tr>
            ) : (
              schemes.map((s) => (
                <tr key={s.id}>
                  <td>
                    <strong>{s.scheme_name}</strong>
                    {s.is_demo_data && <span className="badge-demo">Demo</span>}
                  </td>
                  <td><span className="badge-category">{s.category}</span></td>
                  <td>{s.department}</td>
                  <td>{s.state_applicability}</td>
                  <td>
                    <a
                      href={s.official_application_url || s.official_source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="portal-link"
                    >
                      🔗 Official Portal
                    </a>
                  </td>
                  <td>
                    <span className={`status-pill ${s.is_active ? 'active' : 'inactive'}`}>
                      {s.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td>
                    <div className="actions-cell">
                      <button
                        className="btn-action"
                        onClick={() => setSelectedScheme(s)}
                        title="View Details"
                      >
                        👁️
                      </button>
                      <button
                        className="btn-action"
                        onClick={() => setAnalyticsScheme(s)}
                        title="Beneficiary Analytics & Intelligence"
                        style={{ background: '#ede9fe', color: '#6d28d9' }}
                      >
                        📊
                      </button>
                      <button
                        className={`btn-action ${s.is_active ? 'deactivate' : 'activate'}`}
                        onClick={() => handleToggleActive(s)}
                        title={s.is_active ? 'Deactivate Scheme' : 'Activate Scheme'}
                      >
                        {s.is_active ? '⏸️' : '▶️'}
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Controls */}
      <div className="pagination-container" aria-label="Schemes Pagination">
        <div className="pagination-info">
          Showing {totalCount === 0 ? 0 : (page - 1) * pageSize + 1}–{Math.min(page * pageSize, totalCount)} of {totalCount} schemes (Page {page} of {totalPages})
        </div>
        <div className="pagination-actions">
          <button
            type="button"
            className="btn-page"
            disabled={page <= 1 || loading}
            onClick={() => handlePageChange(page - 1)}
            aria-label="Previous Page"
          >
            ← Previous
          </button>
          
          <div className="page-numbers">
            {Array.from({ length: totalPages }, (_, i) => i + 1)
              .filter(p => p === 1 || p === totalPages || Math.abs(p - page) <= 1)
              .reduce((acc, p, idx, arr) => {
                if (idx > 0 && p - arr[idx - 1] > 1) {
                  acc.push(<span key={`ellipsis-${p}`} className="page-ellipsis">…</span>);
                }
                acc.push(
                  <button
                    key={p}
                    type="button"
                    className={`btn-page-number ${p === page ? 'active' : ''}`}
                    onClick={() => handlePageChange(p)}
                    aria-current={p === page ? 'page' : undefined}
                  >
                    {p}
                  </button>
                );
                return acc;
              }, [])}
          </div>

          <button
            type="button"
            className="btn-page"
            disabled={page >= totalPages || loading}
            onClick={() => handlePageChange(page + 1)}
            aria-label="Next Page"
          >
            Next →
          </button>
        </div>
      </div>

      {/* Modal: Create Scheme */}
      {isCreateOpen && (
        <div className="modal-backdrop">
          <div className="modal-dialog">
            <div className="modal-header">
              <h4>Add New Government Scheme</h4>
              <button className="btn-close" onClick={() => setIsCreateOpen(false)}>✕</button>
            </div>
            <form onSubmit={handleCreateScheme}>
              <div className="modal-body">
                <div className="form-group">
                  <label>Scheme Official Name *</label>
                  <input
                    type="text"
                    required
                    value={newScheme.scheme_name}
                    onChange={(e) => setNewScheme({ ...newScheme, scheme_name: e.target.value })}
                    placeholder="e.g. Pradhan Mantri Awas Yojana"
                  />
                </div>

                <div className="form-row">
                  <div className="form-group flex-1">
                    <label>Category *</label>
                    <select
                      value={newScheme.category}
                      onChange={(e) => setNewScheme({ ...newScheme, category: e.target.value })}
                    >
                      {categories.map((c) => (
                        <option key={c} value={c}>{c}</option>
                      ))}
                    </select>
                  </div>
                  <div className="form-group flex-1">
                    <label>State Applicability</label>
                    <input
                      type="text"
                      value={newScheme.state_applicability}
                      onChange={(e) => setNewScheme({ ...newScheme, state_applicability: e.target.value })}
                      placeholder="All India or State name"
                    />
                  </div>
                </div>

                <div className="form-group">
                  <label>Nodal Ministry / Department *</label>
                  <input
                    type="text"
                    required
                    value={newScheme.department}
                    onChange={(e) => setNewScheme({ ...newScheme, department: e.target.value })}
                    placeholder="e.g. Ministry of Housing and Urban Affairs"
                  />
                </div>

                <div className="form-group">
                  <label>Detailed Scheme Description *</label>
                  <textarea
                    rows={3}
                    required
                    value={newScheme.description}
                    onChange={(e) => setNewScheme({ ...newScheme, description: e.target.value })}
                    placeholder="Complete objectives, financial assistance structure, and coverage..."
                  />
                </div>

                <div className="form-group">
                  <label>Eligibility Summary *</label>
                  <textarea
                    rows={2}
                    required
                    value={newScheme.eligibility_summary}
                    onChange={(e) => setNewScheme({ ...newScheme, eligibility_summary: e.target.value })}
                    placeholder="e.g. Economically weaker sections (EWS) with annual income below 3 lakh..."
                  />
                </div>

                <div className="form-row">
                  <div className="form-group flex-1">
                    <label>Official Information Source URL *</label>
                    <input
                      type="url"
                      required
                      value={newScheme.official_source_url}
                      onChange={(e) => setNewScheme({ ...newScheme, official_source_url: e.target.value })}
                      placeholder="https://pmaymis.gov.in"
                    />
                  </div>
                  <div className="form-group flex-1">
                    <label>Official Application Submission URL *</label>
                    <input
                      type="url"
                      required
                      value={newScheme.official_application_url}
                      onChange={(e) => setNewScheme({ ...newScheme, official_application_url: e.target.value })}
                      placeholder="https://pmaymis.gov.in/Open/Check_Aadhar_Existence.aspx"
                    />
                  </div>
                </div>

                <div className="form-group">
                  <label>Required Documents (Comma-separated)</label>
                  <input
                    type="text"
                    value={newScheme.required_documents}
                    onChange={(e) => setNewScheme({ ...newScheme, required_documents: e.target.value })}
                    placeholder="Voter ID, Income Certificate, Bank Passbook"
                  />
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn-secondary" onClick={() => setIsCreateOpen(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn-primary" disabled={isSubmitting}>
                  {isSubmitting ? 'Registering Scheme...' : 'Save Scheme'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: View Scheme Details */}
      {selectedScheme && (
        <div className="modal-backdrop">
          <div className="modal-dialog">
            <div className="modal-header">
              <h4>{selectedScheme.scheme_name}</h4>
              <button className="btn-close" onClick={() => setSelectedScheme(null)}>✕</button>
            </div>
            <div className="modal-body">
              <div className="detail-meta">
                <span className="badge-category">{selectedScheme.category}</span>
                <span className="meta-text">{selectedScheme.department}</span>
                <span className="meta-text">📍 {selectedScheme.state_applicability}</span>
              </div>
              <p className="mt-3"><strong>Description:</strong> {selectedScheme.description}</p>
              <div className="mt-2">
                <strong>Source Verification:</strong>{' '}
                <span className="badge-tag success">{selectedScheme.source_freshness_status}</span>
              </div>
              <div className="mt-3">
                <strong>Official Application Portal:</strong><br />
                <a
                  href={selectedScheme.official_application_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="portal-link"
                >
                  {selectedScheme.official_application_url}
                </a>
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn-secondary" onClick={() => setSelectedScheme(null)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Beneficiary Analytics & Intelligence */}
      {analyticsScheme && (
        <SchemeAnalyticsModal
          scheme={analyticsScheme}
          onClose={() => setAnalyticsScheme(null)}
        />
      )}
    </div>
  );
}

