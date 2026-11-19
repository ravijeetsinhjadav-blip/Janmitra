import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

const AuthContext = createContext(null);

const rawApiBase = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';
const API_BASE = rawApiBase.endsWith('/api/v1') ? rawApiBase : `${rawApiBase.replace(/\/+$/, '')}/api/v1`;

function getCookie(name) {
  const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
  return match ? decodeURIComponent(match[2]) : null;
}

export function AuthProvider({ children }) {
  // Sensitive tokens are kept purely in memory, NEVER in localStorage
  const [token, setToken] = useState(null);
  const [csrfToken, setCsrfToken] = useState(() => getCookie('csrf_token_cookie'));
  const [adminUser, setAdminUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Restore authenticated session on mount using HttpOnly cookies
  const verifySession = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/auth/me`, {
        method: 'GET',
        credentials: 'include',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });

      if (res.ok) {
        const user = await res.json();
        if (user.role === 'admin') {
          setAdminUser({
            userId: user.id,
            email: user.email,
            role: user.role,
          });
          setCsrfToken(getCookie('csrf_token_cookie'));
          return true;
        }
      }

      // If /auth/me failed, try silent refresh via HttpOnly refresh cookie
      const existingCsrf = getCookie('csrf_token_cookie');
      const refreshRes = await fetch(`${API_BASE}/auth/refresh`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          ...(existingCsrf ? { 'X-CSRF-Token': existingCsrf } : {}),
        },
        body: JSON.stringify({}),
      });

      if (refreshRes.ok) {
        const refreshData = await refreshRes.json();
        if (refreshData.role === 'admin') {
          setToken(refreshData.access_token);
          setCsrfToken(refreshData.csrf_token || getCookie('csrf_token_cookie'));
          setAdminUser({
            userId: refreshData.user_id,
            email: refreshData.email,
            role: refreshData.role,
          });
          return true;
        }
      }

      // Session expired or not present
      setToken(null);
      setAdminUser(null);
      return false;
    } catch (_) {
      setToken(null);
      setAdminUser(null);
      return false;
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    // Clean up any legacy tokens from localStorage to eliminate XSS vectors
    try {
      localStorage.removeItem('janmitra_admin_token');
      localStorage.removeItem('janmitra_admin_user');
    } catch (_) {}

    verifySession();
  }, []);

  const loginWithEmailPassword = async (email, password) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim().toLowerCase(), password }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Authentication failed. Please verify credentials.');
      }
      if (data.role !== 'admin') {
        throw new Error('Access denied: Citizen accounts cannot access the Administration Console.');
      }

      // Set session in memory and HttpOnly cookies on response
      setToken(data.access_token);
      setCsrfToken(data.csrf_token || getCookie('csrf_token_cookie'));
      const userObj = {
        userId: data.user_id,
        email: data.email || email,
        role: data.role,
      };
      setAdminUser(userObj);
      return { success: true };
    } catch (err) {
      setError(err.message);
      return { success: false, error: err.message };
    } finally {
      setLoading(false);
    }
  };

  const loginWithDirectToken = async (directToken) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/admin/stats`, {
        credentials: 'include',
        headers: { Authorization: `Bearer ${directToken}` },
      });
      if (!res.ok) {
        throw new Error(
          res.status === 403
            ? 'Access forbidden: Administrator privileges required.'
            : 'Invalid authentication token.'
        );
      }
      setToken(directToken);
      const userObj = { role: 'admin', authMethod: 'direct_token' };
      setAdminUser(userObj);
      return { success: true };
    } catch (err) {
      setError(err.message);
      return { success: false, error: err.message };
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    try {
      const currentCsrf = csrfToken || getCookie('csrf_token_cookie');
      await fetch(`${API_BASE}/auth/logout`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
          ...(currentCsrf ? { 'X-CSRF-Token': currentCsrf } : {}),
        },
        body: JSON.stringify({ all_sessions: false }),
      });
    } catch (_) {
      // Ignore network errors on logout
    } finally {
      setToken(null);
      setAdminUser(null);
      setCsrfToken(null);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        token,
        csrfToken,
        adminUser,
        isAuthenticated: !!adminUser,
        loading,
        error,
        setError,
        loginWithEmailPassword,
        loginWithDirectToken,
        logout,
        apiBase: API_BASE,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
