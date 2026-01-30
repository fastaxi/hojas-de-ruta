/**
 * RutasFast Mobile - Validators
 * Form validation helpers matching web behavior
 */

/**
 * Check if value is non-empty after trim
 */
export const requireNonEmpty = (v) => String(v || '').trim().length > 0;

/**
 * Normalize to uppercase trimmed string
 */
export const normalizeUpper = (v) => String(v || '').trim().toUpperCase();

/**
 * Normalize to trimmed string
 */
export const normalizeTrim = (v) => String(v || '').trim();

/**
 * Normalize to trimmed string or null if empty
 */
export const normalizeTrimOrNull = (v) => {
  const trimmed = String(v || '').trim();
  return trimmed.length > 0 ? trimmed : null;
};

/**
 * Normalize to uppercase trimmed string or null if empty
 */
export const normalizeUpperOrNull = (v) => {
  const trimmed = String(v || '').trim().toUpperCase();
  return trimmed.length > 0 ? trimmed : null;
};

/**
 * Validate profile form
 */
export const validateProfile = ({ full_name, dni_cif }) => {
  if (!requireNonEmpty(full_name)) {
    return { ok: false, msg: 'El nombre es obligatorio' };
  }
  if (!requireNonEmpty(dni_cif)) {
    return { ok: false, msg: 'El DNI/CIF es obligatorio' };
  }
  return { ok: true };
};

/**
 * Validate vehicle form
 */
export const validateVehicle = ({ vehicle_plate }) => {
  if (!requireNonEmpty(vehicle_plate)) {
    return { ok: false, msg: 'La matrícula es obligatoria' };
  }
  return { ok: true };
};

/**
 * Validate driver form
 */
export const validateDriver = ({ full_name, dni }) => {
  if (!requireNonEmpty(full_name)) {
    return { ok: false, msg: 'El nombre es obligatorio' };
  }
  if (!requireNonEmpty(dni)) {
    return { ok: false, msg: 'El DNI es obligatorio' };
  }
  return { ok: true };
};

/**
 * Validate password change form
 */
export const validatePasswordChange = ({ current_password, new_password, confirm_password }) => {
  if (!requireNonEmpty(current_password)) {
    return { ok: false, msg: 'La contraseña actual es obligatoria' };
  }
  if (!requireNonEmpty(new_password)) {
    return { ok: false, msg: 'La nueva contraseña es obligatoria' };
  }
  if (new_password.length < 8) {
    return { ok: false, msg: 'La nueva contraseña debe tener al menos 8 caracteres' };
  }
  if (new_password !== confirm_password) {
    return { ok: false, msg: 'Las contraseñas no coinciden' };
  }
  return { ok: true };
};
