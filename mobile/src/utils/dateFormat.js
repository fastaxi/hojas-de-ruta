/**
 * RutasFast Mobile - Date formatting utilities
 * Consistent ES format across the app
 */

/**
 * Format datetime to Spanish format: dd/mm/aaaa HH:MM
 * @param {Date|string|null} value - Date object or ISO string
 * @returns {string} Formatted date or '-'
 */
export function formatDateTimeES(value) {
  if (!value) return '-';
  
  try {
    const date = typeof value === 'string' ? new Date(value) : value;
    
    if (isNaN(date.getTime())) return '-';
    
    return new Intl.DateTimeFormat('es-ES', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    }).format(date);
  } catch (error) {
    console.log('[dateFormat] Error formatting datetime:', error.message);
    return '-';
  }
}

/**
 * Format date only to Spanish format: dd/mm/aaaa
 * @param {Date|string|null} value - Date object or ISO string
 * @returns {string} Formatted date or '-'
 */
export function formatDateES(value) {
  if (!value) return '-';
  
  try {
    const date = typeof value === 'string' ? new Date(value) : value;
    
    if (isNaN(date.getTime())) return '-';
    
    return new Intl.DateTimeFormat('es-ES', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    }).format(date);
  } catch (error) {
    console.log('[dateFormat] Error formatting date:', error.message);
    return '-';
  }
}
