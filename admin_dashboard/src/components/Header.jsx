import React from 'react';
import { useAuth } from '../context/AuthContext';

export default function Header() {
  const { adminUser, logout } = useAuth();

  return (
    <header className="dashboard-header">
      <div className="header-left">
        <h1>JanMitra Assist Admin Console</h1>
      </div>
      <div className="header-right">
        <div className="header-status">
          <span className="status-dot"></span>
          <span>FastAPI Online (Port 8000)</span>
        </div>
        {adminUser && (
          <div className="admin-profile-badge">
            <span className="admin-avatar">👤</span>
            <div className="admin-info">
              <span className="admin-role">System Administrator</span>
              <span className="admin-phone">{adminUser.mobileNumber || 'Admin Session'}</span>
            </div>
            <button className="btn-logout" onClick={logout} title="Sign Out">
              🚪 Logout
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
