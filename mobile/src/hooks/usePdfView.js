/**
 * RutasFast Mobile - PDF View Hook
 * Handles viewing PDFs with offline cache support
 */
import { useState, useCallback } from 'react';
import { Alert, Platform } from 'react-native';
import * as FileSystem from 'expo-file-system';
import api from '../services/api';
import { ENDPOINTS } from '../services/config';
import {
  ensureCacheDir,
  getPdfPath,
  getCachedPdfPath,
  savePdfToCache,
  openPdfAndroid,
} from '../utils/pdfCache';

export function usePdfView() {
  const [viewingPdfId, setViewingPdfId] = useState(null);

  /**
   * View PDF - uses cache if available, downloads if not
   */
  const viewPdf = useCallback(async (sheetId, sheetNumber) => {
    if (viewingPdfId) return; // Prevent double-tap
    
    setViewingPdfId(sheetId);
    
    try {
      await ensureCacheDir();
      
      // Check cache first
      const cachedPath = await getCachedPdfPath(sheetNumber);
      
      if (cachedPath) {
        console.log('[usePdfView] Opening from cache:', sheetNumber);
        await openPdfAndroid(cachedPath);
        setViewingPdfId(null);
        return true;
      }
      
      // Download from server
      console.log('[usePdfView] Downloading PDF:', sheetId);
      
      const response = await api.get(`${ENDPOINTS.ROUTE_SHEETS}/${sheetId}/pdf`, {
        responseType: 'arraybuffer',
      });
      
      if (!response.data || response.data.byteLength === 0) {
        throw new Error('PDF vacío recibido');
      }
      
      // Convert ArrayBuffer to Base64
      const base64 = arrayBufferToBase64(response.data);
      
      // Save to cache
      const savedPath = await savePdfToCache(sheetNumber, base64);
      console.log('[usePdfView] PDF saved to cache:', savedPath);
      
      // Open PDF
      await openPdfAndroid(savedPath);
      
      setViewingPdfId(null);
      return true;
      
    } catch (error) {
      setViewingPdfId(null);
      console.log('[usePdfView] Error:', error.message, error.response?.status);
      
      // Handle specific errors
      if (error.response?.status === 401 || error.response?.status === 403) {
        Alert.alert('Sesión caducada', 'Por favor, vuelve a iniciar sesión');
        return false;
      }
      
      if (error.response?.status === 404) {
        Alert.alert('Error', 'PDF no encontrado');
        return false;
      }
      
      if (error.response?.status === 429) {
        Alert.alert('Límite alcanzado', 'Has descargado demasiados PDFs. Espera unos minutos.');
        return false;
      }
      
      // Check if we have cached version for offline
      const cachedPath = await getCachedPdfPath(sheetNumber);
      if (cachedPath) {
        Alert.alert(
          'Sin conexión',
          'Mostrando versión guardada',
          [
            { text: 'Cancelar', style: 'cancel' },
            { 
              text: 'Ver PDF guardado', 
              onPress: async () => {
                try {
                  await openPdfAndroid(cachedPath);
                } catch (e) {
                  Alert.alert('Error', 'No se pudo abrir el PDF');
                }
              }
            },
          ]
        );
        return false;
      }
      
      Alert.alert('Error', error.message || 'No se pudo cargar el PDF');
      return false;
    }
  }, [viewingPdfId]);

  /**
   * Check if PDF is being viewed
   */
  const isViewingPdf = useCallback((sheetId) => {
    return viewingPdfId === sheetId;
  }, [viewingPdfId]);

  return {
    viewPdf,
    viewingPdfId,
    isViewingPdf,
  };
}

/**
 * Convert ArrayBuffer to Base64
 */
function arrayBufferToBase64(buffer) {
  let binary = '';
  const bytes = new Uint8Array(buffer);
  const len = bytes.byteLength;
  
  for (let i = 0; i < len; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  
  return btoa(binary);
}

export default usePdfView;
