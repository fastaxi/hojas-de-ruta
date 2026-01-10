/**
 * RutasFast - Histórico Page
 */
import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Card, CardContent } from '../../components/ui/card';
import { Switch } from '../../components/ui/switch';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../../components/ui/dialog';
import { Textarea } from '../../components/ui/textarea';
import { toast } from '../../hooks/use-toast';
import { 
  FileText, Download, Ban, Search, Filter, Loader2, 
  Calendar, ChevronRight, AlertTriangle, X
} from 'lucide-react';

const API_URL = `${process.env.REACT_APP_BACKEND_URL}/api`;

// ============== PDF DOWNLOAD HELPERS ==============
const isIOS = () => {
  const ua = window.navigator.userAgent;
  return /iPad|iPhone|iPod/.test(ua) && !window.MSStream;
};

const diffDaysInclusive = (from, to) => {
  const f = new Date(`${from}T00:00:00`);
  const t = new Date(`${to}T00:00:00`);
  const ms = t.getTime() - f.getTime();
  return Math.floor(ms / (1000 * 60 * 60 * 24)) + 1;
};

const extractBlobErrorMessage = async (blob) => {
  try {
    const text = await blob.text();
    const maybeJson = JSON.parse(text);
    if (maybeJson?.detail) return String(maybeJson.detail);
    if (maybeJson?.message) return String(maybeJson.message);
    return text?.slice(0, 200) || null;
  } catch {
    return null;
  }
};

export function HistoricoPage() {
  const [sheets, setSheets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [includeAnnulled, setIncludeAnnulled] = useState(false);
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [isExportingRange, setIsExportingRange] = useState(false);
  
  // Annul dialog
  const [annulDialog, setAnnulDialog] = useState({ open: false, sheet: null });
  const [annulReason, setAnnulReason] = useState('');
  const [annulling, setAnnulling] = useState(false);

  // Detail dialog
  const [detailDialog, setDetailDialog] = useState({ open: false, sheet: null });

  const fetchSheets = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (fromDate) params.append('from_date', fromDate);
      if (toDate) params.append('to_date', toDate);
      if (includeAnnulled) params.append('include_annulled', 'true');
      
      const response = await axios.get(`${API_URL}/route-sheets?${params}`);
      // API returns { sheets: [], next_cursor: null, count: 0 }
      setSheets(response.data.sheets || []);
    } catch (err) {
      console.error('Error fetching sheets:', err);
    } finally {
      setLoading(false);
    }
  }, [fromDate, toDate, includeAnnulled]);

  useEffect(() => {
    fetchSheets();
  }, [fetchSheets]);

  const handleAnnul = async () => {
    if (!annulDialog.sheet) return;
    
    setAnnulling(true);
    try {
      await axios.post(`${API_URL}/route-sheets/${annulDialog.sheet.id}/annul`, {
        reason: annulReason || null
      });
      setAnnulDialog({ open: false, sheet: null });
      setAnnulReason('');
      fetchSheets();
    } catch (err) {
      console.error('Error annulling sheet:', err);
    } finally {
      setAnnulling(false);
    }
  };

  const downloadPdf = async (sheetId, sheetNumber) => {
    try {
      const response = await axios.get(`${API_URL}/route-sheets/${sheetId}/pdf`, {
        responseType: 'blob'
      });
      
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      
      if (isIOS()) {
        link.target = '_blank';
        link.rel = 'noopener';
      } else {
        link.setAttribute('download', `hoja_ruta_${sheetNumber.replace('/', '_')}.pdf`);
      }
      
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => window.URL.revokeObjectURL(url), 1500);
    } catch (err) {
      console.error('Error downloading PDF:', err);
      toast({ title: 'Error al descargar el PDF', variant: 'destructive' });
    }
  };

  const downloadRangePdf = async () => {
    if (!fromDate || !toDate) {
      toast({ title: 'Selecciona fechas de inicio y fin', variant: 'destructive' });
      return;
    }

    if (fromDate > toDate) {
      toast({ title: 'El rango no es válido: "Desde" no puede ser posterior a "Hasta"', variant: 'destructive' });
      return;
    }

    const days = diffDaysInclusive(fromDate, toDate);
    if (days > 31) {
      toast({ title: 'El rango máximo para exportar es 31 días', variant: 'destructive' });
      return;
    }

    setIsExportingRange(true);
    try {
      const urlReq = `${API_URL}/route-sheets/pdf/range?from_date=${encodeURIComponent(fromDate)}&to_date=${encodeURIComponent(toDate)}`;
      const response = await axios.get(urlReq, { responseType: 'blob' });

      // Check if backend returned JSON error instead of PDF
      const contentType = response.headers?.['content-type'] || '';
      if (contentType.includes('application/json')) {
        const msg = await extractBlobErrorMessage(response.data);
        toast({ title: msg || 'No se pudo generar el PDF', variant: 'destructive' });
        return;
      }

      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;

      if (isIOS()) {
        link.target = '_blank';
        link.rel = 'noopener';
      } else {
        link.setAttribute('download', `hojas_ruta_${fromDate}_a_${toDate}.pdf`);
      }

      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => window.URL.revokeObjectURL(url), 1500);
      
      toast({ title: 'PDF descargado correctamente' });
    } catch (err) {
      console.error('Error downloading range PDF:', err);

      const status = err?.response?.status;

      if (status === 404 || status === 204) {
        toast({ title: 'No hay hojas en el rango seleccionado', variant: 'destructive' });
        return;
      }

      if (status === 400) {
        const blob = err?.response?.data;
        if (blob instanceof Blob) {
          const msg = await extractBlobErrorMessage(blob);
          toast({ title: msg || 'Solicitud inválida. Revisa el rango de fechas.', variant: 'destructive' });
        } else {
          toast({ title: 'Solicitud inválida. Revisa el rango de fechas.', variant: 'destructive' });
        }
        return;
      }

      toast({ title: 'Error al descargar el PDF. Reinténtalo.', variant: 'destructive' });
    } finally {
      setIsExportingRange(false);
    }
  };

  const filteredSheets = sheets.filter(sheet => {
    if (!searchTerm) return true;
    return sheet.sheet_number.includes(searchTerm) || 
           sheet.destination?.toLowerCase().includes(searchTerm.toLowerCase());
  });

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString('es-ES', { 
      day: '2-digit', 
      month: '2-digit', 
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-stone-900" style={{ fontFamily: 'Chivo, sans-serif' }}>
          Histórico
        </h1>
        <p className="text-stone-600">Consulta y exporta tus hojas de ruta</p>
      </div>

      {/* Filters */}
      <Card className="border-0 shadow-lg">
        <CardContent className="pt-4 pb-4">
          <div className="space-y-4">
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-stone-400" />
              <Input
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Buscar por número o destino..."
                className="pl-10 h-12"
                data-testid="search-sheets"
              />
            </div>

            {/* Date filters */}
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label className="text-xs text-stone-500">Desde</Label>
                <Input
                  type="date"
                  value={fromDate}
                  onChange={(e) => setFromDate(e.target.value)}
                  className="h-10"
                  data-testid="filter-from"
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs text-stone-500">Hasta</Label>
                <Input
                  type="date"
                  value={toDate}
                  onChange={(e) => setToDate(e.target.value)}
                  className="h-10"
                  data-testid="filter-to"
                />
              </div>
            </div>

            {/* Toggle and export */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Switch
                  checked={includeAnnulled}
                  onCheckedChange={setIncludeAnnulled}
                  data-testid="toggle-annulled"
                />
                <Label className="text-sm text-stone-600">Mostrar anuladas</Label>
              </div>
              
              {fromDate && toDate && (
                <div className="flex items-center gap-2">
                  <span className="text-xs text-stone-400 hidden sm:inline">Sin anuladas</span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={downloadRangePdf}
                    disabled={isExportingRange}
                    className="text-maroon-900 border-maroon-900"
                    data-testid="export-range-btn"
                  >
                    {isExportingRange ? (
                      <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                    ) : (
                      <Download className="w-4 h-4 mr-1" />
                    )}
                    {isExportingRange ? 'Generando...' : 'Exportar rango'}
                  </Button>
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Sheets list */}
      {loading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-maroon-900" />
        </div>
      ) : filteredSheets.length === 0 ? (
        <Card className="border-0 shadow-lg">
          <CardContent className="py-12 text-center">
            <FileText className="w-12 h-12 text-stone-300 mx-auto mb-4" />
            <p className="text-stone-500">No hay hojas de ruta</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {filteredSheets.map((sheet) => (
            <Card 
              key={sheet.id} 
              className={`border-0 shadow-md transition-all ${
                sheet.status === 'ANNULLED' ? 'opacity-60 bg-stone-50' : 'bg-white'
              }`}
            >
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex-1" onClick={() => setDetailDialog({ open: true, sheet })}>
                    <div className="flex items-center gap-3 cursor-pointer">
                      <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                        sheet.status === 'ANNULLED' ? 'bg-red-100' : 'bg-maroon-100'
                      }`}>
                        <FileText className={`w-5 h-5 ${
                          sheet.status === 'ANNULLED' ? 'text-red-600' : 'text-maroon-900'
                        }`} />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-stone-900" style={{ fontFamily: 'Chivo, sans-serif' }}>
                            {sheet.sheet_number}
                          </span>
                          {sheet.status === 'ANNULLED' && (
                            <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full">
                              ANULADA
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-stone-500 truncate max-w-[180px]">
                          {sheet.destination}
                        </p>
                        <p className="text-xs text-stone-400">
                          {formatDate(sheet.pickup_datetime)}
                        </p>
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-2">
                    {sheet.status === 'ACTIVE' && (
                      <>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => downloadPdf(sheet.id, sheet.sheet_number)}
                          className="text-stone-500 hover:text-maroon-900"
                          data-testid={`download-${sheet.id}`}
                        >
                          <Download className="w-5 h-5" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => setAnnulDialog({ open: true, sheet })}
                          className="text-stone-500 hover:text-red-600"
                          data-testid={`annul-${sheet.id}`}
                        >
                          <Ban className="w-5 h-5" />
                        </Button>
                      </>
                    )}
                    <ChevronRight className="w-5 h-5 text-stone-300" />
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Annul Dialog */}
      <Dialog open={annulDialog.open} onOpenChange={(open) => !open && setAnnulDialog({ open: false, sheet: null })}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-600">
              <AlertTriangle className="w-5 h-5" />
              Anular Hoja {annulDialog.sheet?.sheet_number}
            </DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <p className="text-stone-600 mb-4">
              ¿Estás seguro de que quieres anular esta hoja de ruta? Esta acción no se puede deshacer.
            </p>
            <div className="space-y-2">
              <Label className="text-stone-600 text-sm">Motivo (opcional)</Label>
              <Textarea
                value={annulReason}
                onChange={(e) => setAnnulReason(e.target.value)}
                placeholder="Indica el motivo de la anulación..."
                className="resize-none"
                rows={3}
                data-testid="annul-reason"
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setAnnulDialog({ open: false, sheet: null })}
            >
              Cancelar
            </Button>
            <Button
              variant="destructive"
              onClick={handleAnnul}
              disabled={annulling}
              data-testid="confirm-annul"
            >
              {annulling ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Anulando...
                </>
              ) : (
                'Anular Hoja'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Detail Dialog */}
      <Dialog open={detailDialog.open} onOpenChange={(open) => !open && setDetailDialog({ open: false, sheet: null })}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center justify-between">
              <span>Hoja {detailDialog.sheet?.sheet_number}</span>
              {detailDialog.sheet?.status === 'ANNULLED' && (
                <span className="text-xs bg-red-100 text-red-700 px-2 py-1 rounded-full">
                  ANULADA
                </span>
              )}
            </DialogTitle>
          </DialogHeader>
          {detailDialog.sheet && (
            <div className="space-y-4 py-4">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-stone-500">Contratante</p>
                  <p className="font-medium">
                    {detailDialog.sheet.contractor_phone || detailDialog.sheet.contractor_email || '-'}
                  </p>
                </div>
                <div>
                  <p className="text-stone-500">Precontratación</p>
                  <p className="font-medium">{detailDialog.sheet.prebooked_locality}</p>
                </div>
                <div>
                  <p className="text-stone-500">Recogida</p>
                  <p className="font-medium">
                    {detailDialog.sheet.pickup_type === 'AIRPORT' 
                      ? `Aeropuerto - ${detailDialog.sheet.flight_number}`
                      : detailDialog.sheet.pickup_address || '-'}
                  </p>
                </div>
                <div>
                  <p className="text-stone-500">Fecha/Hora</p>
                  <p className="font-medium">{formatDate(detailDialog.sheet.pickup_datetime)}</p>
                </div>
                <div className="col-span-2">
                  <p className="text-stone-500">Destino</p>
                  <p className="font-medium">{detailDialog.sheet.destination}</p>
                </div>
                {detailDialog.sheet.annul_reason && (
                  <div className="col-span-2 p-3 bg-red-50 rounded-lg">
                    <p className="text-red-600 text-sm font-medium">Motivo anulación:</p>
                    <p className="text-red-800">{detailDialog.sheet.annul_reason}</p>
                  </div>
                )}
              </div>
            </div>
          )}
          <DialogFooter>
            {detailDialog.sheet?.status === 'ACTIVE' && (
              <Button
                onClick={() => downloadPdf(detailDialog.sheet.id, detailDialog.sheet.sheet_number)}
                className="bg-maroon-900 hover:bg-maroon-800"
              >
                <Download className="w-4 h-4 mr-2" />
                Descargar PDF
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
