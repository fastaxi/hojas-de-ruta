/**
 * RutasFast Mobile - PDF Service
 * Handles PDF download, caching, and sharing
 * 
 * SECURITY: Never log tokens or authorization headers
 */
import * as FileSystem from 'expo-file-system';
import * as Sharing from 'expo-sharing';

// Production mode - disable verbose logging
const IS_PRODUCTION = !__DEV__;

/**
 * Safe logger - never logs sensitive data
 */
const log = {
  info: (msg, data) => {
    if (IS_PRODUCTION) return;
    console.log(`[PDF] ${msg}`, data ? sanitizeForLog(data) : '');
  },
  error: (msg, error) => {
    // Always log errors but sanitize
    console.error(`[PDF] ${msg}`, error?.message || '');
  },
};

/**
 * Sanitize data for logging - remove sensitive fields
 */
function sanitizeForLog(data) {
  if (!data || typeof data !== 'object') return data;
  const { headers, Authorization, authorization, token, ...safe } = data;
  return safe;
}

/**
 * Downloads a PDF from URL to local filesystem
 * 
 * @param {object} options
 * @param {string} options.url - Full URL to download from
 * @param {string} options.filename - Desired filename (will ensure .pdf extension)
 * @param {object} options.headers - HTTP headers (including Authorization)
 * @returns {Promise<string>} Local URI of downloaded file
 * @throws {Error} With status property on HTTP errors
 */
export async function downloadPdfToFile({ url, filename, headers = {} }) {
  // Ensure .pdf extension
  const safeName = filename.endsWith('.pdf') ? filename : `${filename}.pdf`;
  const localUri = FileSystem.documentDirectory + safeName;

  // Delete existing file to avoid iOS reuse issues
  try {
    await FileSystem.deleteAsync(localUri, { idempotent: true });
  } catch (e) {
    // Ignore deletion errors
  }

  log.info('Downloading PDF', { filename: safeName, urlPath: url.split('?')[0] });

  const result = await FileSystem.downloadAsync(url, localUri, { headers });

  // Check for HTTP errors
  if (result.status !== 200) {
    // Clean up partial download
    try {
      await FileSystem.deleteAsync(localUri, { idempotent: true });
    } catch (e) {}

    const error = new Error(getErrorMessage(result.status));
    error.status = result.status;
    log.error(`Download failed with status ${result.status}`);
    throw error;
  }

  // Verify file exists and has content
  const fileInfo = await FileSystem.getInfoAsync(localUri);
  if (!fileInfo.exists || fileInfo.size === 0) {
    try {
      await FileSystem.deleteAsync(localUri, { idempotent: true });
    } catch (e) {}
    const error = new Error('El PDF está vacío o no se pudo descargar');
    error.status = 204;
    throw error;
  }

  log.info('Download complete', { size: fileInfo.size });
  return result.uri;
}

/**
 * Shares a local file via native share sheet
 * 
 * @param {string} localUri - Local file URI
 * @param {object} options
 * @param {string} options.dialogTitle - Title for share dialog
 * @returns {Promise<object>} Result with shared status
 */
export async function sharePdfFile(localUri, { dialogTitle } = {}) {
  const canShare = await Sharing.isAvailableAsync();
  
  if (!canShare) {
    log.info('Sharing not available on this device');
    return { 
      shared: false, 
      reason: 'sharing_unavailable', 
      uri: localUri,
      message: 'Compartir no está disponible en este dispositivo'
    };
  }

  try {
    // shareAsync opens the native share sheet with the file attached
    await Sharing.shareAsync(localUri, {
      mimeType: 'application/pdf',
      dialogTitle: dialogTitle || 'Compartir PDF',
      UTI: 'com.adobe.pdf', // iOS specific
    });

    return { shared: true, uri: localUri };
  } catch (error) {
    // User cancelled share - this is not an error
    if (error.message?.includes('cancel') || 
        error.message?.includes('dismiss') ||
        error.message?.includes('user')) {
      log.info('Share cancelled by user');
      return { shared: false, reason: 'cancelled', uri: localUri };
    }
    throw error;
  }
}

/**
 * Deletes a local PDF file
 * 
 * @param {string} localUri - Local file URI to delete
 * @returns {Promise<boolean>} True if deleted successfully
 */
export async function deleteLocalPdf(localUri) {
  try {
    await FileSystem.deleteAsync(localUri, { idempotent: true });
    return true;
  } catch (error) {
    return false;
  }
}

/**
 * Clears all cached PDFs from document directory
 * 
 * @returns {Promise<number>} Number of files deleted
 */
export async function clearPdfCache() {
  try {
    const dir = FileSystem.documentDirectory;
    const files = await FileSystem.readDirectoryAsync(dir);
    const pdfFiles = files.filter(f => f.endsWith('.pdf'));
    
    let deleted = 0;
    for (const file of pdfFiles) {
      try {
        await FileSystem.deleteAsync(dir + file, { idempotent: true });
        deleted++;
      } catch (e) {}
    }
    
    log.info(`Cache cleared: ${deleted} files`);
    return deleted;
  } catch (error) {
    return 0;
  }
}

/**
 * Gets human-readable error message for HTTP status
 */
function getErrorMessage(status) {
  switch (status) {
    case 401:
      return 'Sesión expirada. Por favor, inicia sesión de nuevo.';
    case 403:
      return 'No tienes permiso para descargar este PDF.';
    case 404:
      return 'No hay PDF disponible para esta hoja.';
    case 204:
      return 'No hay contenido para generar el PDF.';
    case 429:
      return 'Demasiadas descargas. Inténtalo más tarde.';
    case 500:
    case 502:
    case 503:
      return 'Error del servidor. Intenta más tarde.';
    default:
      return `Error al preparar el PDF (código ${status})`;
  }
}

/**
 * Error titles by status code
 */
export function getErrorTitle(status) {
  switch (status) {
    case 401:
    case 403:
      return 'Sesión Caducada';
    case 404:
    case 204:
      return 'PDF No Disponible';
    case 429:
      return 'Límite Alcanzado';
    default:
      return 'Error';
  }
}
