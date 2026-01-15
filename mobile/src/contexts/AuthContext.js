/**
 * RutasFast Mobile - Auth Context
 * Manages authentication state across the app
 */
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import api, { tokenService } from '../services/api';
import { ENDPOINTS } from '../services/config';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  // Check for existing session on mount
  useEffect(() => {
    checkAuthStatus();
  }, []);

  const checkAuthStatus = async () => {
    try {
      const token = await tokenService.getAccessToken();
      if (token) {
        // Verify token by fetching user profile
        const response = await api.get(ENDPOINTS.ME);
        setUser(response.data);
        setIsAuthenticated(true);
      }
    } catch (error) {
      // Token invalid or expired
      await tokenService.clearTokens();
      setUser(null);
      setIsAuthenticated(false);
    } finally {
      setIsLoading(false);
    }
  };

  const login = async (email, password) => {
    const response = await api.post(ENDPOINTS.LOGIN, { email, password });
    const { access_token, refresh_token, user: userData } = response.data;
    
    await tokenService.setTokens(access_token, refresh_token);
    setUser(userData);
    setIsAuthenticated(true);
    
    return userData;
  };

  const register = async (userData) => {
    // Registration returns pending status, user must wait for admin approval
    const response = await api.post(ENDPOINTS.REGISTER, userData);
    return response.data;
  };

  const logout = useCallback(async () => {
    try {
      const refreshToken = await tokenService.getRefreshToken();
      if (refreshToken) {
        await api.post(ENDPOINTS.LOGOUT, { refresh_token: refreshToken });
      }
    } catch (error) {
      // Ignore logout errors
    } finally {
      await tokenService.clearTokens();
      setUser(null);
      setIsAuthenticated(false);
    }
  }, []);

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
