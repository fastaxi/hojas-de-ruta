/**
 * RutasFast - Admin Auth Context
 * Manages admin JWT authentication
 */
import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';

const API_URL = `${process.env.REACT_APP_BACKEND_URL}/api`;

const AdminAuthContext = createContext(null);

export function AdminAuthProvider({ children }) {
  const [isAdmin, setIsAdmin] = useState(false);
  const [loading, setLoading] = useState(true);
  const [adminToken, setAdminToken] = useState(localStorage.getItem('adminToken'));
  const tokenRef = useRef(adminToken);

  // Keep ref in sync with state - prevents stale closure issues
  useEffect(() => {
    tokenRef.current = adminToken;
  }, [adminToken]);

  useEffect(() => {
    const token = localStorage.getItem('adminToken');
    if (token) {
      verifyAdminToken(token);
    } else {
      setLoading(false);
    }
  }, []);

  const verifyAdminToken = async (token) => {
    try {
      await axios.get(`${API_URL}/admin/config`, {
        headers: { Authorization: `Bearer ${token}` }
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
    
    tokenRef.current = access_token;
    setAdminToken(access_token);
    localStorage.setItem('adminToken', access_token);
    setIsAdmin(true);
    
    return response.data;
  };

  const logout = useCallback(() => {
    setIsAdmin(false);
    setAdminToken(null);
    tokenRef.current = null;
    localStorage.removeItem('adminToken');
  }, []);

  // Always reads from ref - never stale, stable reference
  const adminRequest = useCallback(async (method, endpoint, data = null) => {
    const currentToken = tokenRef.current;
    if (!currentToken) {
      throw new Error('No admin token available');
    }

    const config = {
      method,
      url: `${API_URL}${endpoint}`,
      headers: { Authorization: `Bearer ${currentToken}` }
    };
    
    if (data) {
      config.data = data;
    }
    
    try {
      const response = await axios(config);
      return response.data;
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
