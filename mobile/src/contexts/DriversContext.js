/**
 * RutasFast Mobile - Drivers Context
 * Global state for drivers list with sync across screens
 */
import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { getDrivers, createDriver, updateDriver, deleteDriver } from '../services/meService';
import { useAuth } from './AuthContext';

const DriversContext = createContext(null);

export function DriversProvider({ children }) {
  const { isAuthenticated } = useAuth();
  const [drivers, setDrivers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [lastFetched, setLastFetched] = useState(null);

  // Fetch drivers when authenticated
  useEffect(() => {
    if (isAuthenticated) {
      refreshDrivers();
    } else {
      setDrivers([]);
      setLastFetched(null);
    }
  }, [isAuthenticated]);

  /**
   * Refresh drivers list from server
   */
  const refreshDrivers = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getDrivers();
      setDrivers(data);
      setLastFetched(Date.now());
      return data;
    } catch (error) {
      console.error('[Drivers] Failed to fetch:', error.message);
      throw error;
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Add a new driver
   */
  const addDriver = useCallback(async (data) => {
    const newDriver = await createDriver(data);
    setDrivers(prev => [...prev, newDriver]);
    return newDriver;
  }, []);

  /**
   * Edit an existing driver
   */
  const editDriver = useCallback(async (driverId, data) => {
    const updated = await updateDriver(driverId, data);
    setDrivers(prev => prev.map(d => d.id === driverId ? updated : d));
    return updated;
  }, []);

  /**
   * Remove a driver
   */
  const removeDriver = useCallback(async (driverId) => {
    await deleteDriver(driverId);
    setDrivers(prev => prev.filter(d => d.id !== driverId));
  }, []);

  /**
   * Check if drivers need refresh (stale after 5 minutes)
   */
  const isStale = useCallback(() => {
    if (!lastFetched) return true;
    const fiveMinutes = 5 * 60 * 1000;
    return Date.now() - lastFetched > fiveMinutes;
  }, [lastFetched]);

  /**
   * Ensure drivers are loaded (fetch if stale or empty)
   */
  const ensureLoaded = useCallback(async () => {
    if (drivers.length === 0 || isStale()) {
      return refreshDrivers();
    }
    return drivers;
  }, [drivers, isStale, refreshDrivers]);

  const value = {
    drivers,
    loading,
    refreshDrivers,
    addDriver,
    editDriver,
    removeDriver,
    ensureLoaded,
    isStale,
  };

  return (
    <DriversContext.Provider value={value}>
      {children}
    </DriversContext.Provider>
  );
}

export function useDrivers() {
  const context = useContext(DriversContext);
  if (!context) {
    throw new Error('useDrivers must be used within DriversProvider');
  }
  return context;
}
