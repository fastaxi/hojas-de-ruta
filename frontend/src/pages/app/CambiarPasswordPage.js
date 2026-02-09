/**
 * RutasFast - Cambiar Contraseña Page
 * Forced password change after temp password login
 */
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Loader2, Lock, AlertCircle, Check } from 'lucide-react';
import { PasswordInput } from '../../components/ui/password-input';

export function CambiarPasswordPage() {
  const { changePassword, user, logout } = useAuth();
  const navigate = useNavigate();
  
  const [formData, setFormData] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const validatePassword = (password) => {
    if (password.length < 8) {
      return 'La contraseña debe tener al menos 8 caracteres';
    }
    if (!/[A-Z]/.test(password)) {
      return 'La contraseña debe tener al menos una mayúscula';
    }
    if (!/[0-9]/.test(password)) {
      return 'La contraseña debe tener al menos un número';
    }
    return null;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    // Validations
    if (!formData.currentPassword) {
      setError('Ingresa tu contraseña actual');
      return;
    }

    const passwordError = validatePassword(formData.newPassword);
    if (passwordError) {
      setError(passwordError);
      return;
    }

    if (formData.newPassword !== formData.confirmPassword) {
      setError('Las contraseñas no coinciden');
      return;
    }

    if (formData.currentPassword === formData.newPassword) {
      setError('La nueva contraseña debe ser diferente a la actual');
      return;
    }

    setLoading(true);

    try {
      await changePassword(formData.currentPassword, formData.newPassword);
      setSuccess(true);
      
      // Redirect after success
      setTimeout(() => {
        navigate('/app/nueva-hoja');
      }, 2000);
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(detail || 'Error al cambiar la contraseña');
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-stone-100 to-stone-200 flex items-center justify-center p-4">
        <Card className="w-full max-w-md border-0 shadow-xl">
          <CardContent className="pt-8 pb-8 text-center">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <Check className="w-8 h-8 text-green-600" />
            </div>
            <h2 className="text-xl font-bold text-stone-900 mb-2">
              ¡Contraseña actualizada!
            </h2>
            <p className="text-stone-600">
              Redirigiendo a la aplicación...
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-stone-100 to-stone-200 flex items-center justify-center p-4">
      <Card className="w-full max-w-md border-0 shadow-xl">
        <CardHeader className="text-center pb-2">
          <div className="w-16 h-16 bg-amber-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <Lock className="w-8 h-8 text-amber-600" />
          </div>
          <CardTitle className="text-2xl font-bold text-stone-900">
            Cambiar Contraseña
          </CardTitle>
          <CardDescription className="text-stone-600">
            Tu contraseña temporal ha sido configurada.<br />
            Debes crear una nueva contraseña para continuar.
          </CardDescription>
        </CardHeader>
        
        <CardContent>
          {error && (
            <div className="flex items-center gap-2 p-3 mb-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
              <AlertCircle className="w-5 h-5 flex-shrink-0" />
              <p className="text-sm">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label className="text-stone-600 font-medium">
                Contraseña Actual (temporal)
              </Label>
              <PasswordInput
                value={formData.currentPassword}
                onChange={(e) => setFormData({ ...formData, currentPassword: e.target.value })}
                placeholder="Contraseña que te proporcionaron"
                className="h-12"
                data-testid="current-password"
              />
            </div>

            <div className="space-y-2">
              <Label className="text-stone-600 font-medium">
                Nueva Contraseña
              </Label>
              <PasswordInput
                value={formData.newPassword}
                onChange={(e) => setFormData({ ...formData, newPassword: e.target.value })}
                placeholder="Mínimo 8 caracteres"
                className="h-12"
                data-testid="new-password"
              />
              <p className="text-xs text-stone-500">
                Debe incluir: 8+ caracteres, una mayúscula, un número
              </p>
            </div>

            <div className="space-y-2">
              <Label className="text-stone-600 font-medium">
                Confirmar Nueva Contraseña
              </Label>
              <PasswordInput
                value={formData.confirmPassword}
                onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
                placeholder="Repite la nueva contraseña"
                className="h-12"
                data-testid="confirm-password"
              />
            </div>

            <Button
              type="submit"
              disabled={loading}
              className="w-full h-12 rounded-full bg-maroon-900 hover:bg-maroon-800"
              data-testid="change-password-submit"
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                  Cambiando...
                </>
              ) : (
                'Cambiar Contraseña'
              )}
            </Button>
          </form>

          <div className="mt-4 text-center">
            <button
              onClick={logout}
              className="text-sm text-stone-500 hover:text-stone-700"
            >
              Cancelar y cerrar sesión
            </button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
