/**
 * RutasFast Mobile - API Configuration
 */

// Production API URL
export const API_BASE_URL = 'https://asturia-taxi.emergent.host/api';

// API Endpoints
export const ENDPOINTS = {
  // Mobile Auth
  LOGIN: '/auth/mobile/login',
  REFRESH: '/auth/mobile/refresh',
  LOGOUT: '/auth/mobile/logout',
  
  // User Auth (registration uses web endpoints)
  REGISTER: '/auth/register',
  
  // User Profile
  ME: '/me',
  UPDATE_ME: '/me',
  CHANGE_PASSWORD: '/me/change-password',
  
  // Drivers
  DRIVERS: '/me/drivers',
  
  // Route Sheets
  ROUTE_SHEETS: '/route-sheets',
  
  // App Config (for PDF settings)
  CONFIG: '/config',
};

// Request timeout (ms)
export const REQUEST_TIMEOUT = 30000;
