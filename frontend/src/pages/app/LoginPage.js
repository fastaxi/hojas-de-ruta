/**
 * RutasFast - Login Page
 */
import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { AlertCircle, Loader2, ArrowLeft, Info } from 'lucide-react';

export function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const user = await login(email, password);
      
      // If user must change password, redirect to change password page
      if (user.must_change_password) {
        navigate('/app/cambiar-password');
      } else {
        navigate('/app/nueva-hoja');
      }
    } catch (err) {
      const message = err.response?.data?.detail || 'Error al iniciar sesión';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div 
      className="min-h-screen bg-cover bg-center bg-no-repeat relative flex items-center justify-center p-4"
      style={{ 
        backgroundImage: 'url(https://images.pexels.com/photos/35488746/pexels-photo-35488746.jpeg)',
      }}
    >
      <div className="absolute inset-0 bg-black/60" />
      
      <div className="relative z-10 w-full max-w-md">
        {/* Back link */}
        <Link 
          to="/" 
          className="inline-flex items-center gap-2 text-white/80 hover:text-white mb-6 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Volver</span>
        </Link>

        <Card className="border-0 shadow-2xl">
          <CardHeader className="text-center pb-2">
            <div className="mb-4">
              <span 
                className="text-3xl font-black text-maroon-900"
                style={{ fontFamily: 'Chivo, sans-serif' }}
              >
                FAST
              </span>
            </div>
            <CardTitle className="text-2xl" style={{ fontFamily: 'Chivo, sans-serif' }}>
              Iniciar Sesión
            </CardTitle>
            <CardDescription>
              Accede a tu cuenta de RutasFast
            </CardDescription>
          </CardHeader>
          
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-5">
              {error && (
                <div 
                  className="flex items-start gap-3 p-4 bg-red-50 border border-red-200 rounded-lg text-red-800"
                  data-testid="login-error"
                >
                  <AlertCircle className="w-5 h-5 mt-0.5 flex-shrink-0" />
                  <p className="text-sm">{error}</p>
                </div>
              )}

              <div className="space-y-2">
                <Label htmlFor="email" className="text-stone-600 font-medium text-sm uppercase tracking-wide">
                  Email
                </Label>
                <Input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="tu@email.com"
                  required
                  className="h-14 text-lg bg-white border-stone-300 focus:border-maroon-900 focus:ring-maroon-900"
                  data-testid="login-email"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="password" className="text-stone-600 font-medium text-sm uppercase tracking-wide">
                  Contraseña
                </Label>
                <Input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  className="h-14 text-lg bg-white border-stone-300 focus:border-maroon-900 focus:ring-maroon-900"
                  data-testid="login-password"
                />
              </div>

              <Button
                type="submit"
                disabled={loading}
                className="w-full h-14 text-lg font-semibold rounded-full bg-maroon-900 hover:bg-maroon-800"
                data-testid="login-submit"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                    Entrando...
                  </>
                ) : (
                  'Entrar'
                )}
              </Button>
            </form>

            <div className="mt-6 space-y-4">
              {/* Password recovery info - NO LINK */}
              <div className="flex items-start gap-2 p-3 bg-stone-50 border border-stone-200 rounded-lg">
                <Info className="w-4 h-4 text-stone-500 mt-0.5 flex-shrink-0" />
                <p className="text-xs text-stone-600">
                  Si olvidaste tu contraseña, contacta con la Federación para restablecerla.
                </p>
              </div>
              
              <p className="text-sm text-stone-500 text-center">
                ¿No tienes cuenta?{' '}
                <Link 
                  to="/app/registro" 
                  className="text-maroon-900 font-medium hover:underline"
                  data-testid="register-link"
                >
                  Regístrate
                </Link>
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
