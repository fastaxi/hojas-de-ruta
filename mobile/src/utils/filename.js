/**
 * RutasFast Mobile - Filename Utilities
 * Cross-platform safe filename generation
 */

/**
 * Converts a string to a safe filename part.
 * Removes special characters, replaces spaces with underscores,
 * and truncates to max length.
 * 
 * @param {string} input - The input string to sanitize
 * @param {number} maxLength - Maximum length (default 60)
 * @returns {string} Safe filename part
 */
export const toSafeFilenamePart = (input, maxLength = 60) => {
  const str = String(input || '').trim();
  if (!str) return 'unknown';
  
  // Replace non-alphanumeric chars (except dash) with underscore
  // Then collapse multiple underscores and trim leading/trailing
  const out = str
    .normalize('NFD')                    // Decompose accents
    .replace(/[\u0300-\u036f]/g, '')     // Remove accent marks
    .replace(/[^\w-]+/g, '_')            // Replace special chars with _
    .replace(/_+/g, '_')                 // Collapse multiple _
    .replace(/^_+|_+$/g, '');            // Trim _ from ends
  
  return (out || 'unknown').slice(0, maxLength);
};

/**
 * Generates a safe PDF filename for a route sheet
 * @param {object} sheet - Route sheet object
 * @returns {string} Safe filename with .pdf extension
 */
export const generateSheetPdfFilename = (sheet) => {
  const num = toSafeFilenamePart(sheet.seq_number || sheet.id);
  const year = sheet.year || new Date().getFullYear();
  return `hoja_ruta_${num}_${year}.pdf`;
};

/**
 * Generates a safe PDF filename for a date range export
 * @param {string} fromDate - Start date (ISO string or YYYY-MM-DD)
 * @param {string} toDate - End date (ISO string or YYYY-MM-DD)
 * @returns {string} Safe filename with .pdf extension
 */
export const generateRangePdfFilename = (fromDate, toDate) => {
  const from = toSafeFilenamePart(fromDate?.split('T')[0] || 'inicio');
  const to = toSafeFilenamePart(toDate?.split('T')[0] || 'fin');
  return `hojas_ruta_${from}_a_${to}.pdf`;
};
