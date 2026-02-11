/**
 * RutasFast - Admin Route Sheets Page
 */
import React, { useState, useEffect, useCallback } from 'react';
import { useAdminAuth } from '../../contexts/AdminAuthContext';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Card, CardContent } from '../../components/ui/card';
import { Badge } from '../../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../../components/ui/dialog';
import { Label } from '../../components/ui/label';
import axios from 'axios';
import { 
  Search, Download, Loader2, FileText, Calendar, 
  Filter, Eye, EyeOff
} from 'lucide-react';

const API_URL = `${process.env.REACT_APP_BACKEND_URL}/api`;

export function AdminSheetsPage() {
  const { adminRequest, adminToken } = useAdminAuth();
  const [sheets, setSheets] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    status: 'all',
    user_visible: 'all',
    user_id: 'all',
    from_date: '',
    to_date: ''
  });
  const [selectedSheet, setSelectedSheet] = useState(null);
  const [userSearch, setUserSearch] = useState('');

  // Fetch users for filter dropdown
  useEffect(() => {
    const fetchUsers = async () => {
      try {
        const data = await adminRequest('get', '/admin/users');
        // Only approved users
        setUsers(data.filter(u => u.status === 'APPROVED'));
      } catch (err) {
        console.error('Error fetching users:', err);
      }
    };
    fetchUsers();
  }, [adminRequest]);

  // Filter users based on search
  const filteredUsers = users.filter(u => 
    userSearch === '' || 
    u.full_name?.toLowerCase().includes(userSearch.toLowerCase()) ||
    u.email?.toLowerCase().includes(userSearch.toLowerCase())
  );

  const fetchSheets = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      Object.entries(filters).forEach(([key, value]) => {
        // Skip 'all' values and empty strings
        if (value !== '' && value !== 'all') params.append(key, value);
      });
      
      const data = await adminRequest('get', `/admin/route-sheets?${params}`);
      setSheets(data);
    } catch (err) {
      console.error('Error fetching sheets:', err);
    } finally {
      setLoading(false);
    }
  }, [adminRequest, filters]);

  useEffect(() => {
    fetchSheets();
  }, [fetchSheets]);

  const updateFilter = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  const downloadPdf = async (sheetId, sheetNumber) => {
    try {
      const response = await axios.get(`${API_URL}/admin/route-sheets/${sheetId}/pdf`, {
        headers: { Authorization: `Bearer ${adminToken}` },
        responseType: 'blob'
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      const safeNum = sheetNumber.replace(/[^\w-]+/g, '_').replace(/_+/g, '_').replace(/^_|_$/g, '') || 'unknown';
      link.setAttribute('download', `hoja_ruta_${safeNum}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => window.URL.revokeObjectURL(url), 1500);
    } catch (err) {
      console.error('Error downloading PDF:', err);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('es-ES', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      timeZone: 'Europe/Madrid'
    });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-stone-900" style={{ fontFamily: 'Chivo, sans-serif' }}>
            Hojas de Ruta
          </h1>
          <p className="text-stone-600">Listado global de todas las hojas</p>
        </div>
        <div className="flex items-center gap-2 text-sm text-stone-500">
          <FileText className="w-5 h-5" />
          {sheets.length} hojas
        </div>
      </div>

      {/* Filters */}
      <Card className="border-0 shadow-lg">
        <CardContent className="pt-4 pb-4">
          <div className="grid grid-cols-1 md:grid-cols-6 gap-4">
            {/* User filter with search */}
            <div className="space-y-1 md:col-span-2">
              <Label className="text-xs text-stone-500">Taxista</Label>
              <Select value={filters.user_id} onValueChange={(v) => updateFilter('user_id', v)}>
                <SelectTrigger data-testid="filter-user">
                  <SelectValue placeholder="Todos los taxistas" />
                </SelectTrigger>
                <SelectContent>
                  <div className="px-2 py-1.5 sticky top-0 bg-white border-b">
                    <Input
                      placeholder="Buscar taxista..."
                      value={userSearch}
                      onChange={(e) => setUserSearch(e.target.value)}
                      className="h-8"
                      data-testid="user-search"
                    />
                  </div>
                  <SelectItem value="all">Todos los taxistas</SelectItem>
                  {filteredUsers.map((user) => (
                    <SelectItem key={user.id} value={user.id}>
                      {user.full_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label className="text-xs text-stone-500">Estado</Label>
              <Select value={filters.status} onValueChange={(v) => updateFilter('status', v)}>
                <SelectTrigger data-testid="filter-status">
                  <SelectValue placeholder="Todos" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos</SelectItem>
                  <SelectItem value="ACTIVE">Activas</SelectItem>
                  <SelectItem value="ANNULLED">Anuladas</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label className="text-xs text-stone-500">Visibilidad</Label>
              <Select value={filters.user_visible} onValueChange={(v) => updateFilter('user_visible', v)}>
                <SelectTrigger data-testid="filter-visibility">
                  <SelectValue placeholder="Todas" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todas</SelectItem>
                  <SelectItem value="true">Visibles</SelectItem>
                  <SelectItem value="false">Ocultas</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label className="text-xs text-stone-500">Desde</Label>
              <Input
                type="date"
                value={filters.from_date}
                onChange={(e) => updateFilter('from_date', e.target.value)}
                className="h-10"
                data-testid="filter-from"
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs text-stone-500">Hasta</Label>
              <Input
                type="date"
                value={filters.to_date}
                onChange={(e) => updateFilter('to_date', e.target.value)}
                className="h-10"
                data-testid="filter-to"
              />
            </div>
          </div>
          <div className="flex justify-end mt-4">
            <Button
              variant="outline"
              onClick={() => {
                setFilters({ status: 'all', user_visible: 'all', user_id: 'all', from_date: '', to_date: '' });
                setUserSearch('');
              }}
            >
              Limpiar filtros
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Sheets table */}
      <Card className="border-0 shadow-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-stone-50 border-b border-stone-200">
              <tr>
                <th className="text-left px-6 py-4 text-sm font-semibold text-stone-600">Nº Hoja</th>
                <th className="text-left px-6 py-4 text-sm font-semibold text-stone-600">Usuario</th>
                <th className="text-left px-6 py-4 text-sm font-semibold text-stone-600">Destino</th>
                <th className="text-left px-6 py-4 text-sm font-semibold text-stone-600">Fecha Recogida</th>
                <th className="text-left px-6 py-4 text-sm font-semibold text-stone-600">Estado</th>
                <th className="text-left px-6 py-4 text-sm font-semibold text-stone-600">Visible</th>
                <th className="text-right px-6 py-4 text-sm font-semibold text-stone-600">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={7} className="text-center py-12">
                    <Loader2 className="w-8 h-8 animate-spin mx-auto text-maroon-900" />
                  </td>
                </tr>
              ) : sheets.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center py-12 text-stone-500">
                    No hay hojas de ruta
                  </td>
                </tr>
              ) : (
                sheets.map((sheet) => (
                  <tr 
                    key={sheet.id} 
                    className={`border-b border-stone-100 hover:bg-stone-50 transition-colors ${
                      sheet.status === 'ANNULLED' ? 'bg-red-50/30' : ''
                    }`}
                  >
                    <td className="px-6 py-4">
                      <span className="font-bold text-maroon-900" style={{ fontFamily: 'Chivo, sans-serif' }}>
                        {sheet.sheet_number}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <p className="text-stone-900">{sheet.user_name}</p>
                      <p className="text-xs text-stone-500">{sheet.user_email}</p>
                    </td>
                    <td className="px-6 py-4 max-w-[200px] truncate">
                      {sheet.destination}
                    </td>
                    <td className="px-6 py-4 text-sm text-stone-600">
                      {formatDate(sheet.pickup_datetime)}
                    </td>
                    <td className="px-6 py-4">
                      <Badge 
                        className={sheet.status === 'ACTIVE' 
                          ? 'bg-green-100 text-green-700 hover:bg-green-100' 
                          : 'bg-red-100 text-red-700 hover:bg-red-100'}
                      >
                        {sheet.status === 'ACTIVE' ? 'Activa' : 'Anulada'}
                      </Badge>
                    </td>
                    <td className="px-6 py-4">
                      {sheet.user_visible ? (
                        <Eye className="w-5 h-5 text-green-600" />
                      ) : (
                        <EyeOff className="w-5 h-5 text-stone-400" />
                      )}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setSelectedSheet(sheet)}
                          data-testid={`view-sheet-${sheet.id}`}
                        >
                          Ver
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => downloadPdf(sheet.id, sheet.sheet_number)}
                          data-testid={`download-sheet-${sheet.id}`}
                        >
                          <Download className="w-4 h-4" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Sheet Detail Dialog */}
      <Dialog open={!!selectedSheet} onOpenChange={(open) => !open && setSelectedSheet(null)}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-3">
              <div className="w-10 h-10 bg-maroon-100 rounded-lg flex items-center justify-center">
                <FileText className="w-5 h-5 text-maroon-900" />
              </div>
              Hoja {selectedSheet?.sheet_number}
              {selectedSheet?.status === 'ANNULLED' && (
                <Badge className="bg-red-100 text-red-700 ml-2">Anulada</Badge>
              )}
            </DialogTitle>
          </DialogHeader>
          
          {selectedSheet && (
            <div className="space-y-4 py-4">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <Label className="text-xs text-stone-500">Usuario</Label>
                  <p className="font-medium">{selectedSheet.user_name}</p>
                  <p className="text-stone-500">{selectedSheet.user_email}</p>
                </div>
                <div>
                  <Label className="text-xs text-stone-500">Contratante</Label>
                  <p className="font-medium">
                    {selectedSheet.contractor_phone || selectedSheet.contractor_email || '-'}
                  </p>
                </div>
                <div>
                  <Label className="text-xs text-stone-500">Precontratación</Label>
                  <p className="font-medium">{selectedSheet.prebooked_locality}</p>
                  <p className="text-stone-500">{selectedSheet.prebooked_date}</p>
                </div>
                <div>
                  <Label className="text-xs text-stone-500">Recogida</Label>
                  <p className="font-medium">
                    {selectedSheet.pickup_type === 'AIRPORT' 
                      ? `Aeropuerto - ${selectedSheet.flight_number}`
                      : selectedSheet.pickup_address || 'No especificada'}
                  </p>
                  <p className="text-stone-500">{formatDate(selectedSheet.pickup_datetime)}</p>
                </div>
                <div className="col-span-2">
                  <Label className="text-xs text-stone-500">Destino</Label>
                  <p className="font-medium">{selectedSheet.destination}</p>
                </div>
                {selectedSheet.annul_reason && (
                  <div className="col-span-2 p-3 bg-red-50 rounded-lg">
                    <Label className="text-xs text-red-600">Motivo anulación</Label>
                    <p className="text-red-800">{selectedSheet.annul_reason}</p>
                    <p className="text-xs text-red-500 mt-1">
                      {formatDate(selectedSheet.annulled_at)}
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}

          <DialogFooter>
            <Button
              onClick={() => downloadPdf(selectedSheet?.id, selectedSheet?.sheet_number)}
              className="bg-maroon-900 hover:bg-maroon-800"
            >
              <Download className="w-4 h-4 mr-2" />
              Descargar PDF
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
