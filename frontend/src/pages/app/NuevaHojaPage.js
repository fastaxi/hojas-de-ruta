/**
 * RutasFast - Nueva Hoja de Ruta Page
 */
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../../contexts/AuthContext';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { RadioGroup, RadioGroupItem } from '../../components/ui/radio-group';
import { AlertCircle, Loader2, Check, Plane, MapPin, Truck } from 'lucide-react';

const API_URL = `${process.env.REACT_APP_BACKEND_URL}/api`;

export function NuevaHojaPage() {
  const { user } = useAuth();
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(null);
  const [error, setError] = useState('');
  const [drivers, setDrivers] = useState([]);
  const [assistanceCompanies, setAssistanceCompanies] = useState([]);

  const [formData, setFormData] = useState({
    conductor_driver_id: 'titular',
    contractor_phone: '',
    contractor_email: '',
    prebooked_date: new Date().toISOString().split('T')[0],
    prebooked_locality: '',
    pickup_type: 'OTHER',
    flight_number: '',
    pickup_address: '',
    pickup_datetime: '',
    destination: '',
    passenger_info: '',
    assistance_company_id: ''
  });

  useEffect(() => {
    fetchDrivers();
    fetchAssistanceCompanies();
  }, []);

  const fetchDrivers = async () => {
    try {
      const response = await axios.get(`${API_URL}/me/drivers`);
      setDrivers(response.data);
    } catch (err) {
      console.error('Error fetching drivers:', err);
    }
  };

  const fetchAssistanceCompanies = async () => {
    try {
      const response = await axios.get(`${API_URL}/me/assistance-companies`);
      setAssistanceCompanies(response.data);
    } catch (err) {
      console.error('Error fetching assistance companies:', err);
    }
  };

  const updateField = (field, value) => {
    setFormData(prev => {
      const updated = { ...prev, [field]: value };
      // Auto-fill pickup_address when AIRPORT is selected
      if (field === 'pickup_type') {
        if (value === 'AIRPORT') {
          updated.pickup_address = 'Aeropuerto de Asturias';
          updated.flight_number = prev.flight_number || '';
          updated.assistance_company_id = '';
        } else if (value === 'ROADSIDE') {
          updated.pickup_address = '';
          updated.flight_number = '';
        } else {
          updated.pickup_address = '';
          updated.flight_number = '';
          updated.assistance_company_id = '';
        }
      }
      return updated;
    });
    setError('');
  };

  const validateForm = () => {
    if (!formData.contractor_phone && !formData.contractor_email) {
      setError('Debe proporcionar teléfono o email del contratante');
      return false;
    }
    if (!formData.prebooked_locality) {
      setError('La localidad de precontratación es obligatoria');
      return false;
    }
    if (!formData.pickup_datetime) {
      setError('La fecha/hora de recogida es obligatoria');
      return false;
    }
    if (!formData.destination) {
      setError('El destino es obligatorio');
      return false;
    }
    if (!formData.passenger_info) {
      setError('Los datos del pasajero son obligatorios');
      return false;
    }
    if (formData.pickup_type === 'AIRPORT') {
      if (!formData.flight_number) {
        setError('El número de vuelo es obligatorio para recogida en aeropuerto');
        return false;
      }
      const flightRegex = /^[A-Z]{2}\d{3,4}$/;
      if (!flightRegex.test(formData.flight_number)) {
        setError('Formato de vuelo inválido. Ejemplo: VY1234');
        return false;
      }
    }
    if (formData.pickup_type === 'OTHER' || formData.pickup_type === 'ROADSIDE') {
      if (!formData.pickup_address) {
        setError('La dirección/ubicación de recogida es obligatoria');
        return false;
      }
    }
    if (formData.pickup_type === 'ROADSIDE') {
      if (!formData.assistance_company_id) {
        setError('Debe seleccionar una empresa de asistencia');
        return false;
      }
    }
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validateForm()) return;

    setLoading(true);
    setError('');

    try {
      // Clean up empty strings to null for optional fields
      const submitData = {
        contractor_phone: formData.contractor_phone || null,
        contractor_email: formData.contractor_email || null,
        prebooked_date: formData.prebooked_date,
        prebooked_locality: formData.prebooked_locality,
        pickup_type: formData.pickup_type,
        flight_number: formData.pickup_type === 'AIRPORT' ? formData.flight_number : null,
        pickup_address: formData.pickup_address || null,
        pickup_datetime: formData.pickup_datetime,
        destination: formData.destination,
        passenger_info: formData.passenger_info,
        conductor_driver_id: formData.conductor_driver_id === 'titular' ? null : formData.conductor_driver_id,
        assistance_company_id: formData.pickup_type === 'ROADSIDE' ? formData.assistance_company_id : null
      };

      const response = await axios.post(`${API_URL}/route-sheets`, submitData);
      setSuccess(response.data);
      
      // Reset form
      setFormData({
        conductor_driver_id: 'titular',
        contractor_phone: '',
        contractor_email: '',
        prebooked_date: new Date().toISOString().split('T')[0],
        prebooked_locality: '',
        pickup_type: 'OTHER',
        flight_number: '',
        pickup_address: '',
        pickup_datetime: '',
        destination: '',
        passenger_info: ''
      });
    } catch (err) {
      // Handle validation errors from backend
      const errorDetail = err.response?.data?.detail;
      if (Array.isArray(errorDetail)) {
        // Pydantic validation error
        const messages = errorDetail.map(e => e.msg).join(', ');
        setError(messages);
      } else {
        setError(errorDetail || 'Error al crear la hoja');
      }
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <Card className="border-0 shadow-lg">
        <CardContent className="pt-8 pb-8 text-center">
          <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
            <Check className="w-8 h-8 text-green-600" />
          </div>
          <h2 className="text-2xl font-bold text-stone-900 mb-2" style={{ fontFamily: 'Chivo, sans-serif' }}>
            Hoja Creada
          </h2>
          <p className="text-3xl font-black text-maroon-900 mb-4" style={{ fontFamily: 'Chivo, sans-serif' }}>
            {success.sheet_number}
          </p>
          <p className="text-stone-600 mb-6">
            La hoja de ruta se ha guardado correctamente.
          </p>
          <Button 
            onClick={() => setSuccess(null)}
            className="rounded-full bg-maroon-900 hover:bg-maroon-800"
            data-testid="create-another-btn"
          >
            Crear otra hoja
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-stone-900" style={{ fontFamily: 'Chivo, sans-serif' }}>
          Nueva Hoja de Ruta
        </h1>
        <p className="text-stone-600">Completa los datos del servicio</p>
      </div>

      <Card className="border-0 shadow-lg">
        <CardContent className="pt-6">
          <form onSubmit={handleSubmit} className="space-y-6">
            {error && (
              <div className="flex items-start gap-3 p-4 bg-red-50 border border-red-200 rounded-lg text-red-800">
                <AlertCircle className="w-5 h-5 mt-0.5 flex-shrink-0" />
                <p className="text-sm">{error}</p>
              </div>
            )}

            {/* Conductor */}
            <div className="space-y-2">
              <Label className="text-stone-600 font-medium text-sm uppercase tracking-wide">
                Conductor
              </Label>
              <Select 
                value={formData.conductor_driver_id} 
                onValueChange={(v) => updateField('conductor_driver_id', v)}
              >
                <SelectTrigger className="h-14 text-lg" data-testid="select-conductor">
                  <SelectValue placeholder="Selecciona conductor" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="titular">Titular ({user?.full_name})</SelectItem>
                  {drivers.map(driver => (
                    <SelectItem key={driver.id} value={driver.id}>
                      {driver.full_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Contratante */}
            <div className="space-y-4">
              <Label className="text-stone-700 font-semibold">
                Datos del Contratante
              </Label>
              <p className="text-sm text-stone-500 -mt-2">
                Teléfono o email obligatorio
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label className="text-stone-600 font-medium text-sm uppercase tracking-wide">
                    Teléfono
                  </Label>
                  <Input
                    type="tel"
                    value={formData.contractor_phone}
                    onChange={(e) => updateField('contractor_phone', e.target.value)}
                    placeholder="612345678"
                    className="h-14 text-lg"
                    data-testid="contractor-phone"
                  />
                </div>
                <div className="space-y-2">
                  <Label className="text-stone-600 font-medium text-sm uppercase tracking-wide">
                    Email
                  </Label>
                  <Input
                    type="email"
                    value={formData.contractor_email}
                    onChange={(e) => updateField('contractor_email', e.target.value)}
                    placeholder="email@ejemplo.com"
                    className="h-14 text-lg"
                    data-testid="contractor-email"
                  />
                </div>
              </div>
            </div>

            {/* Precontratación */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label className="text-stone-600 font-medium text-sm uppercase tracking-wide">
                  Fecha Precontratación *
                </Label>
                <Input
                  type="date"
                  value={formData.prebooked_date}
                  onChange={(e) => updateField('prebooked_date', e.target.value)}
                  className="h-14 text-lg"
                  data-testid="prebooked-date"
                />
              </div>
              <div className="space-y-2">
                <Label className="text-stone-600 font-medium text-sm uppercase tracking-wide">
                  Localidad *
                </Label>
                <Input
                  value={formData.prebooked_locality}
                  onChange={(e) => updateField('prebooked_locality', e.target.value)}
                  placeholder="Oviedo"
                  className="h-14 text-lg"
                  data-testid="prebooked-locality"
                />
              </div>
            </div>

            {/* Tipo de recogida */}
            <div className="space-y-3">
              <Label className="text-stone-600 font-medium text-sm uppercase tracking-wide">
                Lugar de Recogida *
              </Label>
              <RadioGroup
                value={formData.pickup_type}
                onValueChange={(v) => updateField('pickup_type', v)}
                className="flex gap-4"
              >
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="AIRPORT" id="airport" data-testid="pickup-airport" />
                  <Label htmlFor="airport" className="flex items-center gap-2 cursor-pointer">
                    <Plane className="w-4 h-4" />
                    Aeropuerto de Asturias
                  </Label>
                </div>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="OTHER" id="other" data-testid="pickup-other" />
                  <Label htmlFor="other" className="flex items-center gap-2 cursor-pointer">
                    <MapPin className="w-4 h-4" />
                    Otra dirección
                  </Label>
                </div>
              </RadioGroup>
            </div>

            {/* Número de vuelo (solo aeropuerto) */}
            {formData.pickup_type === 'AIRPORT' && (
              <div className="space-y-2">
                <Label className="text-stone-600 font-medium text-sm uppercase tracking-wide">
                  Número de Vuelo * (Formato: VY1234)
                </Label>
                <Input
                  value={formData.flight_number}
                  onChange={(e) => updateField('flight_number', e.target.value.toUpperCase())}
                  placeholder="VY1234"
                  className="h-14 text-lg font-mono"
                  maxLength={6}
                  data-testid="flight-number"
                />
              </div>
            )}

            {/* Dirección de recogida (solo si no es aeropuerto) */}
            {formData.pickup_type === 'OTHER' && (
              <div className="space-y-2">
                <Label className="text-stone-600 font-medium text-sm uppercase tracking-wide">
                  Dirección de Recogida
                </Label>
                <Input
                  value={formData.pickup_address}
                  onChange={(e) => updateField('pickup_address', e.target.value)}
                  placeholder="Calle, número, ciudad"
                  className="h-14 text-lg"
                  data-testid="pickup-address"
                />
              </div>
            )}

            {/* Fecha/hora de recogida */}
            <div className="space-y-2">
              <Label className="text-stone-600 font-medium text-sm uppercase tracking-wide">
                Fecha y Hora de Recogida *
              </Label>
              <Input
                type="datetime-local"
                value={formData.pickup_datetime}
                onChange={(e) => updateField('pickup_datetime', e.target.value)}
                className="h-14 text-lg"
                data-testid="pickup-datetime"
              />
            </div>

            {/* Destino */}
            <div className="space-y-2">
              <Label className="text-stone-600 font-medium text-sm uppercase tracking-wide">
                Destino *
              </Label>
              <Input
                value={formData.destination}
                onChange={(e) => updateField('destination', e.target.value)}
                placeholder="Dirección de destino"
                className="h-14 text-lg"
                data-testid="destination"
              />
            </div>

            {/* Pasajero(s) */}
            <div className="space-y-2">
              <Label className="text-stone-600 font-medium text-sm uppercase tracking-wide">
                Pasajero(s) *
              </Label>
              <Input
                value={formData.passenger_info}
                onChange={(e) => updateField('passenger_info', e.target.value)}
                placeholder="Nombre y datos del pasajero o pasajeros"
                className="h-14 text-lg"
                data-testid="passenger-info"
              />
            </div>

            <Button
              type="submit"
              disabled={loading}
              className="w-full h-14 text-lg font-semibold rounded-full bg-maroon-900 hover:bg-maroon-800"
              data-testid="create-sheet-btn"
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                  Guardando...
                </>
              ) : (
                'Crear Hoja de Ruta'
              )}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
