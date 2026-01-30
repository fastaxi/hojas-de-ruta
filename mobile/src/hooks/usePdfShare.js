/**
 * RutasFast Mobile - usePdfShare Hook
 * Handles PDF download and sharing with loading states and error handling
 */
import { useState, useCallback } from 'react';
import { Alert } from 'react-native';
import { downloadPdfToFile, sharePdfFile, deleteLocalPdf } from '../services/pdfService';
import { generateSheetPdfFilename, generateRangePdfFilename } from '../utils/filename';
import { tokenService } from '../services/api';
import { API_BASE_URL, ENDPOINTS } from '../services/config';

/**
 * Hook for PDF download and sharing functionality
 */
export function usePdfShare() {
  const [loading, setLoading] = useState(false);
  const [loadingSheetId, setLoadingSheetId] = useState(null);

  /**
   * Downloads and shares a single route sheet PDF
   */
  const shareSheetPdf = useCallback(async (sheet) => {
    if (loading) return;
    
    setLoading(true);
    setLoadingSheetId(sheet.id);
    
    let localUri = null;
    
    try {
      const accessToken = await tokenService.getAccessToken();
      if (!accessToken) {
        throw { status: 401, message: 'No hay sesión activa' };
      }

      const filename = generateSheetPdfFilename(sheet);
      const url = `${API_BASE_URL}${ENDPOINTS.ROUTE_SHEETS}/${sheet.id}/pdf`;
      
      const headers = {
        Authorization: `Bearer ${accessToken}`,
      };

      // Download PDF
      localUri = await downloadPdfToFile({ url, filename, headers });
      
      // Share via native share sheet
      const result = await sharePdfFile(localUri, {
        dialogTitle: `Hoja de ruta #${sheet.seq_number}/${sheet.year}`,
      });

      if (!result.shared && result.reason === 'sharing_unavailable') {
        Alert.alert(
          'Compartir no disponible',
          'El PDF se ha descargado pero no se puede compartir en este dispositivo.',
          [{ text: 'OK' }]
        );
      }
      
      return result;
    } catch (error) {
      handlePdfError(error, 'compartir');
      return { shared: false, error };
    } finally {
      // Optional: Clean up downloaded file
      // if (localUri) await deleteLocalPdf(localUri);
      setLoading(false);
      setLoadingSheetId(null);
    }
  }, [loading]);

  /**
   * Downloads a single route sheet PDF (without sharing)
   */
  const downloadSheetPdf = useCallback(async (sheet) => {
    if (loading) return;
    
    setLoading(true);
    setLoadingSheetId(sheet.id);
    
    try {
      const accessToken = await tokenService.getAccessToken();
      if (!accessToken) {
        throw { status: 401, message: 'No hay sesión activa' };
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
    } catch (error) {
      handlePdfError(error, 'descargar');
      return { downloaded: false, error };
    } finally {
      setLoading(false);
      setLoadingSheetId(null);
    }
  }, [loading]);

  /**
   * Downloads and shares PDFs for a date range
   */
  const shareRangePdf = useCallback(async (fromDate, toDate) => {
    if (loading) return;
    
    setLoading(true);
    
    let localUri = null;
    
    try {
      const accessToken = await tokenService.getAccessToken();
      if (!accessToken) {
        throw { status: 401, message: 'No hay sesión activa' };
      }

      const filename = generateRangePdfFilename(fromDate, toDate);
      const url = `${API_BASE_URL}${ENDPOINTS.ROUTE_SHEETS}/pdf/range?from_date=${fromDate}&to_date=${toDate}`;
      
      const headers = {
        Authorization: `Bearer ${accessToken}`,
      };

      // Download PDF
      localUri = await downloadPdfToFile({ url, filename, headers });
      
      // Share via native share sheet
      const result = await sharePdfFile(localUri, {
        dialogTitle: `Hojas de ruta (${formatDateRange(fromDate, toDate)})`,
      });

      if (!result.shared && result.reason === 'sharing_unavailable') {
        Alert.alert(
          'Compartir no disponible',
          'El PDF se ha descargado pero no se puede compartir en este dispositivo.',
          [{ text: 'OK' }]
        );
      }
      
      return result;
    } catch (error) {
      handlePdfError(error, 'compartir');
      return { shared: false, error };
    } finally {
      setLoading(false);
    }
  }, [loading]);

  return {
    loading,
    loadingSheetId,
    shareSheetPdf,
    downloadSheetPdf,
    shareRangePdf,
  };
}

/**
 * Handles PDF errors with user-friendly alerts
 */
function handlePdfError(error, action) {
  console.error(`[PDF] Error during ${action}:`, error);
  
  const status = error.status || error.response?.status;
  let title = 'Error';
  let message = error.message || `No se pudo ${action} el PDF`;

  switch (status) {
    case 401:
      title = 'Sesión Expirada';
      message = 'Tu sesión ha expirado. Por favor, inicia sesión de nuevo.';
      break;
    case 403:
      title = 'Sin Permiso';
      message = 'No tienes permiso para acceder a este PDF.';
      break;
    case 404:
      title = 'No Encontrado';
      message = 'El PDF solicitado no existe.';
      break;
    case 204:
      title = 'Sin Contenido';
      message = 'No hay hojas de ruta para generar el PDF.';
      break;
    case 429:
      title = 'Límite Alcanzado';
      message = 'Has solicitado demasiados PDFs. Espera un momento e intenta de nuevo.';
      break;
  }

  Alert.alert(title, message, [{ text: 'OK' }]);
}

/**
 * Formats date range for display
 */
function formatDateRange(from, to) {
  const fromStr = from?.split('T')[0] || '';
  const toStr = to?.split('T')[0] || '';
  return `${fromStr} - ${toStr}`;
}
