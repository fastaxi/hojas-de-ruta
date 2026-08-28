/**
 * RutasFast - Admin Auth Context
 * Admin session stored in an httpOnly cookie (no tokens in localStorage)
 */
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import axios from 'axios';

const API_URL = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Cookies must travel with every request (independent of AuthContext side-effects)
axios.defaults.withCredentials = true;

const AdminAuthContext = createContext(null);

export function AdminAuthProvider({ children }) {
  const [isAdmin, setIsAdmin] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Cleanup: tokens are no longer kept in localStorage
    localStorage.removeItem('adminToken');
    // Only check the admin session cookie on admin routes
    if (!window.location.pathname.startsWith('/admin')) {
      setLoading(false);
      return;
    }
    const verifySession = async () => {
      try {
        await axios.get(`${API_URL}/admin/config`);
        setIsAdmin(true);
      } catch (error) {
        setIsAdmin(false);
      } finally {
        setLoading(false);
      }
    };
    verifySession();
  }, []);

  const login = async (username, password) => {
    const response = await axios.post(`${API_URL}/admin/login`, { username, password });
    setIsAdmin(true);
    return response.data;
  };

  const logout = useCallback(async () => {
    try {
      await axios.post(`${API_URL}/admin/logout`);
    } catch (error) {
      // Clearing local state regardless of API response
    }
    setIsAdmin(false);
  }, []);

  const adminRequest = useCallback(async (method, endpoint, data = null, options = {}) => {
    const config = { method, url: `${API_URL}${endpoint}` };
    if (data) {
      config.data = data;
    }
    try {
      const response = await axios(config);
      return options.fullResponse ? response : response.data;
    } catch (error) {
      if (error.response?.status === 401) {
        logout();
      }
      throw error;
    }
  }, [logout]);

  const value = {
    isAdmin,
    loading,
    login,
    logout,
    adminRequest
  };

  return (
    <AdminAuthContext.Provider value={value}>
      {children}
    </AdminAuthContext.Provider>
  );
}

export function useAdminAuth() {
  const context = useContext(AdminAuthContext);
  if (!context) {
    throw new Error('useAdminAuth must be used within AdminAuthProvider');
  }
  return context;
}
