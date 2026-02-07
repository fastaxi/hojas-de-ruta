/**
 * RutasFast Mobile - PDF Cache Utility
 * Manages offline PDF caching with limit of 50 files
 */
import * as FileSystem from 'expo-file-system';
import * as IntentLauncher from 'expo-intent-launcher';
import { Platform } from 'react-native';

const CACHE_DIR = FileSystem.documentDirectory + 'rutasfast_pdfs/';
const MAX_CACHED_PDFS = 50;

/**
 * Convert sheet number to safe filename
 */
export function toSafeFilename(sheetNumber) {
  if (!sheetNumber) return 'unknown';
  return sheetNumber.replace(/\//g, '_').replace(/[^a-zA-Z0-9_-]/g, '');
}

/**
 * Ensure cache directory exists
 */
export async function ensureCacheDir() {
  const dirInfo = await FileSystem.getInfoAsync(CACHE_DIR);
  if (!dirInfo.exists) {
    await FileSystem.makeDirectoryAsync(CACHE_DIR, { intermediates: true });
  }
}

/**
 * Get PDF file path for a sheet
 */
export function getPdfPath(sheetNumber) {
  const safeName = toSafeFilename(sheetNumber);
  return `${CACHE_DIR}hoja_${safeName}.pdf`;
}

/**
 * Check if PDF is cached
 */
export async function isPdfCached(sheetNumber) {
  const path = getPdfPath(sheetNumber);
  const info = await FileSystem.getInfoAsync(path);
  return info.exists;
}

/**
 * List all cached PDFs with modification times
 */
export async function listCachedPdfs() {
  await ensureCacheDir();
  
  try {
    const files = await FileSystem.readDirectoryAsync(CACHE_DIR);
    const pdfFiles = files.filter(f => f.endsWith('.pdf'));
    
    const filesWithInfo = await Promise.all(
      pdfFiles.map(async (filename) => {
        const path = CACHE_DIR + filename;
        const info = await FileSystem.getInfoAsync(path);
        return {
          filename,
          path,
          modificationTime: info.modificationTime || 0,
        };
      })
    );
    
    // Sort by modification time (oldest first)
    return filesWithInfo.sort((a, b) => a.modificationTime - b.modificationTime);
  } catch (error) {
    console.log('[pdfCache] Error listing PDFs:', error.message);
    return [];
  }
}

/**
 * Enforce cache limit - delete oldest files if over limit
 */
export async function enforceCacheLimit() {
  try {
    const cachedPdfs = await listCachedPdfs();
    
    if (cachedPdfs.length > MAX_CACHED_PDFS) {
      const toDelete = cachedPdfs.slice(0, cachedPdfs.length - MAX_CACHED_PDFS);
      
      for (const file of toDelete) {
        console.log('[pdfCache] Deleting old PDF:', file.filename);
        await FileSystem.deleteAsync(file.path, { idempotent: true });
      }
      
      console.log(`[pdfCache] Deleted ${toDelete.length} old PDFs`);
    }
  } catch (error) {
    console.log('[pdfCache] Error enforcing limit:', error.message);
  }
}

/**
 * Open PDF on Android using Intent
 */
export async function openPdfAndroid(filePath) {
  if (Platform.OS !== 'android') {
    throw new Error('openPdfAndroid only works on Android');
  }
  
  try {
    const contentUri = await FileSystem.getContentUriAsync(filePath);
    
    await IntentLauncher.startActivityAsync('android.intent.action.VIEW', {
      data: contentUri,
      flags: 1, // FLAG_GRANT_READ_URI_PERMISSION
      type: 'application/pdf',
    });
    
    return true;
  } catch (error) {
    console.log('[pdfCache] Error opening PDF:', error.message);
    throw error;
  }
}

/**
 * Save PDF to cache
 */
export async function savePdfToCache(sheetNumber, pdfData) {
  await ensureCacheDir();
  
  const path = getPdfPath(sheetNumber);
  
  // pdfData should be base64 string
  await FileSystem.writeAsStringAsync(path, pdfData, {
    encoding: FileSystem.EncodingType.Base64,
  });
  
  // Enforce limit after saving
  await enforceCacheLimit();
  
  return path;
}

/**
 * Get cached PDF path if exists
 */
export async function getCachedPdfPath(sheetNumber) {
  const path = getPdfPath(sheetNumber);
  const info = await FileSystem.getInfoAsync(path);
  
  if (info.exists) {
    return path;
  }
  
  return null;
}

/**
 * Clear entire cache
 */
export async function clearCache() {
  try {
    await FileSystem.deleteAsync(CACHE_DIR, { idempotent: true });
    await ensureCacheDir();
    console.log('[pdfCache] Cache cleared');
  } catch (error) {
    console.log('[pdfCache] Error clearing cache:', error.message);
  }
}

/**
 * Get cache stats
 */
export async function getCacheStats() {
  const cachedPdfs = await listCachedPdfs();
  let totalSize = 0;
  
  for (const file of cachedPdfs) {
    const info = await FileSystem.getInfoAsync(file.path);
    totalSize += info.size || 0;
  }
  
  return {
    count: cachedPdfs.length,
    maxCount: MAX_CACHED_PDFS,
    totalSizeMB: (totalSize / (1024 * 1024)).toFixed(2),
  };
}
