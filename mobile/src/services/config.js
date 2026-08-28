/**
 * RutasFast Mobile - API Configuration
 */
import Constants from 'expo-constants';

// Backend URL from env (EXPO_PUBLIC_* is inlined at build time by Expo/EAS)
// or from app config extra (legacy builds)
const BASE_URL = process.env.EXPO_PUBLIC_BACKEND_URL || Constants.expoConfig?.extra?.API_BASE_URL;
if (!BASE_URL) {
  throw new Error('EXPO_PUBLIC_BACKEND_URL no configurada (mobile/.env o eas.json build env)');
}
export const API_BASE_URL = `${BASE_URL}/api`;

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
  
  // Assistance Companies
  ASSISTANCE_COMPANIES: '/me/assistance-companies',
  
  // Route Sheets
  ROUTE_SHEETS: '/route-sheets',
  
  // App Config (for PDF settings)
  CONFIG: '/config',
};

// Request timeout (ms)
export const REQUEST_TIMEOUT = 30000;
