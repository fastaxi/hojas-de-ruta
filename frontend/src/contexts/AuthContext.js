/**
 * RutasFast - Auth Context
 * Manages JWT authentication state with auto-refresh
 */
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import axios from 'axios';

const API_URL = `${process.env.REACT_APP_BACKEND_URL}/api`;

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [accessToken, setAccessToken] = useState(localStorage.getItem('accessToken'));
  const [refreshToken, setRefreshToken] = useState(localStorage.getItem('refreshToken'));

  // Configure axios defaults
  useEffect(() => {
    if (accessToken) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${accessToken}`;
    } else {
      delete axios.defaults.headers.common['Authorization'];
    }
  }, [accessToken]);

  // Fetch user profile
  const fetchUser = useCallback(async () => {
    if (!accessToken) {
      setLoading(false);
      return;
    }

    try {
      const response = await axios.get(`${API_URL}/me`);
      setUser(response.data);
    } catch (error) {
      if (error.response?.status === 401 || error.response?.status === 403) {
        // Try to refresh token
        await tryRefreshToken();
      } else {
        console.error('Error fetching user:', error);
        logout();
      }
    } finally {
      setLoading(false);
    }
  }, [accessToken]);

  // Refresh token
  const tryRefreshToken = async () => {
    if (!refreshToken) {
      logout();
      return;
    }

    try {
      const response = await axios.post(`${API_URL}/auth/refresh`, {
        refresh_token: refreshToken
      });
      
      const { access_token, refresh_token: newRefreshToken } = response.data;
      
      setAccessToken(access_token);
      setRefreshToken(newRefreshToken);
      localStorage.setItem('accessToken', access_token);
      localStorage.setItem('refreshToken', newRefreshToken);
      
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
      
      // Retry fetching user
      const userResponse = await axios.get(`${API_URL}/me`);
      setUser(userResponse.data);
    } catch (error) {
      console.error('Token refresh failed:', error);
      logout();
    }
  };

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  // Login
  const login = async (email, password) => {
    const response = await axios.post(`${API_URL}/auth/login`, { email, password });
    const { access_token, refresh_token } = response.data;
    
    setAccessToken(access_token);
    setRefreshToken(refresh_token);
    localStorage.setItem('accessToken', access_token);
    localStorage.setItem('refreshToken', refresh_token);
    
    axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
    
    // Fetch user data
    const userResponse = await axios.get(`${API_URL}/me`);
    setUser(userResponse.data);
    
    return userResponse.data;
  };

  // Register
  const register = async (data) => {
    const response = await axios.post(`${API_URL}/auth/register`, data);
    return response.data;
  };

  // Logout
  const logout = useCallback(() => {
    setUser(null);
    setAccessToken(null);
    setRefreshToken(null);
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    delete axios.defaults.headers.common['Authorization'];
  }, []);

  // Forgot password
  const forgotPassword = async (email) => {
    const response = await axios.post(`${API_URL}/auth/forgot-password`, { email });
    return response.data;
  };

  // Reset password
  const resetPassword = async (token, newPassword) => {
    const response = await axios.post(`${API_URL}/auth/reset-password`, {
      token,
      new_password: newPassword
    });
    return response.data;
  };

  // Update profile
  const updateProfile = async (data) => {
    const response = await axios.put(`${API_URL}/me`, data);
    setUser(response.data);
    return response.data;
  };

  const value = {
    user,
    loading,
    isAuthenticated: !!user,
    login,
    register,
    logout,
    forgotPassword,
    resetPassword,
    updateProfile,
    refreshUser: fetchUser
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
