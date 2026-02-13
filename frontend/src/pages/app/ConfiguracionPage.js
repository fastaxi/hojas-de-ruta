/**
 * RutasFast - Configuración Page (User settings)
 * Profile, Vehicle, Drivers CRUD, Logout
 */
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../../components/ui/dialog';
import { 
  User, Car, Users, Loader2, Check, Plus, Trash2, Save, AlertCircle, 
  LogOut, Shield, Pencil, Truck
} from 'lucide-react';
import { PasswordInput } from '../../components/ui/password-input';

const API_URL = `${process.env.REACT_APP_BACKEND_URL}/api`;

export function ConfiguracionPage() {
  const { user, logout, refreshUser } = useAuth();
  const navigate = useNavigate();
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
    vehicle_plate: '',
    vehicle_license_number: ''
  });

  // Drivers
  const [drivers, setDrivers] = useState([]);
  const [loadingDrivers, setLoadingDrivers] = useState(true);
  
  // Driver dialog
  const [driverDialog, setDriverDialog] = useState(false);
  const [editingDriver, setEditingDriver] = useState(null);
  const [driverForm, setDriverForm] = useState({ full_name: '', dni: '' });
  const [savingDriver, setSavingDriver] = useState(false);
  
  // Assistance Companies
  const [assistanceCompanies, setAssistanceCompanies] = useState([]);
  const [loadingCompanies, setLoadingCompanies] = useState(true);
  const [companyDialog, setCompanyDialog] = useState(false);
  const [editingCompany, setEditingCompany] = useState(null);
  const [companyForm, setCompanyForm] = useState({ 
    name: '', 
    cif: '', 
    contact_phone: '', 
    contact_email: '' 
  });
  const [savingCompany, setSavingCompany] = useState(false);
  const [deleteCompanyConfirm, setDeleteCompanyConfirm] = useState(null);
  
  // Confirm dialogs
  const [deleteConfirm, setDeleteConfirm] = useState(null);
  const [logoutConfirm, setLogoutConfirm] = useState(false);
  
  // Password change form
  const [passwordForm, setPasswordForm] = useState({
    current_password: '',
    new_password: '',
    confirm_password: ''
  });
  const [changingPassword, setChangingPassword] = useState(false);
  const [passwordError, setPasswordError] = useState('');

  // Note: axios already has auth headers configured via AuthContext

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
        vehicle_plate: user.vehicle_plate || '',
        vehicle_license_number: user.vehicle_license_number || ''
      });
    }
    fetchDrivers();
    fetchAssistanceCompanies();
  }, [user]);

  const fetchDrivers = async () => {
    try {
      const response = await axios.get(`${API_URL}/me/drivers`);
      setDrivers(response.data);
    } catch (err) {
      console.error('Error fetching drivers:', err);
    } finally {
      setLoadingDrivers(false);
    }
  };

  const fetchAssistanceCompanies = async () => {
    try {
      const response = await axios.get(`${API_URL}/me/assistance-companies`);
      setAssistanceCompanies(response.data);
    } catch (err) {
      console.error('Error fetching assistance companies:', err);
    } finally {
      setLoadingCompanies(false);
    }
  };

  const showSuccess = (msg) => {
    setSuccess(msg);
    setError('');
    setTimeout(() => setSuccess(''), 3000);
  };

  const showError = (msg) => {
    setError(msg);
    setSuccess('');
  };

  // ============== ASSISTANCE COMPANIES ==============
  const openCompanyDialog = (company = null) => {
    if (company) {
      setEditingCompany(company);
      setCompanyForm({
        name: company.name,
        cif: company.cif,
        contact_phone: company.contact_phone || '',
        contact_email: company.contact_email || ''
      });
    } else {
      setEditingCompany(null);
      setCompanyForm({ name: '', cif: '', contact_phone: '', contact_email: '' });
    }
    setCompanyDialog(true);
  };

  const handleCompanySave = async () => {
    if (!companyForm.name.trim() || !companyForm.cif.trim()) {
      showError('Nombre y CIF son obligatorios');
      return;
    }
    if (!companyForm.contact_phone.trim() && !companyForm.contact_email.trim()) {
      showError('Teléfono o email de contacto es obligatorio');
      return;
    }

    setSavingCompany(true);
    try {
      if (editingCompany) {
        await axios.put(`${API_URL}/me/assistance-companies/${editingCompany.id}`, companyForm);
        showSuccess('Empresa actualizada');
      } else {
        await axios.post(`${API_URL}/me/assistance-companies`, companyForm);
        showSuccess('Empresa añadida');
      }
      setCompanyDialog(false);
      fetchAssistanceCompanies();
    } catch (err) {
      showError(err.response?.data?.detail || 'Error al guardar');
    } finally {
      setSavingCompany(false);
    }
  };

  const handleCompanyDelete = async (id) => {
    try {
      await axios.delete(`${API_URL}/me/assistance-companies/${id}`);
      showSuccess('Empresa eliminada');
      setDeleteCompanyConfirm(null);
      fetchAssistanceCompanies();
    } catch (err) {
      showError('Error al eliminar empresa');
    }
  };

  // ============== PROFILE ==============
  const handleProfileUpdate = async (e) => {
    e.preventDefault();
    
    // Validations
    if (!profileData.full_name.trim()) {
      showError('El nombre es obligatorio');
      return;
    }
    if (!profileData.dni_cif.trim()) {
      showError('El DNI/CIF es obligatorio');
      return;
    }
    
    setLoading(true);
    setError('');

    try {
      await axios.put(`${API_URL}/me`, profileData);
      if (refreshUser) await refreshUser();
      showSuccess('Perfil actualizado correctamente');
    } catch (err) {
      showError(err.response?.data?.detail || 'Error al actualizar perfil');
    } finally {
      setLoading(false);
    }
  };

  // ============== VEHICLE ==============
  const handleVehicleUpdate = async (e) => {
    e.preventDefault();
    
    // Validation
    if (!vehicleData.vehicle_plate.trim()) {
      showError('La matrícula es obligatoria');
      return;
    }
    
    setLoading(true);
    setError('');

    try {
      await axios.put(`${API_URL}/me`, vehicleData);
      if (refreshUser) await refreshUser();
      showSuccess('Vehículo actualizado correctamente');
    } catch (err) {
      showError(err.response?.data?.detail || 'Error al actualizar vehículo');
    } finally {
      setLoading(false);
    }
  };

  // ============== DRIVERS ==============
  const openAddDriver = () => {
    setEditingDriver(null);
    setDriverForm({ full_name: '', dni: '' });
    setDriverDialog(true);
  };

  const openEditDriver = (driver) => {
    setEditingDriver(driver);
    setDriverForm({ full_name: driver.full_name, dni: driver.dni });
    setDriverDialog(true);
  };

  const handleSaveDriver = async () => {
    // Validations
    if (!driverForm.full_name.trim()) {
      showError('El nombre del chofer es obligatorio');
      return;
    }
    if (!driverForm.dni.trim()) {
      showError('El DNI del chofer es obligatorio');
      return;
    }
    
    setSavingDriver(true);
    try {
      if (editingDriver) {
        await axios.put(`${API_URL}/me/drivers/${editingDriver.id}`, driverForm);
        showSuccess('Chofer actualizado');
      } else {
        await axios.post(`${API_URL}/me/drivers`, driverForm);
        showSuccess('Chofer añadido');
      }
      setDriverDialog(false);
      fetchDrivers();
    } catch (err) {
      showError(err.response?.data?.detail || 'Error al guardar chofer');
    } finally {
      setSavingDriver(false);
    }
  };

  const handleDeleteDriver = async (driverId) => {
    try {
      await axios.delete(`${API_URL}/me/drivers/${driverId}`);
      showSuccess('Chofer eliminado');
      setDeleteConfirm(null);
      fetchDrivers();
    } catch (err) {
      showError(err.response?.data?.detail || 'Error al eliminar chofer');
    }
  };

  // ============== LOGOUT ==============
  const handleLogout = async () => {
    await logout();
    navigate('/app/login');
  };

  // ============== CHANGE PASSWORD ==============
  const handleChangePassword = async (e) => {
    e.preventDefault();
    setPasswordError('');
    
    // Validations
    if (!passwordForm.current_password) {
      setPasswordError('Introduce tu contraseña actual');
      return;
    }
    if (!passwordForm.new_password) {
      setPasswordError('Introduce la nueva contraseña');
      return;
    }
    if (passwordForm.new_password.length < 8) {
      setPasswordError('La contraseña debe tener al menos 8 caracteres');
      return;
    }
    if (!/[A-Z]/.test(passwordForm.new_password)) {
      setPasswordError('La contraseña debe tener al menos una mayúscula');
      return;
    }
    if (!/[0-9]/.test(passwordForm.new_password)) {
      setPasswordError('La contraseña debe tener al menos un número');
      return;
    }
    if (passwordForm.new_password !== passwordForm.confirm_password) {
      setPasswordError('Las contraseñas no coinciden');
      return;
    }
    
    setChangingPassword(true);
    try {
      await axios.post(`${API_URL}/me/change-password`, {
        current_password: passwordForm.current_password,
        new_password: passwordForm.new_password
      });
      
      // Clear form
      setPasswordForm({ current_password: '', new_password: '', confirm_password: '' });
      
      // Show success message and redirect to login
      showSuccess('Contraseña actualizada. Serás redirigido al login...');
      
      // Wait and redirect
      setTimeout(async () => {
        await logout();
        navigate('/app/login', { state: { message: 'Sesión cerrada por seguridad tras cambiar la contraseña' } });
      }, 2000);
      
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (err.response?.status === 401) {
        setPasswordError('Contraseña actual incorrecta');
      } else {
        setPasswordError(detail || 'Error al cambiar la contraseña');
      }
    } finally {
      setChangingPassword(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-stone-900" style={{ fontFamily: 'Chivo, sans-serif' }}>
          Configuración
        </h1>
        <p className="text-stone-600">Gestiona tu perfil, vehículo y conductores</p>
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
        <TabsList className="grid w-full grid-cols-5 h-12">
          <TabsTrigger value="perfil" className="data-[state=active]:bg-maroon-900 data-[state=active]:text-white text-xs sm:text-sm">
            <User className="w-4 h-4 sm:mr-2" />
            <span className="hidden sm:inline">Perfil</span>
          </TabsTrigger>
          <TabsTrigger value="vehiculo" className="data-[state=active]:bg-maroon-900 data-[state=active]:text-white text-xs sm:text-sm">
            <Car className="w-4 h-4 sm:mr-2" />
            <span className="hidden sm:inline">Vehículo</span>
          </TabsTrigger>
          <TabsTrigger value="choferes" className="data-[state=active]:bg-maroon-900 data-[state=active]:text-white text-xs sm:text-sm">
            <Users className="w-4 h-4 sm:mr-2" />
            <span className="hidden sm:inline">Choferes</span>
          </TabsTrigger>
          <TabsTrigger value="asistencia" className="data-[state=active]:bg-maroon-900 data-[state=active]:text-white text-xs sm:text-sm">
            <Truck className="w-4 h-4 sm:mr-2" />
            <span className="hidden sm:inline">Asistencia</span>
          </TabsTrigger>
          <TabsTrigger value="seguridad" className="data-[state=active]:bg-maroon-900 data-[state=active]:text-white text-xs sm:text-sm">
            <Shield className="w-4 h-4 sm:mr-2" />
            <span className="hidden sm:inline">Seguridad</span>
          </TabsTrigger>
        </TabsList>

        {/* Profile Tab */}
        <TabsContent value="perfil">
          <Card className="border-0 shadow-lg">
            <CardHeader>
              <CardTitle>Datos Personales</CardTitle>
              <CardDescription>Información de tu licencia y contacto</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleProfileUpdate} className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label className="text-stone-600 font-medium text-sm uppercase tracking-wide">
                      Nombre Completo *
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
                      DNI/CIF *
                    </Label>
                    <Input
                      value={profileData.dni_cif}
                      onChange={(e) => setProfileData(prev => ({ ...prev, dni_cif: e.target.value }))}
                      className="h-12"
                      data-testid="config-dni"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label className="text-stone-600 font-medium text-sm uppercase tracking-wide">
                      Nº Licencia Taxi
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
                  <div className="space-y-2">
                    <Label className="text-stone-600 font-medium text-sm uppercase tracking-wide">
                      Email (no editable)
                    </Label>
                    <Input
                      value={user?.email || ''}
                      disabled
                      className="h-12 bg-stone-100 text-stone-500"
                    />
                    <p className="text-xs text-stone-500">El email no puede modificarse por seguridad</p>
                  </div>
                </div>
                <Button
                  type="submit"
                  disabled={loading}
                  className="h-12 px-6 rounded-full bg-maroon-900 hover:bg-maroon-800"
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
            <CardHeader>
              <CardTitle>Datos del Vehículo</CardTitle>
              <CardDescription>Información de tu vehículo de trabajo</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleVehicleUpdate} className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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
                      Matrícula *
                    </Label>
                    <Input
                      value={vehicleData.vehicle_plate}
                      onChange={(e) => setVehicleData(prev => ({ ...prev, vehicle_plate: e.target.value.toUpperCase() }))}
                      className="h-12"
                      data-testid="config-vehicle-plate"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label className="text-stone-600 font-medium text-sm uppercase tracking-wide">
                      Nº VT
                    </Label>
                    <Input
                      value={vehicleData.vehicle_license_number}
                      onChange={(e) => setVehicleData(prev => ({ ...prev, vehicle_license_number: e.target.value.toUpperCase() }))}
                      className="h-12"
                      placeholder="Ej: VT-12345"
                      data-testid="config-vehicle-license-number"
                    />
                  </div>
                </div>
                <Button
                  type="submit"
                  disabled={loading}
                  className="h-12 px-6 rounded-full bg-maroon-900 hover:bg-maroon-800"
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
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Conductores Adicionales</CardTitle>
                  <CardDescription>Choferes que pueden conducir tu vehículo</CardDescription>
                </div>
                <Button
                  onClick={openAddDriver}
                  className="h-10 rounded-full bg-maroon-900 hover:bg-maroon-800"
                  data-testid="add-driver-btn"
                >
                  <Plus className="w-4 h-4 mr-2" />
                  Añadir
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {loadingDrivers ? (
                <div className="flex justify-center py-8">
                  <Loader2 className="w-6 h-6 animate-spin text-maroon-900" />
                </div>
              ) : drivers.length === 0 ? (
                <div className="text-center py-8 text-stone-500">
                  <Users className="w-12 h-12 mx-auto mb-3 opacity-30" />
                  <p>No tienes conductores adicionales</p>
                  <p className="text-sm">Añade choferes que puedan usar tu vehículo</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {drivers.map((driver) => (
                    <div 
                      key={driver.id}
                      className="flex items-center justify-between p-4 bg-stone-50 rounded-lg"
                    >
                      <div>
                        <p className="font-medium text-stone-900">{driver.full_name}</p>
                        <p className="text-sm text-stone-500">DNI: {driver.dni}</p>
                      </div>
                      <div className="flex gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => openEditDriver(driver)}
                          data-testid={`edit-driver-${driver.id}`}
                        >
                          <Pencil className="w-4 h-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setDeleteConfirm(driver)}
                          className="text-red-600 hover:text-red-700 hover:bg-red-50"
                          data-testid={`delete-driver-${driver.id}`}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Assistance Companies Tab */}
        <TabsContent value="asistencia">
          <Card className="border-0 shadow-lg">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Empresas de Asistencia</CardTitle>
                  <CardDescription>Gestiona las empresas de asistencia en carretera con las que trabajas</CardDescription>
                </div>
                <Button onClick={() => openCompanyDialog()} size="sm" className="bg-maroon-900 hover:bg-maroon-800">
                  <Plus className="w-4 h-4 mr-2" />
                  Añadir
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {loadingCompanies ? (
                <div className="flex justify-center py-8">
                  <Loader2 className="w-8 h-8 animate-spin text-stone-400" />
                </div>
              ) : assistanceCompanies.length === 0 ? (
                <div className="text-center py-8 text-stone-500">
                  <Truck className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p>No tienes empresas de asistencia registradas</p>
                  <p className="text-sm">Añade las empresas con las que trabajas para usarlas en tus hojas de ruta</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {assistanceCompanies.map((company) => (
                    <div key={company.id} className="flex items-center justify-between p-4 bg-stone-50 rounded-lg">
                      <div className="flex-1">
                        <p className="font-medium text-stone-900">{company.name}</p>
                        <p className="text-sm text-stone-500">CIF: {company.cif}</p>
                        <p className="text-sm text-stone-500">
                          {company.contact_phone && `Tel: ${company.contact_phone}`}
                          {company.contact_phone && company.contact_email && ' | '}
                          {company.contact_email && `Email: ${company.contact_email}`}
                        </p>
                      </div>
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => openCompanyDialog(company)}
                        >
                          <Pencil className="w-4 h-4" />
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          className="text-red-600 hover:bg-red-50"
                          onClick={() => setDeleteCompanyConfirm(company.id)}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Security Tab */}
        <TabsContent value="seguridad">
          <Card className="border-0 shadow-lg">
            <CardHeader>
              <CardTitle>Seguridad de la Cuenta</CardTitle>
              <CardDescription>Gestiona tu sesión y contraseña</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Change Password Form */}
              <div className="p-4 bg-stone-50 rounded-lg">
                <div className="flex items-center gap-2 mb-4">
                  <Shield className="w-5 h-5 text-stone-500" />
                  <p className="font-medium text-stone-900">Cambiar Contraseña</p>
                </div>
                
                {passwordError && (
                  <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                    {passwordError}
                  </div>
                )}
                
                <form onSubmit={handleChangePassword} className="space-y-4">
                  <div className="space-y-2">
                    <Label className="text-stone-600 text-sm">Contraseña Actual</Label>
                    <PasswordInput
                      value={passwordForm.current_password}
                      onChange={(e) => setPasswordForm(prev => ({ ...prev, current_password: e.target.value }))}
                      placeholder="••••••••"
                      className="h-11"
                      data-testid="current-password"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label className="text-stone-600 text-sm">Nueva Contraseña</Label>
                    <PasswordInput
                      value={passwordForm.new_password}
                      onChange={(e) => setPasswordForm(prev => ({ ...prev, new_password: e.target.value }))}
                      placeholder="Mín. 8 caracteres, 1 mayúscula, 1 número"
                      className="h-11"
                      data-testid="new-password"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label className="text-stone-600 text-sm">Confirmar Nueva Contraseña</Label>
                    <PasswordInput
                      value={passwordForm.confirm_password}
                      onChange={(e) => setPasswordForm(prev => ({ ...prev, confirm_password: e.target.value }))}
                      placeholder="Repite la nueva contraseña"
                      className="h-11"
                      data-testid="confirm-password"
                    />
                  </div>
                  <Button
                    type="submit"
                    disabled={changingPassword}
                    className="w-full bg-maroon-900 hover:bg-maroon-800 h-11"
                    data-testid="change-password-submit"
                  >
                    {changingPassword ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Cambiando...
                      </>
                    ) : (
                      'Cambiar Contraseña'
                    )}
                  </Button>
                  <p className="text-xs text-stone-500 text-center">
                    Al cambiar tu contraseña, se cerrará tu sesión por seguridad.
                  </p>
                </form>
              </div>

              {/* Logout */}
              <div className="flex items-center justify-between p-4 bg-stone-50 rounded-lg">
                <div>
                  <p className="font-medium text-stone-900">Cerrar Sesión</p>
                  <p className="text-sm text-stone-500">Salir de tu cuenta en este dispositivo</p>
                </div>
                <Button
                  variant="outline"
                  onClick={() => setLogoutConfirm(true)}
                  className="border-red-300 text-red-600 hover:bg-red-50"
                  data-testid="logout-btn"
                >
                  <LogOut className="w-4 h-4 mr-2" />
                  Cerrar Sesión
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Driver Dialog */}
      <Dialog open={driverDialog} onOpenChange={setDriverDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {editingDriver ? 'Editar Chofer' : 'Añadir Chofer'}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Nombre Completo *</Label>
              <Input
                value={driverForm.full_name}
                onChange={(e) => setDriverForm({...driverForm, full_name: e.target.value})}
                placeholder="Nombre y apellidos"
                data-testid="driver-name-input"
              />
            </div>
            <div className="space-y-2">
              <Label>DNI *</Label>
              <Input
                value={driverForm.dni}
                onChange={(e) => setDriverForm({...driverForm, dni: e.target.value.toUpperCase()})}
                placeholder="12345678A"
                data-testid="driver-dni-input"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDriverDialog(false)}>
              Cancelar
            </Button>
            <Button
              onClick={handleSaveDriver}
              disabled={savingDriver}
              className="bg-maroon-900 hover:bg-maroon-800"
              data-testid="save-driver-btn"
            >
              {savingDriver ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Guardar'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Driver Confirm */}
      <Dialog open={!!deleteConfirm} onOpenChange={() => setDeleteConfirm(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Eliminar Chofer</DialogTitle>
          </DialogHeader>
          <p className="py-4 text-stone-600">
            ¿Estás seguro de eliminar a <strong>{deleteConfirm?.full_name}</strong>?
            Esta acción no se puede deshacer.
          </p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteConfirm(null)}>
              Cancelar
            </Button>
            <Button
              onClick={() => handleDeleteDriver(deleteConfirm.id)}
              className="bg-red-600 hover:bg-red-700"
              data-testid="confirm-delete-driver"
            >
              Eliminar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Logout Confirm */}
      <Dialog open={logoutConfirm} onOpenChange={setLogoutConfirm}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Cerrar Sesión</DialogTitle>
          </DialogHeader>
          <p className="py-4 text-stone-600">
            ¿Estás seguro de que quieres cerrar sesión?
          </p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setLogoutConfirm(false)}>
              Cancelar
            </Button>
            <Button
              onClick={handleLogout}
              className="bg-red-600 hover:bg-red-700"
              data-testid="confirm-logout"
            >
              Cerrar Sesión
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
