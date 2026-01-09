/**
 * RutasFast - Admin Users Page
 */
import React, { useState, useEffect, useCallback } from 'react';
import { useAdminAuth } from '../../contexts/AdminAuthContext';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Badge } from '../../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '../../components/ui/dialog';
import { Label } from '../../components/ui/label';
import { Tabs, TabsList, TabsTrigger } from '../../components/ui/tabs';
import { 
  Search, Check, KeyRound, Loader2, User, Mail, Phone, 
  Car, FileText, ChevronRight, Users, Copy, AlertTriangle, CheckCircle
} from 'lucide-react';

export function AdminUsersPage() {
  const { adminRequest } = useAdminAuth();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('PENDING');
  const [search, setSearch] = useState('');
  const [selectedUser, setSelectedUser] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [message, setMessage] = useState('');

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filter) params.append('status', filter);
      if (search) params.append('search', search);
      
      const data = await adminRequest('get', `/admin/users?${params}`);
      setUsers(data);
    } catch (err) {
      console.error('Error fetching users:', err);
    } finally {
      setLoading(false);
    }
  }, [adminRequest, filter, search]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  const handleApprove = async (userId) => {
    setActionLoading(true);
    try {
      const result = await adminRequest('post', `/admin/users/${userId}/approve`);
      setMessage(result.email_sent 
        ? 'Usuario aprobado y notificado por email' 
        : 'Usuario aprobado (email no enviado)');
      fetchUsers();
      setSelectedUser(null);
    } catch (err) {
      setMessage('Error al aprobar usuario');
    } finally {
      setActionLoading(false);
      setTimeout(() => setMessage(''), 3000);
    }
  };

  const handleSendReset = async (userId) => {
    setActionLoading(true);
    try {
      const result = await adminRequest('post', `/admin/users/${userId}/send-reset`);
      setMessage(result.email_sent 
        ? 'Email de recuperación enviado' 
        : 'Error enviando email');
    } catch (err) {
      setMessage('Error al enviar email');
    } finally {
      setActionLoading(false);
      setTimeout(() => setMessage(''), 3000);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('es-ES', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric'
    });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-stone-900" style={{ fontFamily: 'Chivo, sans-serif' }}>
            Usuarios
          </h1>
          <p className="text-stone-600">Gestiona los usuarios de RutasFast</p>
        </div>
        <div className="flex items-center gap-2 text-sm text-stone-500">
          <Users className="w-5 h-5" />
          {users.length} usuarios
        </div>
      </div>

      {/* Message */}
      {message && (
        <div className="p-4 bg-green-50 border border-green-200 rounded-lg text-green-800">
          {message}
        </div>
      )}

      {/* Filters */}
      <Card className="border-0 shadow-lg">
        <CardContent className="pt-4 pb-4">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-stone-400" />
              <Input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Buscar por nombre, email o DNI..."
                className="pl-10 h-11"
                data-testid="admin-search-users"
              />
            </div>
            <Tabs value={filter} onValueChange={setFilter}>
              <TabsList>
                <TabsTrigger value="PENDING" data-testid="filter-pending">
                  Pendientes
                </TabsTrigger>
                <TabsTrigger value="APPROVED" data-testid="filter-approved">
                  Aprobados
                </TabsTrigger>
                <TabsTrigger value="" data-testid="filter-all">
                  Todos
                </TabsTrigger>
              </TabsList>
            </Tabs>
          </div>
        </CardContent>
      </Card>

      {/* Users table */}
      <Card className="border-0 shadow-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-stone-50 border-b border-stone-200">
              <tr>
                <th className="text-left px-6 py-4 text-sm font-semibold text-stone-600">Usuario</th>
                <th className="text-left px-6 py-4 text-sm font-semibold text-stone-600">Licencia</th>
                <th className="text-left px-6 py-4 text-sm font-semibold text-stone-600">Vehículo</th>
                <th className="text-left px-6 py-4 text-sm font-semibold text-stone-600">Estado</th>
                <th className="text-left px-6 py-4 text-sm font-semibold text-stone-600">Registro</th>
                <th className="text-right px-6 py-4 text-sm font-semibold text-stone-600">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={6} className="text-center py-12">
                    <Loader2 className="w-8 h-8 animate-spin mx-auto text-maroon-900" />
                  </td>
                </tr>
              ) : users.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-center py-12 text-stone-500">
                    No hay usuarios
                  </td>
                </tr>
              ) : (
                users.map((user) => (
                  <tr 
                    key={user.id} 
                    className="border-b border-stone-100 hover:bg-stone-50 transition-colors"
                  >
                    <td className="px-6 py-4">
                      <div>
                        <p className="font-medium text-stone-900">{user.full_name}</p>
                        <p className="text-sm text-stone-500">{user.email}</p>
                        <p className="text-xs text-stone-400">{user.dni_cif}</p>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <p className="text-stone-900">{user.license_number}</p>
                      <p className="text-sm text-stone-500">{user.license_council}</p>
                    </td>
                    <td className="px-6 py-4">
                      <p className="text-stone-900">{user.vehicle_brand} {user.vehicle_model}</p>
                      <p className="text-sm text-stone-500">{user.vehicle_plate}</p>
                    </td>
                    <td className="px-6 py-4">
                      <Badge 
                        variant={user.status === 'APPROVED' ? 'default' : 'secondary'}
                        className={user.status === 'APPROVED' 
                          ? 'bg-green-100 text-green-700 hover:bg-green-100' 
                          : 'bg-yellow-100 text-yellow-700 hover:bg-yellow-100'}
                      >
                        {user.status === 'APPROVED' ? 'Aprobado' : 'Pendiente'}
                      </Badge>
                    </td>
                    <td className="px-6 py-4 text-sm text-stone-500">
                      {formatDate(user.created_at)}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setSelectedUser(user)}
                        data-testid={`view-user-${user.id}`}
                      >
                        Ver <ChevronRight className="w-4 h-4 ml-1" />
                      </Button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* User Detail Dialog */}
      <Dialog open={!!selectedUser} onOpenChange={(open) => !open && setSelectedUser(null)}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-3">
              <div className="w-10 h-10 bg-maroon-100 rounded-lg flex items-center justify-center">
                <User className="w-5 h-5 text-maroon-900" />
              </div>
              {selectedUser?.full_name}
            </DialogTitle>
          </DialogHeader>
          
          {selectedUser && (
            <div className="space-y-4 py-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <Label className="text-xs text-stone-500">Email</Label>
                  <p className="font-medium flex items-center gap-2">
                    <Mail className="w-4 h-4 text-stone-400" />
                    {selectedUser.email}
                  </p>
                </div>
                <div className="space-y-1">
                  <Label className="text-xs text-stone-500">Teléfono</Label>
                  <p className="font-medium flex items-center gap-2">
                    <Phone className="w-4 h-4 text-stone-400" />
                    {selectedUser.phone}
                  </p>
                </div>
                <div className="space-y-1">
                  <Label className="text-xs text-stone-500">DNI/CIF</Label>
                  <p className="font-medium">{selectedUser.dni_cif}</p>
                </div>
                <div className="space-y-1">
                  <Label className="text-xs text-stone-500">Licencia</Label>
                  <p className="font-medium">{selectedUser.license_number}</p>
                </div>
                <div className="space-y-1">
                  <Label className="text-xs text-stone-500">Concejo</Label>
                  <p className="font-medium">{selectedUser.license_council}</p>
                </div>
                <div className="space-y-1">
                  <Label className="text-xs text-stone-500">Estado</Label>
                  <Badge 
                    className={selectedUser.status === 'APPROVED' 
                      ? 'bg-green-100 text-green-700' 
                      : 'bg-yellow-100 text-yellow-700'}
                  >
                    {selectedUser.status === 'APPROVED' ? 'Aprobado' : 'Pendiente'}
                  </Badge>
                </div>
              </div>

              <div className="p-4 bg-stone-50 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <Car className="w-5 h-5 text-stone-500" />
                  <span className="font-medium">Vehículo</span>
                </div>
                <p className="text-stone-700">
                  {selectedUser.vehicle_brand} {selectedUser.vehicle_model} - {selectedUser.vehicle_plate}
                </p>
              </div>

              {selectedUser.drivers && selectedUser.drivers.length > 0 && (
                <div className="p-4 bg-stone-50 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <Users className="w-5 h-5 text-stone-500" />
                    <span className="font-medium">Choferes ({selectedUser.drivers.length})</span>
                  </div>
                  <ul className="space-y-1">
                    {selectedUser.drivers.map((driver) => (
                      <li key={driver.id} className="text-sm text-stone-600">
                        {driver.full_name} - {driver.dni}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          <DialogFooter className="gap-2">
            <Button
              variant="outline"
              onClick={() => handleSendReset(selectedUser?.id)}
              disabled={actionLoading}
              data-testid="send-reset-btn"
            >
              <KeyRound className="w-4 h-4 mr-2" />
              Enviar Reset Password
            </Button>
            {selectedUser?.status === 'PENDING' && (
              <Button
                onClick={() => handleApprove(selectedUser?.id)}
                disabled={actionLoading}
                className="bg-green-600 hover:bg-green-700"
                data-testid="approve-user-btn"
              >
                {actionLoading ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Check className="w-4 h-4 mr-2" />
                )}
                Aprobar Usuario
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
