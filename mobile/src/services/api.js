/**
 * RutasFast Mobile - API Service
 * Handles all HTTP requests to the backend with auth token management
 */
import axios from 'axios';
import * as SecureStore from 'expo-secure-store';
import { API_BASE_URL, REQUEST_TIMEOUT } from './config';

// Token storage keys
const ACCESS_TOKEN_KEY = 'rutasfast_access_token';
const REFRESH_TOKEN_KEY = 'rutasfast_refresh_token';

// In-memory token cache for faster access
let cachedAccessToken = null;
let cachedRefreshToken = null;

// Logout callback (set by AuthContext)
let onLogoutCallback = null;

/**
 * Token management service
 */
export const tokenService = {
  async getAccessToken() {
    if (cachedAccessToken) return cachedAccessToken;
    cachedAccessToken = await SecureStore.getItemAsync(ACCESS_TOKEN_KEY);
    return cachedAccessToken;
  },
  
  async getRefreshToken() {
    if (cachedRefreshToken) return cachedRefreshToken;
    cachedRefreshToken = await SecureStore.getItemAsync(REFRESH_TOKEN_KEY);
    return cachedRefreshToken;
  },
  
  async setTokens(accessToken, refreshToken) {
    cachedAccessToken = accessToken;
    await SecureStore.setItemAsync(ACCESS_TOKEN_KEY, accessToken);
    if (refreshToken) {
      cachedRefreshToken = refreshToken;
      await SecureStore.setItemAsync(REFRESH_TOKEN_KEY, refreshToken);
    }
  },
  
  async clearTokens() {
    cachedAccessToken = null;
    cachedRefreshToken = null;
    await SecureStore.deleteItemAsync(ACCESS_TOKEN_KEY);
    await SecureStore.deleteItemAsync(REFRESH_TOKEN_KEY);
  },

  // Initialize tokens on app start
  async initializeFromStorage() {
    try {
      cachedAccessToken = await SecureStore.getItemAsync(ACCESS_TOKEN_KEY);
      cachedRefreshToken = await SecureStore.getItemAsync(REFRESH_TOKEN_KEY);
      return { 
        hasAccessToken: !!cachedAccessToken,
        hasRefreshToken: !!cachedRefreshToken 
      };
    } catch (error) {
      console.log('[TokenService] Error reading from storage:', error.message);
      cachedAccessToken = null;
      cachedRefreshToken = null;
      return { hasAccessToken: false, hasRefreshToken: false };
    }
  },
};

/**
 * Set logout callback (called from AuthContext)
 */
export const setLogoutCallback = (callback) => {
  onLogoutCallback = callback;
};

/**
 * Force logout - clears tokens and calls logout callback
 */
const forceLogout = async () => {
  await tokenService.clearTokens();
  if (onLogoutCallback) {
    onLogoutCallback();
  }
};

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: REQUEST_TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor - add auth token
api.interceptors.request.use(
  async (config) => {
    const token = await tokenService.getAccessToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor - handle token refresh
let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    // If 401 and not already retrying
    if (error.response?.status === 401 && !originalRequest._retry) {
      // If this is already a refresh request, don't retry
      if (originalRequest.url?.includes('/auth/mobile/refresh')) {
        console.log('[API] Refresh token failed, forcing logout');
        await forceLogout();
        return Promise.reject(error);
      }

      if (isRefreshing) {
        // Queue this request while refreshing
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            return api(originalRequest);
          })
          .catch((err) => Promise.reject(err));
      }
      
      originalRequest._retry = true;
      isRefreshing = true;
      
      try {
        const refreshToken = await tokenService.getRefreshToken();
        if (!refreshToken) {
          console.log('[API] No refresh token available, forcing logout');
          await forceLogout();
          throw new Error('No refresh token');
        }
        
        console.log('[API] Attempting token refresh...');
        
        // Use raw axios to avoid interceptors
        const response = await axios.post(
          `${API_BASE_URL}/auth/mobile/refresh`,
          { refresh_token: refreshToken },
          { timeout: REQUEST_TIMEOUT }
        );
        
        const { access_token, refresh_token: newRefreshToken } = response.data;
        
        console.log('[API] Token refresh successful');
        await tokenService.setTokens(access_token, newRefreshToken);
        
        processQueue(null, access_token);
        
        originalRequest.headers.Authorization = `Bearer ${access_token}`;
        return api(originalRequest);
      } catch (refreshError) {
        console.error('[API] Token refresh failed:', refreshError.message);
        processQueue(refreshError, null);
        await forceLogout();
        throw refreshError;
      } finally {
        isRefreshing = false;
      }
    }
    
    return Promise.reject(error);
  }
);

export default api;
