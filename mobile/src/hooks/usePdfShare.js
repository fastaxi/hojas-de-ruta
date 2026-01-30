/**
 * RutasFast Mobile - usePdfShare Hook
 * Handles PDF download and sharing with:
 * - Loading states per sheet
 * - Double-click prevention
 * - Comprehensive error handling
 * - Date range PDF support
 * 
 * SECURITY: No tokens logged
 */
import { useState, useCallback, useRef } from 'react';
import { Alert } from 'react-native';
import { downloadPdfToFile, sharePdfFile, getErrorTitle } from '../services/pdfService';
import { generateSheetPdfFilename, generateRangePdfFilename, validateDateRange } from '../utils/filename';
import { tokenService } from '../services/api';
import { API_BASE_URL, ENDPOINTS } from '../services/config';

/**
 * Hook for PDF download and sharing functionality
 * Prevents double-clicks and provides consistent error handling
 */
export function usePdfShare() {
  const [preparingPdfId, setPreparingPdfId] = useState(null);
  const [preparingRange, setPreparingRange] = useState(false);
  
  // Ref to track in-flight requests and prevent duplicates
  const pendingRequests = useRef(new Set());

  /**
   * Safe wrapper that handles all errors gracefully
   * Never crashes, always shows user-friendly message
   */
  const sharePdfSafe = useCallback(async (downloadFn, { onStart, onEnd, sheetId } = {}) => {
    // Prevent duplicate requests
    const requestKey = sheetId || 'range';
    if (pendingRequests.current.has(requestKey)) {
      console.log('[PDF] Request already in progress, ignoring');
      return { success: false, reason: 'duplicate' };
    }

    pendingRequests.current.add(requestKey);
    onStart?.();

    try {
      const result = await downloadFn();
      return { success: true, ...result };
    } catch (error) {
      handlePdfError(error);
      return { success: false, error };
    } finally {
      pendingRequests.current.delete(requestKey);
      onEnd?.();
    }
  }, []);

  /**
   * Downloads and shares a single route sheet PDF
   */
  const shareSheetPdf = useCallback(async (sheet) => {
    // Check if already preparing this sheet
    if (preparingPdfId === sheet.id) {
      return { success: false, reason: 'already_preparing' };
    }

    return sharePdfSafe(
      async () => {
        const accessToken = await tokenService.getAccessToken();
        if (!accessToken) {
          const error = new Error('No hay sesión activa');
          error.status = 401;
          throw error;
        }

        const filename = generateSheetPdfFilename(sheet);
        const url = `${API_BASE_URL}${ENDPOINTS.ROUTE_SHEETS}/${sheet.id}/pdf`;
        
        const headers = {
          Authorization: `Bearer ${accessToken}`,
        };

        // Download PDF
        const localUri = await downloadPdfToFile({ url, filename, headers });
        
        // Share via native share sheet
        const result = await sharePdfFile(localUri, {
          dialogTitle: `Hoja de ruta #${sheet.seq_number}/${sheet.year}`,
        });

        if (!result.shared && result.reason === 'sharing_unavailable') {
          Alert.alert(
            'Compartir no disponible',
            'El PDF se ha descargado correctamente pero no se puede compartir en este dispositivo.',
            [{ text: 'OK' }]
          );
        }

        return result;
      },
      {
        sheetId: sheet.id,
        onStart: () => setPreparingPdfId(sheet.id),
        onEnd: () => setPreparingPdfId(null),
      }
    );
  }, [preparingPdfId, sharePdfSafe]);

  /**
   * Downloads a single route sheet PDF (without sharing)
   */
  const downloadSheetPdf = useCallback(async (sheet) => {
    if (preparingPdfId === sheet.id) {
      return { success: false, reason: 'already_preparing' };
    }

    return sharePdfSafe(
      async () => {
        const accessToken = await tokenService.getAccessToken();
        if (!accessToken) {
          const error = new Error('No hay sesión activa');
          error.status = 401;
          throw error;
        }

        const filename = generateSheetPdfFilename(sheet);
        const url = `${API_BASE_URL}${ENDPOINTS.ROUTE_SHEETS}/${sheet.id}/pdf`;
        
        const headers = {
          Authorization: `Bearer ${accessToken}`,
        };

        const localUri = await downloadPdfToFile({ url, filename, headers });
        
        Alert.alert(
          'PDF Descargado',
          `El archivo se guardó como ${filename}`,
          [{ text: 'OK' }]
        );
        
        return { downloaded: true, uri: localUri, filename };
      },
      {
        sheetId: sheet.id,
        onStart: () => setPreparingPdfId(sheet.id),
        onEnd: () => setPreparingPdfId(null),
      }
    );
  }, [preparingPdfId, sharePdfSafe]);

  /**
   * Downloads and shares PDFs for a date range
   * Validates: both dates required, from <= to, max 31 days
   */
  const shareRangePdf = useCallback(async (fromDate, toDate) => {
    if (preparingRange) {
      return { success: false, reason: 'already_preparing' };
    }

    // Validate date range
    const validation = validateDateRange(fromDate, toDate);
    if (!validation.valid) {
      Alert.alert('Rango Inválido', validation.message, [{ text: 'OK' }]);
      return { success: false, reason: 'validation', message: validation.message };
    }

    return sharePdfSafe(
      async () => {
        const accessToken = await tokenService.getAccessToken();
        if (!accessToken) {
          const error = new Error('No hay sesión activa');
          error.status = 401;
          throw error;
        }

        const filename = generateRangePdfFilename(fromDate, toDate);
        const url = `${API_BASE_URL}${ENDPOINTS.ROUTE_SHEETS}/pdf/range?from_date=${encodeURIComponent(fromDate)}&to_date=${encodeURIComponent(toDate)}`;
        
        const headers = {
          Authorization: `Bearer ${accessToken}`,
        };

        // Download PDF
        const localUri = await downloadPdfToFile({ url, filename, headers });
        
        // Share via native share sheet
        const result = await sharePdfFile(localUri, {
          dialogTitle: `Hojas de ruta ${formatDateForDisplay(fromDate)} - ${formatDateForDisplay(toDate)}`,
        });

        if (!result.shared && result.reason === 'sharing_unavailable') {
          Alert.alert(
            'Compartir no disponible',
            'El PDF se ha descargado correctamente pero no se puede compartir en este dispositivo.',
            [{ text: 'OK' }]
          );
        }

        return result;
      },
      {
        sheetId: 'range',
        onStart: () => setPreparingRange(true),
        onEnd: () => setPreparingRange(false),
      }
    );
  }, [preparingRange, sharePdfSafe]);

  /**
   * Check if a specific sheet is being prepared
   */
  const isPreparingSheet = useCallback((sheetId) => {
    return preparingPdfId === sheetId;
  }, [preparingPdfId]);

  return {
    // States
    preparingPdfId,
    preparingRange,
    isPreparingSheet,
    
    // Actions
    shareSheetPdf,
    downloadSheetPdf,
    shareRangePdf,
  };
}

/**
 * Handles PDF errors with user-friendly alerts
 * Maps HTTP status codes to clear Spanish messages
 */
function handlePdfError(error) {
  const status = error?.status || error?.response?.status;
  const title = getErrorTitle(status);
  
  let message;
  switch (status) {
    case 401:
    case 403:
      message = 'Tu sesión ha caducado. Vuelve a iniciar sesión.';
      break;
    case 404:
    case 204:
      message = 'No hay PDF disponible para esta hoja.';
      break;
    case 429:
      message = 'Demasiadas descargas. Inténtalo más tarde.';
      break;
    default:
      message = error.message || 'Error al preparar el PDF';
  }

  Alert.alert(title, message, [{ text: 'OK' }]);
}

/**
 * Format date for display in dialog title
 */
function formatDateForDisplay(dateStr) {
  if (!dateStr) return '';
  const [year, month, day] = dateStr.split('-');
  return `${day}/${month}/${year}`;
}
