/**
 * RutasFast Mobile - Auth Context
 * Manages authentication state across the app
 */
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import api, { tokenService, setLogoutCallback } from '../services/api';
import { ENDPOINTS } from '../services/config';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  // Logout function (defined early so we can pass to API service)
  const logout = useCallback(async () => {
    console.log('[Auth] Logging out...');
    try {
      const refreshToken = await tokenService.getRefreshToken();
      if (refreshToken) {
        // Try to invalidate token on server (best effort)
        await api.post(ENDPOINTS.LOGOUT, { refresh_token: refreshToken }).catch(() => {});
      }
    } catch (error) {
      // Ignore logout API errors
    } finally {
      await tokenService.clearTokens();
      setUser(null);
      setIsAuthenticated(false);
    }
  }, []);

  // Set logout callback for API interceptor
  useEffect(() => {
    setLogoutCallback(() => {
      console.log('[Auth] Forced logout from API interceptor');
      setUser(null);
      setIsAuthenticated(false);
    });
  }, []);

  // Check for existing session on mount
  useEffect(() => {
    checkAuthStatus();
  }, []);

  const checkAuthStatus = async () => {
    console.log('[Auth] Checking auth status...');
    try {
      const { hasAccessToken, hasRefreshToken } = await tokenService.initializeFromStorage();
      
      if (!hasAccessToken && !hasRefreshToken) {
        console.log('[Auth] No tokens found');
        setIsLoading(false);
        return;
      }

      // Verify token by fetching user profile
      const response = await api.get(ENDPOINTS.ME);
      setUser(response.data);
      setIsAuthenticated(true);
      console.log('[Auth] Session restored for:', response.data.email);
    } catch (error) {
      console.log('[Auth] Session check failed:', error.message);
      // Token invalid or expired - will be handled by interceptor
      await tokenService.clearTokens();
      setUser(null);
      setIsAuthenticated(false);
    } finally {
      setIsLoading(false);
    }
  };

  const login = async (email, password) => {
    console.log('[Auth] Logging in:', email);
    const response = await api.post(ENDPOINTS.LOGIN, { email, password });
    const { access_token, refresh_token, user: userData } = response.data;
    
    await tokenService.setTokens(access_token, refresh_token);
    setUser(userData);
    setIsAuthenticated(true);
    console.log('[Auth] Login successful');
    
    return userData;
  };

  const register = async (userData) => {
    console.log('[Auth] Registering:', userData.email);
    // Registration returns pending status, user must wait for admin approval
    const response = await api.post(ENDPOINTS.REGISTER, userData);
    return response.data;
  };

  const updateUser = async (updates) => {
    const response = await api.put(ENDPOINTS.UPDATE_ME, updates);
    setUser(response.data);
    return response.data;
  };

  const changePassword = async (currentPassword, newPassword) => {
    await api.post(ENDPOINTS.CHANGE_PASSWORD, {
      current_password: currentPassword,
      new_password: newPassword,
    });
  };

  const refreshUser = async () => {
    const response = await api.get(ENDPOINTS.ME);
    setUser(response.data);
    return response.data;
  };

  const value = {
    user,
    isLoading,
    isAuthenticated,
    login,
    register,
    logout,
    updateUser,
    changePassword,
    refreshUser,
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
