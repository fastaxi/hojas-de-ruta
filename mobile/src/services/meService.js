/**
 * RutasFast Mobile - Me Service
 * User profile and drivers management
 */
import api from './api';
import { ENDPOINTS } from './config';

/**
 * Get current user profile
 */
export const getMe = async () => {
  const response = await api.get(ENDPOINTS.ME);
  return response.data;
};

/**
 * Update current user profile
 * @param {object} data - Fields to update
 */
export const updateMe = async (data) => {
  const response = await api.put(ENDPOINTS.UPDATE_ME, data);
  return response.data;
};

/**
 * Change password
 * @param {string} currentPassword 
 * @param {string} newPassword 
 */
export const changePassword = async (currentPassword, newPassword) => {
  const response = await api.post(ENDPOINTS.CHANGE_PASSWORD, {
    current_password: currentPassword,
    new_password: newPassword,
  });
  return response.data;
};

/**
 * Get all drivers for current user
 */
export const getDrivers = async () => {
  const response = await api.get(ENDPOINTS.DRIVERS);
  return response.data;
};

/**
 * Create a new driver
 * @param {object} data - { full_name, dni }
 */
export const createDriver = async (data) => {
  const response = await api.post(ENDPOINTS.DRIVERS, data);
  return response.data;
};

/**
 * Update a driver
 * @param {string} driverId 
 * @param {object} data - { full_name, dni }
 */
export const updateDriver = async (driverId, data) => {
  const response = await api.put(`${ENDPOINTS.DRIVERS}/${driverId}`, data);
  return response.data;
};

/**
 * Delete a driver
 * @param {string} driverId 
 */
export const deleteDriver = async (driverId) => {
  const response = await api.delete(`${ENDPOINTS.DRIVERS}/${driverId}`);
  return response.data;
};
