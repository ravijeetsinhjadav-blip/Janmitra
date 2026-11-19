import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';

export default function LoginView() {
  const { loginWithEmailPassword, loading, error, setError } = useAuth();
  
  // Email + Password Flow State
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleCredentialsLogin = async (e) => {
    e.preventDefault();
    if (!email.trim() || !password) {
      setError('Please provide administrator email and password.');
      return;
    }
    await loginWithEmailPassword(email.trim(), password);
  };

  return (
    <div className="login-screen">
      <div className="login-card">
        <div className="login-header">
          <div className="login-emblem">🏛️</div>
          <h2>JanMitra Assist</h2>
          <p className="login-subtitle">Administrative Management Portal</p>
        </div>

        {error && (
          <div className="login-alert error">
            <span>⚠️ {error}</span>
          </div>
        )}

        <form onSubmit={handleCredentialsLogin} className="login-form">
          <div className="form-group">
            <label>Administrator Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="admin@janmitra.internal"
              required
            />
          </div>
          <div className="form-group">
            <label>Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••••••"
              required
            />
          </div>
          <button
            type="submit"
            className="login-submit-btn"
            disabled={loading}
          >
            {loading ? 'Authenticating...' : 'Sign In as Administrator'}
          </button>
          <div className="login-hint">
            <span>🔐 Access strictly restricted to authorized administrators. OTP is disabled.</span>
          </div>
        </form>
      </div>
    </div>
  );
}
