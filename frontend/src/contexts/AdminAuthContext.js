/**
 * RutasFast - Admin Auth Context
 * Manages admin JWT authentication
 */
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import axios from 'axios';

const API_URL = `${process.env.REACT_APP_BACKEND_URL}/api`;

const AdminAuthContext = createContext(null);

export function AdminAuthProvider({ children }) {
  const [isAdmin, setIsAdmin] = useState(false);
  const [loading, setLoading] = useState(true);
  const [adminToken, setAdminToken] = useState(localStorage.getItem('adminToken'));

  useEffect(() => {
    if (adminToken) {
      // Verify token is still valid by making a test request
      verifyAdminToken();
    } else {
      setLoading(false);
    }
  }, []);

  const verifyAdminToken = async () => {
    try {
      await axios.get(`${API_URL}/admin/config`, {
        headers: { Authorization: `Bearer ${adminToken}` }
      });
      setIsAdmin(true);
    } catch (error) {
      logout();
    } finally {
      setLoading(false);
    }
  };

  const login = async (username, password) => {
    const response = await axios.post(`${API_URL}/admin/login`, { username, password });
    const { access_token } = response.data;
    
    setAdminToken(access_token);
    localStorage.setItem('adminToken', access_token);
    setIsAdmin(true);
    
    return response.data;
  };

  const logout = useCallback(() => {
    setIsAdmin(false);
    setAdminToken(null);
    localStorage.removeItem('adminToken');
  }, []);

  // Helper for admin API calls
  const adminRequest = useCallback(async (method, endpoint, data = null) => {
    const config = {
      method,
      url: `${API_URL}${endpoint}`,
      headers: { Authorization: `Bearer ${adminToken}` }
    };
    
    if (data) {
      config.data = data;
    }
    
    const response = await axios(config);
    return response.data;
  }, [adminToken]);

  const value = {
    isAdmin,
    loading,
    login,
    logout,
    adminToken,
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
