/**
 * RutasFast - Configuración Page (User settings)
 */
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../../contexts/AuthContext';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import { 
  User, Car, Users, Loader2, Check, Plus, Trash2, Save, AlertCircle
} from 'lucide-react';

const API_URL = `${process.env.REACT_APP_BACKEND_URL}/api`;

export function ConfiguracionPage() {
  const { user, updateProfile } = useAuth();
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState('');
  const [error, setError] = useState('');

  // Profile form
  const [profileData, setProfileData] = useState({
    full_name: '',
    dni_cif: '',
    license_number: '',
    license_council: '',
    phone: ''
  });

  // Vehicle form
  const [vehicleData, setVehicleData] = useState({
    vehicle_brand: '',
    vehicle_model: '',
    vehicle_plate: ''
  });

  // Drivers
  const [drivers, setDrivers] = useState([]);
  const [newDriver, setNewDriver] = useState({ full_name: '', dni: '' });

  useEffect(() => {
    if (user) {
      setProfileData({
        full_name: user.full_name || '',
        dni_cif: user.dni_cif || '',
        license_number: user.license_number || '',
        license_council: user.license_council || '',
        phone: user.phone || ''
      });
      setVehicleData({
        vehicle_brand: user.vehicle_brand || '',
        vehicle_model: user.vehicle_model || '',
        vehicle_plate: user.vehicle_plate || ''
      });
    }
    fetchDrivers();
  }, [user]);

  const fetchDrivers = async () => {
    try {
      const response = await axios.get(`${API_URL}/me/drivers`);
      setDrivers(response.data);
    } catch (err) {
      console.error('Error fetching drivers:', err);
    }
  };

  const handleProfileUpdate = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccess('');

    try {
      await updateProfile(profileData);
      setSuccess('Perfil actualizado');
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al actualizar');
    } finally {
      setLoading(false);
    }
  };

  const handleVehicleUpdate = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccess('');

    try {
      await updateProfile(vehicleData);
      setSuccess('Vehículo actualizado');
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al actualizar');
    } finally {
      setLoading(false);
    }
  };

  const handleAddDriver = async (e) => {
    e.preventDefault();
    if (!newDriver.full_name || !newDriver.dni) return;

    try {
      await axios.post(`${API_URL}/me/drivers`, newDriver);
      setNewDriver({ full_name: '', dni: '' });
      fetchDrivers();
      setSuccess('Chofer añadido');
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al añadir chofer');
    }
  };

  const handleDeleteDriver = async (driverId) => {
    if (!window.confirm('¿Eliminar este chofer?')) return;

    try {
      await axios.delete(`${API_URL}/me/drivers/${driverId}`);
      fetchDrivers();
      setSuccess('Chofer eliminado');
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al eliminar');
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-stone-900" style={{ fontFamily: 'Chivo, sans-serif' }}>
          Configuración
        </h1>
        <p className="text-stone-600">Gestiona tu perfil y vehículo</p>
      </div>

      {/* Messages */}
      {success && (
        <div className="flex items-center gap-2 p-4 bg-green-50 border border-green-200 rounded-lg text-green-800">
          <Check className="w-5 h-5" />
          <p className="text-sm">{success}</p>
        </div>
      )}
      {error && (
        <div className="flex items-center gap-2 p-4 bg-red-50 border border-red-200 rounded-lg text-red-800">
          <AlertCircle className="w-5 h-5" />
          <p className="text-sm">{error}</p>
        </div>
      )}

      <Tabs defaultValue="perfil" className="w-full">
        <TabsList className="grid w-full grid-cols-3 h-12">
          <TabsTrigger value="perfil" className="data-[state=active]:bg-maroon-900 data-[state=active]:text-white">
            <User className="w-4 h-4 mr-2" />
            Perfil
          </TabsTrigger>
          <TabsTrigger value="vehiculo" className="data-[state=active]:bg-maroon-900 data-[state=active]:text-white">
            <Car className="w-4 h-4 mr-2" />
            Vehículo
          </TabsTrigger>
          <TabsTrigger value="choferes" className="data-[state=active]:bg-maroon-900 data-[state=active]:text-white">
            <Users className="w-4 h-4 mr-2" />
            Choferes
          </TabsTrigger>
        </TabsList>

        {/* Profile Tab */}
        <TabsContent value="perfil">
          <Card className="border-0 shadow-lg">
            <CardContent className="pt-6">
              <form onSubmit={handleProfileUpdate} className="space-y-4">
                <div className="space-y-2">
                  <Label className="text-stone-600 font-medium text-sm uppercase tracking-wide">
                    Nombre y Apellidos
                  </Label>
                  <Input
                    value={profileData.full_name}
                    onChange={(e) => setProfileData(prev => ({ ...prev, full_name: e.target.value }))}
                    className="h-12"
                    data-testid="config-fullname"
                  />
                </div>
                <div className="space-y-2">
                  <Label className="text-stone-600 font-medium text-sm uppercase tracking-wide">
                    DNI/CIF
                  </Label>
                  <Input
                    value={profileData.dni_cif}
                    onChange={(e) => setProfileData(prev => ({ ...prev, dni_cif: e.target.value }))}
                    className="h-12"
                    data-testid="config-dni"
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label className="text-stone-600 font-medium text-sm uppercase tracking-wide">
                      Nº Licencia
                    </Label>
                    <Input
                      value={profileData.license_number}
                      onChange={(e) => setProfileData(prev => ({ ...prev, license_number: e.target.value }))}
                      className="h-12"
                      data-testid="config-license"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label className="text-stone-600 font-medium text-sm uppercase tracking-wide">
                      Concejo
                    </Label>
                    <Input
                      value={profileData.license_council}
                      onChange={(e) => setProfileData(prev => ({ ...prev, license_council: e.target.value }))}
                      className="h-12"
                      data-testid="config-council"
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label className="text-stone-600 font-medium text-sm uppercase tracking-wide">
                    Teléfono
                  </Label>
                  <Input
                    value={profileData.phone}
                    onChange={(e) => setProfileData(prev => ({ ...prev, phone: e.target.value }))}
                    className="h-12"
                    data-testid="config-phone"
                  />
                </div>
                <Button
                  type="submit"
                  disabled={loading}
                  className="w-full h-12 rounded-full bg-maroon-900 hover:bg-maroon-800"
                  data-testid="save-profile-btn"
                >
                  {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <><Save className="w-4 h-4 mr-2" /> Guardar Perfil</>}
                </Button>
              </form>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Vehicle Tab */}
        <TabsContent value="vehiculo">
          <Card className="border-0 shadow-lg">
            <CardContent className="pt-6">
              <form onSubmit={handleVehicleUpdate} className="space-y-4">
                <div className="space-y-2">
                  <Label className="text-stone-600 font-medium text-sm uppercase tracking-wide">
                    Marca
                  </Label>
                  <Input
                    value={vehicleData.vehicle_brand}
                    onChange={(e) => setVehicleData(prev => ({ ...prev, vehicle_brand: e.target.value }))}
                    className="h-12"
                    data-testid="config-vehicle-brand"
                  />
                </div>
                <div className="space-y-2">
                  <Label className="text-stone-600 font-medium text-sm uppercase tracking-wide">
                    Modelo
                  </Label>
                  <Input
                    value={vehicleData.vehicle_model}
                    onChange={(e) => setVehicleData(prev => ({ ...prev, vehicle_model: e.target.value }))}
                    className="h-12"
                    data-testid="config-vehicle-model"
                  />
                </div>
                <div className="space-y-2">
                  <Label className="text-stone-600 font-medium text-sm uppercase tracking-wide">
                    Matrícula
                  </Label>
                  <Input
                    value={vehicleData.vehicle_plate}
                    onChange={(e) => setVehicleData(prev => ({ ...prev, vehicle_plate: e.target.value }))}
                    className="h-12"
                    data-testid="config-vehicle-plate"
                  />
                </div>
                <Button
                  type="submit"
                  disabled={loading}
                  className="w-full h-12 rounded-full bg-maroon-900 hover:bg-maroon-800"
                  data-testid="save-vehicle-btn"
                >
                  {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <><Save className="w-4 h-4 mr-2" /> Guardar Vehículo</>}
                </Button>
              </form>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Drivers Tab */}
        <TabsContent value="choferes">
          <Card className="border-0 shadow-lg">
            <CardHeader>
              <CardTitle className="text-lg">Mis Choferes</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Driver list */}
              {drivers.length === 0 ? (
                <p className="text-stone-500 text-center py-4">No tienes choferes registrados</p>
              ) : (
                <div className="space-y-2">
                  {drivers.map((driver) => (
                    <div 
                      key={driver.id}
                      className="flex items-center justify-between p-3 bg-stone-50 rounded-lg"
                    >
                      <div>
                        <p className="font-medium text-stone-900">{driver.full_name}</p>
                        <p className="text-sm text-stone-500">DNI: {driver.dni}</p>
                      </div>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleDeleteDriver(driver.id)}
                        className="text-red-500 hover:text-red-700 hover:bg-red-50"
                        data-testid={`delete-driver-${driver.id}`}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              )}

              {/* Add new driver */}
              <form onSubmit={handleAddDriver} className="pt-4 border-t border-stone-200 space-y-3">
                <p className="text-sm font-medium text-stone-700">Añadir nuevo chofer</p>
                <div className="grid grid-cols-2 gap-3">
                  <Input
                    value={newDriver.full_name}
                    onChange={(e) => setNewDriver(prev => ({ ...prev, full_name: e.target.value }))}
                    placeholder="Nombre y apellidos"
                    className="h-11"
                    data-testid="new-driver-name"
                  />
                  <Input
                    value={newDriver.dni}
                    onChange={(e) => setNewDriver(prev => ({ ...prev, dni: e.target.value }))}
                    placeholder="DNI"
                    className="h-11"
                    data-testid="new-driver-dni"
                  />
                </div>
                <Button
                  type="submit"
                  variant="outline"
                  className="w-full h-11 border-maroon-900 text-maroon-900 hover:bg-maroon-50"
                  data-testid="add-driver-btn"
                >
                  <Plus className="w-4 h-4 mr-2" />
                  Añadir Chofer
                </Button>
              </form>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
