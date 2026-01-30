/**
 * RutasFast Mobile - Filename Utilities
 * Cross-platform safe filename generation and date range validation
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
  const num = toSafeFilenamePart(String(sheet.seq_number || sheet.id));
  const year = sheet.year || new Date().getFullYear();
  return `hoja_ruta_${num}_${year}.pdf`;
};

/**
 * Generates a safe PDF filename for a date range export
 * @param {string} fromDate - Start date (YYYY-MM-DD)
 * @param {string} toDate - End date (YYYY-MM-DD)
 * @returns {string} Safe filename with .pdf extension
 */
export const generateRangePdfFilename = (fromDate, toDate) => {
  // Keep dashes in dates for readability
  const from = toSafeFilenamePart(fromDate || 'inicio');
  const to = toSafeFilenamePart(toDate || 'fin');
  return `hojas_ruta_${from}_a_${to}.pdf`;
};

/**
 * Maximum days allowed for PDF range export
 */
export const MAX_RANGE_DAYS = 31;

/**
 * Validates a date range for PDF export
 * 
 * @param {string} fromDate - Start date (YYYY-MM-DD)
 * @param {string} toDate - End date (YYYY-MM-DD)
 * @returns {object} { valid: boolean, message?: string }
 */
export const validateDateRange = (fromDate, toDate) => {
  // Both dates required
  if (!fromDate || !toDate) {
    return {
      valid: false,
      message: 'Debes seleccionar ambas fechas (desde y hasta).',
    };
  }

  const from = new Date(fromDate);
  const to = new Date(toDate);

  // Valid dates
  if (isNaN(from.getTime()) || isNaN(to.getTime())) {
    return {
      valid: false,
      message: 'Las fechas introducidas no son válidas.',
    };
  }

  // from <= to
  if (from > to) {
    return {
      valid: false,
      message: 'La fecha "desde" no puede ser posterior a la fecha "hasta".',
    };
  }

  // Max 31 days
  const diffTime = Math.abs(to - from);
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  
  if (diffDays > MAX_RANGE_DAYS) {
    return {
      valid: false,
      message: `El rango máximo es de ${MAX_RANGE_DAYS} días. Has seleccionado ${diffDays} días.`,
    };
  }

  return { valid: true };
};

/**
 * Formats a Date object to YYYY-MM-DD string
 * @param {Date} date 
 * @returns {string}
 */
export const formatDateToISO = (date) => {
  if (!date) return '';
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

/**
 * Parses YYYY-MM-DD string to Date object
 * @param {string} dateStr 
 * @returns {Date|null}
 */
export const parseISODate = (dateStr) => {
  if (!dateStr) return null;
  const [year, month, day] = dateStr.split('-').map(Number);
  if (!year || !month || !day) return null;
  return new Date(year, month - 1, day);
};
