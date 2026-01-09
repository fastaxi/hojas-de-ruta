/**
 * RutasFast - Auth Context
 * Manages JWT authentication with httpOnly cookie for refresh token
 * Access token stored in memory (React state) only - NOT in localStorage
 */
import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';

// API URL - In production, frontend and backend share same origin
// The httpOnly cookie works because SameSite=Lax allows same-site requests
const API_URL = `${process.env.REACT_APP_BACKEND_URL}/api`;

const AuthContext = createContext(null);

// Configure axios to send cookies (required for httpOnly refresh token)
axios.defaults.withCredentials = true;

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [accessToken, setAccessToken] = useState(null);
  
  // Ref to track if we're currently refreshing to prevent duplicate requests
  const isRefreshing = useRef(false);
  const refreshPromise = useRef(null);

  // Setup axios interceptor for automatic token refresh on 401
  useEffect(() => {
    const requestInterceptor = axios.interceptors.request.use(
      (config) => {
        // Add access token to requests if we have one
        if (accessToken) {
          config.headers.Authorization = `Bearer ${accessToken}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    const responseInterceptor = axios.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config;
        
        // Don't retry auth endpoints - they handle their own errors
        if (originalRequest.url?.includes('/auth/')) {
          return Promise.reject(error);
        }
        
        // If 401 and we haven't tried to refresh yet
        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;
          
          // If we're already refreshing, wait for that to complete
          if (isRefreshing.current && refreshPromise.current) {
            try {
              const newToken = await refreshPromise.current;
              originalRequest.headers.Authorization = `Bearer ${newToken}`;
              return axios(originalRequest);
            } catch (refreshError) {
              return Promise.reject(refreshError);
            }
          }
          
          // Start refresh
          isRefreshing.current = true;
          refreshPromise.current = tryRefreshToken();
          
          try {
            const newToken = await refreshPromise.current;
            if (newToken) {
              originalRequest.headers.Authorization = `Bearer ${newToken}`;
              return axios(originalRequest);
            }
          } catch (refreshError) {
            // Refresh failed, logout
            handleLogout();
            return Promise.reject(refreshError);
          } finally {
            isRefreshing.current = false;
            refreshPromise.current = null;
          }
        }
        
        return Promise.reject(error);
      }
    );

    return () => {
      axios.interceptors.request.eject(requestInterceptor);
      axios.interceptors.response.eject(responseInterceptor);
    };
  }, [accessToken]);

  // Try to refresh token (returns new access token or throws)
  const tryRefreshToken = async () => {
    try {
      // Call refresh endpoint - browser will send cookie automatically
      const response = await axios.post(`${API_URL}/auth/refresh`);
      const { access_token, user: userData } = response.data;
      
      setAccessToken(access_token);
      setUser(userData);
      
      return access_token;
    } catch (error) {
      console.error('Token refresh failed:', error);
      throw error;
    }
  };

  // Bootstrap: try to restore session on mount
  useEffect(() => {
    const initAuth = async () => {
      try {
        // Try to refresh - if we have a valid cookie, this will work
        await tryRefreshToken();
      } catch (error) {
        // No valid session, user needs to login
        console.log('No active session');
      } finally {
        setLoading(false);
      }
    };

    initAuth();
  }, []);

  // Login
  const login = async (email, password) => {
    const response = await axios.post(`${API_URL}/auth/login`, { email, password });
    const { access_token, must_change_password, user: userData } = response.data;
    
    setAccessToken(access_token);
    setUser({ ...userData, must_change_password });
    
    // If must_change_password, don't fetch full profile yet
    if (must_change_password) {
      return { ...userData, must_change_password };
    }
    
    // Fetch full user profile
    const profileResponse = await axios.get(`${API_URL}/me`, {
      headers: { Authorization: `Bearer ${access_token}` }
    });
    setUser(profileResponse.data);
    
    return profileResponse.data;
  };

  // Change password
  const changePassword = async (currentPassword, newPassword) => {
    const response = await axios.post(`${API_URL}/me/change-password`, {
      current_password: currentPassword,
      new_password: newPassword
    });
    
    // After successful change, update user state
    if (user) {
      setUser({ ...user, must_change_password: false });
    }
    
    return response.data;
  };

  // Register
  const register = async (data) => {
    const response = await axios.post(`${API_URL}/auth/register`, data);
    return response.data;
  };

  // Logout - calls backend to clear cookie and invalidate tokens
  const handleLogout = useCallback(async () => {
    try {
      await axios.post(`${API_URL}/auth/logout`);
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      // Clear local state regardless of API response
      setUser(null);
      setAccessToken(null);
    }
  }, []);

  // Update profile
  const updateProfile = async (data) => {
    const response = await axios.put(`${API_URL}/me`, data);
    setUser(response.data);
    return response.data;
  };

  // Refresh user data from API
  const refreshUser = useCallback(async () => {
    if (!accessToken) return;
    
    try {
      const response = await axios.get(`${API_URL}/me`);
      setUser(response.data);
    } catch (error) {
      console.error('Error refreshing user:', error);
    }
  }, [accessToken]);

  const value = {
    user,
    loading,
    isAuthenticated: !!user && !!accessToken,
    mustChangePassword: user?.must_change_password || false,
    login,
    register,
    logout: handleLogout,
    changePassword,
    updateProfile,
    refreshUser
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
