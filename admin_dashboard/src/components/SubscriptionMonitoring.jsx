import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';

export default function SubscriptionMonitoring() {
  const { token, apiBase } = useAuth();

  // Metrics
  const [stats, setStats] = useState(null);
  const [activeSubTab, setActiveSubTab] = useState('subscriptions'); // 'subscriptions' or 'payments'

  // Subscriptions Table State
  const [subscriptions, setSubscriptions] = useState([]);
  const [subTotal, setSubTotal] = useState(0);
  const [subLoading, setSubLoading] = useState(true);
  const [subPlanFilter, setSubPlanFilter] = useState('');
  const [subStatusFilter, setSubStatusFilter] = useState('');
  const [subSearch, setSubSearch] = useState('');
  const [subPage, setSubPage] = useState(1);
  const [subPageSize] = useState(25);
  const [subTotalPages, setSubTotalPages] = useState(1);

  // Payments Table State
  const [payments, setPayments] = useState([]);
  const [payTotal, setPayTotal] = useState(0);
  const [payLoading, setPayLoading] = useState(true);
  const [payStatusFilter, setPayStatusFilter] = useState('');
  const [paySearch, setPaySearch] = useState('');
  const [payPage, setPayPage] = useState(1);
  const [payPageSize] = useState(25);
  const [payTotalPages, setPayTotalPages] = useState(1);

  const [error, setError] = useState(null);

  // Fetch Stats
  const fetchStats = async () => {
    try {
      const res = await fetch(`${apiBase}/admin/stats`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch (err) {
      console.error('Failed to fetch stats:', err);
    }
  };

  // Fetch Subscriptions
  const fetchSubscriptions = async (targetPage = subPage, targetPageSize = subPageSize) => {
    setSubLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      params.append('page', String(targetPage));
      params.append('page_size', String(targetPageSize));
      if (subPlanFilter && subPlanFilter !== 'All') params.append('plan_type', subPlanFilter);
      if (subStatusFilter && subStatusFilter !== 'All') params.append('status', subStatusFilter);
      if (subSearch.trim()) params.append('query', subSearch.trim());

      const res = await fetch(`${apiBase}/admin/subscriptions?${params.toString()}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error(`HTTP Error ${res.status}: Failed to fetch subscriptions`);
      const data = await res.json();
      setSubscriptions(data.items || []);
      setSubTotal(data.total || 0);
      setSubTotalPages(data.total_pages || 1);
      setSubPage(data.page || targetPage);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubLoading(false);
    }
  };

  // Fetch Payments
  const fetchPayments = async (targetPage = payPage, targetPageSize = payPageSize) => {
    setPayLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      params.append('page', String(targetPage));
      params.append('page_size', String(targetPageSize));
      if (payStatusFilter && payStatusFilter !== 'All') params.append('status', payStatusFilter);
      if (paySearch.trim()) params.append('query', paySearch.trim());

      const res = await fetch(`${apiBase}/admin/payments?${params.toString()}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error(`HTTP Error ${res.status}: Failed to fetch payments`);
      const data = await res.json();
      setPayments(data.items || []);
      setPayTotal(data.total || 0);
      setPayTotalPages(data.total_pages || 1);
      setPayPage(data.page || targetPage);
    } catch (err) {
      setError(err.message);
    } finally {
      setPayLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  useEffect(() => {
    setSubPage(1);
    fetchSubscriptions(1, subPageSize);
  }, [subPlanFilter, subStatusFilter, subSearch]);

  useEffect(() => {
    setPayPage(1);
    fetchPayments(1, payPageSize);
  }, [payStatusFilter, paySearch]);

  useEffect(() => {
    if (activeSubTab === 'subscriptions') {
      fetchSubscriptions(subPage, subPageSize);
    } else {
      fetchPayments(payPage, payPageSize);
    }
  }, [activeSubTab]);

  const handleSubPageChange = (newPage) => {
    if (newPage >= 1 && newPage <= subTotalPages && newPage !== subPage) {
      setSubPage(newPage);
      fetchSubscriptions(newPage, subPageSize);
    }
  };

  const handlePayPageChange = (newPage) => {
    if (newPage >= 1 && newPage <= payTotalPages && newPage !== payPage) {
      setPayPage(newPage);
      fetchPayments(newPage, payPageSize);
    }
  };

  const getStatusBadge = (status) => {
    const s = (status || '').toLowerCase();
    let badgeClass = 'badge-secondary';
    if (s === 'active' || s === 'captured') badgeClass = 'badge-success';
    else if (s === 'expired' || s === 'failed') badgeClass = 'badge-danger';
    else if (s === 'cancelled' || s === 'refunded') badgeClass = 'badge-warning';
    else if (s === 'created') badgeClass = 'badge-info';

    return <span className={`status-badge ${badgeClass}`}>{status.toUpperCase()}</span>;
  };

  const getPlanBadge = (plan) => {
    const p = (plan || '').toLowerCase();
    return (
      <span className={`status-badge ${p === 'premium' ? 'badge-primary' : 'badge-secondary'}`}>
        {p === 'premium' ? '★ PREMIUM' : 'FREE'}
      </span>
    );
  };

  return (
    <div className="subscription-monitoring-container">
      {/* Security & Financial Notice */}
      <div className="boundary-banner">
        <div className="boundary-icon">🔒</div>
        <div className="boundary-content">
          <strong>Security & Financial Privacy Notice:</strong> All online payment processing is managed securely by Razorpay.
          Secret API keys and sensitive customer financial credentials (card numbers, CVVs, UPI PINs) are never stored or accessible
          in the administration portal. Only verified transaction statuses and masked references are logged for compliance.
        </div>
      </div>

      {/* Metrics Row */}
      <div className="metrics-grid">
        <div className="metric-card">
          <div className="metric-card-title">Free Plan Citizens</div>
          <div className="metric-card-value">{stats ? stats.total_free_users : '—'}</div>
          <div className="metric-card-footer">3 docs & 5 guidance sessions / mo</div>
        </div>
        <div className="metric-card">
          <div className="metric-card-title">Active Premium Subscribers</div>
          <div className="metric-card-value text-success">{stats ? stats.total_premium_users : '—'}</div>
          <div className="metric-card-footer">₹99/mo or ₹799/yr subscribers</div>
        </div>
        <div className="metric-card">
          <div className="metric-card-title">Active Subscriptions</div>
          <div className="metric-card-value">{stats ? stats.active_subscriptions : '—'}</div>
          <div className="metric-card-footer">Currently entitled subscriptions</div>
        </div>
        <div className="metric-card">
          <div className="metric-card-title">Expired / Cancelled</div>
          <div className="metric-card-value text-danger">
            {stats ? (stats.expired_subscriptions || 0) + (stats.cancelled_subscriptions || 0) : '—'}
          </div>
          <div className="metric-card-footer">Automatically reverted to Free tier</div>
        </div>
        <div className="metric-card">
          <div className="metric-card-title">Total Revenue Captured</div>
          <div className="metric-card-value text-primary">
            ₹{stats ? Number(stats.total_revenue_inr || 0).toLocaleString('en-IN') : '0'}
          </div>
          <div className="metric-card-footer">{stats ? stats.total_payments_captured : 0} successful transactions</div>
        </div>
      </div>

      {/* View Switcher Tabs */}
      <div className="sub-nav-tabs" style={{ display: 'flex', gap: '1rem', marginTop: '1.5rem', marginBottom: '1rem' }}>
        <button
          className={`tab-btn ${activeSubTab === 'subscriptions' ? 'tab-btn-active' : ''}`}
          onClick={() => setActiveSubTab('subscriptions')}
          style={{
            padding: '0.6rem 1.2rem',
            borderRadius: '6px',
            border: 'none',
            cursor: 'pointer',
            fontWeight: '600',
            backgroundColor: activeSubTab === 'subscriptions' ? '#0F766E' : '#e2e8f0',
            color: activeSubTab === 'subscriptions' ? '#ffffff' : '#334155',
          }}
        >
          📋 Citizen Subscriptions ({subTotal})
        </button>
        <button
          className={`tab-btn ${activeSubTab === 'payments' ? 'tab-btn-active' : ''}`}
          onClick={() => setActiveSubTab('payments')}
          style={{
            padding: '0.6rem 1.2rem',
            borderRadius: '6px',
            border: 'none',
            cursor: 'pointer',
            fontWeight: '600',
            backgroundColor: activeSubTab === 'payments' ? '#0F766E' : '#e2e8f0',
            color: activeSubTab === 'payments' ? '#ffffff' : '#334155',
          }}
        >
          💳 Razorpay Transactions ({payTotal})
        </button>
      </div>

      {error && <div className="error-alert" style={{ color: '#b91c1c', marginBottom: '1rem' }}>⚠️ {error}</div>}

      {/* Section 1: Citizen Subscriptions */}
      {activeSubTab === 'subscriptions' && (
        <div className="table-card">
          <div className="table-header-controls" style={{ display: 'flex', gap: '1rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
            <input
              type="text"
              placeholder="Search by name or mobile..."
              value={subSearch}
              onChange={(e) => setSubSearch(e.target.value)}
              className="search-input"
              style={{ padding: '0.5rem', borderRadius: '4px', border: '1px solid #cbd5e1', minWidth: '220px' }}
            />
            <select
              value={subPlanFilter}
              onChange={(e) => setSubPlanFilter(e.target.value)}
              className="filter-select"
              style={{ padding: '0.5rem', borderRadius: '4px', border: '1px solid #cbd5e1' }}
            >
              <option value="">All Plan Tiers</option>
              <option value="free">Free Plan</option>
              <option value="premium">Premium Plan</option>
            </select>
            <select
              value={subStatusFilter}
              onChange={(e) => setSubStatusFilter(e.target.value)}
              className="filter-select"
              style={{ padding: '0.5rem', borderRadius: '4px', border: '1px solid #cbd5e1' }}
            >
              <option value="">All Statuses</option>
              <option value="active">Active</option>
              <option value="expired">Expired</option>
              <option value="cancelled">Cancelled</option>
            </select>
            <button
              onClick={fetchSubscriptions}
              style={{ padding: '0.5rem 1rem', borderRadius: '4px', border: 'none', background: '#0F766E', color: 'white', cursor: 'pointer' }}
            >
              Refresh
            </button>
          </div>

          {subLoading ? (
            <div className="loading-state">Loading subscriptions...</div>
          ) : subscriptions.length === 0 ? (
            <div className="empty-state">No subscriptions found matching the filter criteria.</div>
          ) : (
            <div className="table-responsive">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>Citizen</th>
                    <th>Mobile</th>
                    <th>Plan Tier</th>
                    <th>Billing Cycle</th>
                    <th>Status</th>
                    <th>Started</th>
                    <th>Expiry / Days Left</th>
                  </tr>
                </thead>
                <tbody>
                  {subscriptions.map((sub) => (
                    <tr key={sub.id}>
                      <td style={{ fontWeight: '600' }}>{sub.citizen_name || 'Citizen'}</td>
                      <td>+91 {sub.mobile_number}</td>
                      <td>{getPlanBadge(sub.plan_type)}</td>
                      <td>{sub.billing_cycle ? sub.billing_cycle.toUpperCase() : 'Permanent'}</td>
                      <td>{getStatusBadge(sub.status)}</td>
                      <td>{new Date(sub.start_date).toLocaleDateString()}</td>
                      <td>
                        {sub.end_date
                          ? `${new Date(sub.end_date).toLocaleDateString()} (${sub.days_remaining ?? 0} days)`
                          : 'Never (Free)'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Subscriptions Pagination Controls */}
          <div className="pagination-container" aria-label="Subscriptions Pagination">
            <div className="pagination-info">
              Showing {subTotal === 0 ? 0 : (subPage - 1) * subPageSize + 1}–{Math.min(subPage * subPageSize, subTotal)} of {subTotal} subscriptions (Page {subPage} of {subTotalPages})
            </div>
            <div className="pagination-actions">
              <button
                type="button"
                className="btn-page"
                disabled={subPage <= 1 || subLoading}
                onClick={() => handleSubPageChange(subPage - 1)}
                aria-label="Previous Page"
              >
                ← Previous
              </button>
              
              <div className="page-numbers">
                {Array.from({ length: subTotalPages }, (_, i) => i + 1)
                  .filter(p => p === 1 || p === subTotalPages || Math.abs(p - subPage) <= 1)
                  .reduce((acc, p, idx, arr) => {
                    if (idx > 0 && p - arr[idx - 1] > 1) {
                      acc.push(<span key={`ellipsis-${p}`} className="page-ellipsis">…</span>);
                    }
                    acc.push(
                      <button
                        key={p}
                        type="button"
                        className={`btn-page-number ${p === subPage ? 'active' : ''}`}
                        onClick={() => handleSubPageChange(p)}
                        aria-current={p === subPage ? 'page' : undefined}
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
                disabled={subPage >= subTotalPages || subLoading}
                onClick={() => handleSubPageChange(subPage + 1)}
                aria-label="Next Page"
              >
                Next →
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Section 2: Payment Transactions */}
      {activeSubTab === 'payments' && (
        <div className="table-card">
          <div className="table-header-controls" style={{ display: 'flex', gap: '1rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
            <input
              type="text"
              placeholder="Search by Order ID, Payment ID, or Mobile..."
              value={paySearch}
              onChange={(e) => setPaySearch(e.target.value)}
              className="search-input"
              style={{ padding: '0.5rem', borderRadius: '4px', border: '1px solid #cbd5e1', minWidth: '260px' }}
            />
            <select
              value={payStatusFilter}
              onChange={(e) => setPayStatusFilter(e.target.value)}
              className="filter-select"
              style={{ padding: '0.5rem', borderRadius: '4px', border: '1px solid #cbd5e1' }}
            >
              <option value="">All Payment Statuses</option>
              <option value="captured">Captured (Success)</option>
              <option value="created">Created (Pending)</option>
              <option value="failed">Failed</option>
              <option value="refunded">Refunded</option>
            </select>
            <button
              onClick={fetchPayments}
              style={{ padding: '0.5rem 1rem', borderRadius: '4px', border: 'none', background: '#0F766E', color: 'white', cursor: 'pointer' }}
            >
              Refresh
            </button>
          </div>

          {payLoading ? (
            <div className="loading-state">Loading transactions...</div>
          ) : payments.length === 0 ? (
            <div className="empty-state">No payment transactions found.</div>
          ) : (
            <div className="table-responsive">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>Razorpay Order ID</th>
                    <th>Razorpay Payment ID</th>
                    <th>Citizen</th>
                    <th>Amount</th>
                    <th>Plan & Cycle</th>
                    <th>Method</th>
                    <th>Status</th>
                    <th>Date & Time</th>
                  </tr>
                </thead>
                <tbody>
                  {payments.map((p) => (
                    <tr key={p.id}>
                      <td style={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>{p.razorpay_order_id}</td>
                      <td style={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>{p.razorpay_payment_id || '—'}</td>
                      <td>
                        <div style={{ fontWeight: '600' }}>{p.citizen_name || 'Citizen'}</div>
                        <div style={{ fontSize: '0.8rem', color: '#64748b' }}>+91 {p.mobile_number}</div>
                      </td>
                      <td style={{ fontWeight: 'bold', color: '#0F766E' }}>₹{p.amount.toFixed(2)}</td>
                      <td>
                        {p.plan_type.toUpperCase()} ({p.billing_cycle})
                      </td>
                      <td>
                        <span style={{ textTransform: 'uppercase', fontSize: '0.8rem', background: '#f1f5f9', padding: '2px 6px', borderRadius: '4px' }}>
                          {p.payment_method || 'UPI/Card'}
                        </span>
                      </td>
                      <td>{getStatusBadge(p.payment_status)}</td>
                      <td>{new Date(p.created_at).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Payments Pagination Controls */}
          <div className="pagination-container" aria-label="Payments Pagination">
            <div className="pagination-info">
              Showing {payTotal === 0 ? 0 : (payPage - 1) * payPageSize + 1}–{Math.min(payPage * payPageSize, payTotal)} of {payTotal} transactions (Page {payPage} of {payTotalPages})
            </div>
            <div className="pagination-actions">
              <button
                type="button"
                className="btn-page"
                disabled={payPage <= 1 || payLoading}
                onClick={() => handlePayPageChange(payPage - 1)}
                aria-label="Previous Page"
              >
                ← Previous
              </button>
              
              <div className="page-numbers">
                {Array.from({ length: payTotalPages }, (_, i) => i + 1)
                  .filter(p => p === 1 || p === payTotalPages || Math.abs(p - payPage) <= 1)
                  .reduce((acc, p, idx, arr) => {
                    if (idx > 0 && p - arr[idx - 1] > 1) {
                      acc.push(<span key={`ellipsis-${p}`} className="page-ellipsis">…</span>);
                    }
                    acc.push(
                      <button
                        key={p}
                        type="button"
                        className={`btn-page-number ${p === payPage ? 'active' : ''}`}
                        onClick={() => handlePayPageChange(p)}
                        aria-current={p === payPage ? 'page' : undefined}
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
                disabled={payPage >= payTotalPages || payLoading}
                onClick={() => handlePayPageChange(payPage + 1)}
                aria-label="Next Page"
              >
                Next →
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

