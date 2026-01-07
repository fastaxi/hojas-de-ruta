/**
 * RutasFast - Registration Page (Multi-step form)
 */
import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Switch } from '../../components/ui/switch';
import { AlertCircle, Loader2, ArrowLeft, ArrowRight, Check, Plus, Trash2 } from 'lucide-react';

export function RegisterPage() {
  const [step, setStep] = useState(1);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  // Form data
  const [formData, setFormData] = useState({
    full_name: '',
    dni_cif: '',
    license_number: '',
    license_council: '',
    phone: '',
    email: '',
    password: '',
    confirmPassword: '',
    vehicle_brand: '',
    vehicle_model: '',
    vehicle_plate: '',
    hasDrivers: false,
    drivers: []
  });

  const updateField = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const addDriver = () => {
    setFormData(prev => ({
      ...prev,
      drivers: [...prev.drivers, { full_name: '', dni: '' }]
    }));
  };

  const updateDriver = (index, field, value) => {
    setFormData(prev => ({
      ...prev,
      drivers: prev.drivers.map((d, i) => i === index ? { ...d, [field]: value } : d)
    }));
  };

  const removeDriver = (index) => {
    setFormData(prev => ({
      ...prev,
      drivers: prev.drivers.filter((_, i) => i !== index)
    }));
  };

  const validateStep = (stepNum) => {
    switch (stepNum) {
      case 1:
        if (!formData.full_name || !formData.dni_cif || !formData.phone || !formData.email) {
          setError('Completa todos los campos obligatorios');
          return false;
        }
        if (!formData.email.includes('@')) {
          setError('Email inválido');
          return false;
        }
        break;
      case 2:
        if (!formData.license_number || !formData.license_council) {
          setError('Completa los datos de la licencia');
          return false;
        }
        break;
      case 3:
        if (!formData.vehicle_brand || !formData.vehicle_model || !formData.vehicle_plate) {
          setError('Completa los datos del vehículo');
          return false;
        }
        break;
      case 4:
        if (!formData.password || formData.password.length < 6) {
          setError('La contraseña debe tener al menos 6 caracteres');
          return false;
        }
        if (formData.password !== formData.confirmPassword) {
          setError('Las contraseñas no coinciden');
          return false;
        }
        break;
      default:
        break;
    }
    setError('');
    return true;
  };

  const nextStep = () => {
    if (validateStep(step)) {
      setStep(prev => prev + 1);
    }
  };

  const prevStep = () => {
    setError('');
    setStep(prev => prev - 1);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validateStep(4)) return;

    setLoading(true);
    setError('');

    try {
      const submitData = {
        full_name: formData.full_name,
        dni_cif: formData.dni_cif,
        license_number: formData.license_number,
        license_council: formData.license_council,
        phone: formData.phone,
        email: formData.email,
        password: formData.password,
        vehicle_brand: formData.vehicle_brand,
        vehicle_model: formData.vehicle_model,
        vehicle_plate: formData.vehicle_plate,
        drivers: formData.hasDrivers ? formData.drivers : []
      };

      await register(submitData);
      setSuccess(true);
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al registrar');
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="min-h-screen bg-stone-100 flex items-center justify-center p-4">
        <Card className="w-full max-w-md border-0 shadow-xl">
          <CardContent className="pt-8 pb-8 text-center">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <Check className="w-8 h-8 text-green-600" />
            </div>
            <h2 className="text-2xl font-bold text-stone-900 mb-3" style={{ fontFamily: 'Chivo, sans-serif' }}>
              Solicitud Enviada
            </h2>
            <p className="text-stone-600 mb-6">
              Tu registro está pendiente de verificación por el administrador. Te notificaremos por email cuando sea aprobado.
            </p>
            <Link to="/app/login">
              <Button className="rounded-full bg-maroon-900 hover:bg-maroon-800">
                Volver al Login
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  const steps = ['Datos Personales', 'Licencia', 'Vehículo', 'Contraseña'];

  return (
    <div className="min-h-screen bg-stone-100 py-8 px-4">
      <div className="max-w-md mx-auto">
        {/* Back link */}
        <Link 
          to="/" 
          className="inline-flex items-center gap-2 text-stone-600 hover:text-stone-900 mb-6"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Volver</span>
        </Link>

        {/* Progress */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            {steps.map((s, i) => (
              <div 
                key={i}
                className={`flex items-center justify-center w-8 h-8 rounded-full text-sm font-medium ${
                  i + 1 < step 
                    ? 'bg-green-500 text-white' 
                    : i + 1 === step 
                      ? 'bg-maroon-900 text-white' 
                      : 'bg-stone-200 text-stone-500'
                }`}
              >
                {i + 1 < step ? <Check className="w-4 h-4" /> : i + 1}
              </div>
            ))}
          </div>
          <div className="flex gap-1">
            {steps.map((_, i) => (
              <div 
                key={i}
                className={`h-1 flex-1 rounded ${
                  i + 1 <= step ? 'bg-maroon-900' : 'bg-stone-200'
                }`}
              />
            ))}
          </div>
        </div>

        <Card className="border-0 shadow-xl">
          <CardHeader className="pb-2">
            <div className="text-center mb-2">
              <span className="text-2xl font-black text-maroon-900" style={{ fontFamily: 'Chivo, sans-serif' }}>
                FAST
              </span>
            </div>
            <CardTitle style={{ fontFamily: 'Chivo, sans-serif' }}>
              {steps[step - 1]}
            </CardTitle>
            <CardDescription>
              Paso {step} de {steps.length}
            </CardDescription>
          </CardHeader>

          <CardContent>
            <form onSubmit={handleSubmit}>
              {error && (
                <div className="flex items-start gap-3 p-4 mb-5 bg-red-50 border border-red-200 rounded-lg text-red-800">
                  <AlertCircle className="w-5 h-5 mt-0.5 flex-shrink-0" />
                  <p className="text-sm">{error}</p>
                </div>
              )}

              {/* Step 1: Personal Data */}
              {step === 1 && (
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label className="text-stone-600 font-medium text-sm uppercase tracking-wide">
                      Nombre y Apellidos *
                    </Label>
                    <Input
                      value={formData.full_name}
                      onChange={(e) => updateField('full_name', e.target.value)}
                      placeholder="Juan García López"
                      className="h-14 text-lg"
                      data-testid="register-fullname"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label className="text-stone-600 font-medium text-sm uppercase tracking-wide">
                      DNI/CIF *
                    </Label>
                    <Input
                      value={formData.dni_cif}
                      onChange={(e) => updateField('dni_cif', e.target.value)}
                      placeholder="12345678A"
                      className="h-14 text-lg"
                      data-testid="register-dni"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label className="text-stone-600 font-medium text-sm uppercase tracking-wide">
                      Teléfono *
                    </Label>
                    <Input
                      value={formData.phone}
                      onChange={(e) => updateField('phone', e.target.value)}
                      placeholder="612345678"
                      type="tel"
                      className="h-14 text-lg"
                      data-testid="register-phone"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label className="text-stone-600 font-medium text-sm uppercase tracking-wide">
                      Email *
                    </Label>
                    <Input
                      value={formData.email}
                      onChange={(e) => updateField('email', e.target.value)}
                      placeholder="tu@email.com"
                      type="email"
                      className="h-14 text-lg"
                      data-testid="register-email"
                    />
                  </div>
                </div>
              )}

              {/* Step 2: License */}
              {step === 2 && (
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label className="text-stone-600 font-medium text-sm uppercase tracking-wide">
                      Número de Licencia *
                    </Label>
                    <Input
                      value={formData.license_number}
                      onChange={(e) => updateField('license_number', e.target.value)}
                      placeholder="L-12345"
                      className="h-14 text-lg"
                      data-testid="register-license"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label className="text-stone-600 font-medium text-sm uppercase tracking-wide">
                      Concejo *
                    </Label>
                    <Input
                      value={formData.license_council}
                      onChange={(e) => updateField('license_council', e.target.value)}
                      placeholder="Oviedo"
                      className="h-14 text-lg"
                      data-testid="register-council"
                    />
                  </div>
                  
                  {/* Drivers toggle */}
                  <div className="pt-4 border-t border-stone-200">
                    <div className="flex items-center justify-between">
                      <Label className="text-stone-700">¿Tienes choferes?</Label>
                      <Switch
                        checked={formData.hasDrivers}
                        onCheckedChange={(checked) => {
                          updateField('hasDrivers', checked);
                          if (checked && formData.drivers.length === 0) {
                            addDriver();
                          }
                        }}
                        data-testid="register-has-drivers"
                      />
                    </div>

                    {formData.hasDrivers && (
                      <div className="mt-4 space-y-4">
                        {formData.drivers.map((driver, index) => (
                          <div key={index} className="p-4 bg-stone-50 rounded-lg space-y-3">
                            <div className="flex items-center justify-between">
                              <span className="text-sm font-medium text-stone-600">
                                Chofer {index + 1}
                              </span>
                              <button
                                type="button"
                                onClick={() => removeDriver(index)}
                                className="text-red-500 hover:text-red-700"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </div>
                            <Input
                              value={driver.full_name}
                              onChange={(e) => updateDriver(index, 'full_name', e.target.value)}
                              placeholder="Nombre y apellidos"
                              className="h-12"
                            />
                            <Input
                              value={driver.dni}
                              onChange={(e) => updateDriver(index, 'dni', e.target.value)}
                              placeholder="DNI"
                              className="h-12"
                            />
                          </div>
                        ))}
                        <Button
                          type="button"
                          variant="outline"
                          onClick={addDriver}
                          className="w-full"
                        >
                          <Plus className="w-4 h-4 mr-2" />
                          Añadir chofer
                        </Button>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Step 3: Vehicle */}
              {step === 3 && (
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label className="text-stone-600 font-medium text-sm uppercase tracking-wide">
                      Marca *
                    </Label>
                    <Input
                      value={formData.vehicle_brand}
                      onChange={(e) => updateField('vehicle_brand', e.target.value)}
                      placeholder="Toyota"
                      className="h-14 text-lg"
                      data-testid="register-vehicle-brand"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label className="text-stone-600 font-medium text-sm uppercase tracking-wide">
                      Modelo *
                    </Label>
                    <Input
                      value={formData.vehicle_model}
                      onChange={(e) => updateField('vehicle_model', e.target.value)}
                      placeholder="Prius"
                      className="h-14 text-lg"
                      data-testid="register-vehicle-model"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label className="text-stone-600 font-medium text-sm uppercase tracking-wide">
                      Matrícula *
                    </Label>
                    <Input
                      value={formData.vehicle_plate}
                      onChange={(e) => updateField('vehicle_plate', e.target.value)}
                      placeholder="1234 ABC"
                      className="h-14 text-lg"
                      data-testid="register-vehicle-plate"
                    />
                  </div>
                </div>
              )}

              {/* Step 4: Password */}
              {step === 4 && (
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label className="text-stone-600 font-medium text-sm uppercase tracking-wide">
                      Contraseña *
                    </Label>
                    <Input
                      type="password"
                      value={formData.password}
                      onChange={(e) => updateField('password', e.target.value)}
                      placeholder="Mínimo 6 caracteres"
                      className="h-14 text-lg"
                      data-testid="register-password"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label className="text-stone-600 font-medium text-sm uppercase tracking-wide">
                      Confirmar Contraseña *
                    </Label>
                    <Input
                      type="password"
                      value={formData.confirmPassword}
                      onChange={(e) => updateField('confirmPassword', e.target.value)}
                      placeholder="Repite la contraseña"
                      className="h-14 text-lg"
                      data-testid="register-confirm-password"
                    />
                  </div>
                </div>
              )}

              {/* Navigation buttons */}
              <div className="flex gap-3 mt-6">
                {step > 1 && (
                  <Button
                    type="button"
                    variant="outline"
                    onClick={prevStep}
                    className="flex-1 h-12 rounded-full"
                  >
                    <ArrowLeft className="w-4 h-4 mr-2" />
                    Anterior
                  </Button>
                )}
                
                {step < 4 ? (
                  <Button
                    type="button"
                    onClick={nextStep}
                    className="flex-1 h-12 rounded-full bg-maroon-900 hover:bg-maroon-800"
                    data-testid="register-next"
                  >
                    Siguiente
                    <ArrowRight className="w-4 h-4 ml-2" />
                  </Button>
                ) : (
                  <Button
                    type="submit"
                    disabled={loading}
                    className="flex-1 h-12 rounded-full bg-maroon-900 hover:bg-maroon-800"
                    data-testid="register-submit"
                  >
                    {loading ? (
                      <>
                        <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                        Registrando...
                      </>
                    ) : (
                      'Completar Registro'
                    )}
                  </Button>
                )}
              </div>
            </form>

            <p className="text-sm text-stone-500 text-center mt-6">
              ¿Ya tienes cuenta?{' '}
              <Link to="/app/login" className="text-maroon-900 font-medium hover:underline">
                Inicia sesión
              </Link>
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
