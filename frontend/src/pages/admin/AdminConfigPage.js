/**
 * RutasFast - Admin Config Page
 */
import React, { useState, useEffect, useCallback } from 'react';
import { useAdminAuth } from '../../contexts/AdminAuthContext';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../../components/ui/dialog';
import { Loader2, Save, Check, FileText, Clock, Play, AlertCircle, Trash2, RefreshCw, History } from 'lucide-react';

export function AdminConfigPage() {
  const { adminRequest } = useAdminAuth();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');
  const [config, setConfig] = useState({
    header_title: '',
    header_line1: '',
    header_line2: '',
    legend_text: '',
    hide_after_months: 14,
    purge_after_months: 24
  });

  // Retention job state
  const [retentionDialog, setRetentionDialog] = useState(false);
  const [retentionResult, setRetentionResult] = useState(null);
  const [runningRetention, setRunningRetention] = useState(false);
  const [lastRetentionRun, setLastRetentionRun] = useState(null);

  const fetchLastRetentionRun = useCallback(async () => {
    try {
      const data = await adminRequest('get', '/admin/retention-runs/last');
      setLastRetentionRun(data);
    } catch (err) {
      console.error('Error fetching last retention run:', err);
    }
  }, [adminRequest]);

  useEffect(() => {
    fetchConfig();
    fetchLastRetentionRun();
  }, [fetchLastRetentionRun]);

  const fetchConfig = async () => {
    try {
      const data = await adminRequest('get', '/admin/config');
      setConfig(data);
    } catch (err) {
      console.error('Error fetching config:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setError('');
    
    // Frontend validation
    if (config.purge_after_months <= config.hide_after_months) {
      setError('Los meses de eliminación deben ser mayores que los de ocultación');
      return;
    }
    
    setSaving(true);

    try {
      await adminRequest('put', '/admin/config', config);
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(detail || 'Error al guardar la configuración');
    } finally {
      setSaving(false);
    }
  };

  const runRetentionJob = async (dryRun = true) => {
    setRunningRetention(true);
    try {
      const result = await adminRequest('post', `/admin/run-retention?dry_run=${dryRun}`);
      setRetentionResult(result);
      // Refresh last run after real execution
      if (!dryRun) {
        fetchLastRetentionRun();
      }
    } catch (err) {
      setRetentionResult({
        error: true,
        message: err.response?.data?.detail || 'Error ejecutando el job'
      });
    } finally {
      setRunningRetention(false);
    }
  };

  const updateField = (field, value) => {
    setConfig(prev => ({ ...prev, [field]: value }));
    setError('');
  };

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-maroon-900" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-stone-900" style={{ fontFamily: 'Chivo, sans-serif' }}>
          Configuración
        </h1>
        <p className="text-stone-600">Ajustes globales de RutasFast</p>
      </div>

      {success && (
        <div className="flex items-center gap-2 p-4 bg-green-50 border border-green-200 rounded-lg text-green-800">
          <Check className="w-5 h-5" />
          <p>Configuración guardada correctamente</p>
        </div>
      )}

      {error && (
        <div className="flex items-center gap-2 p-4 bg-red-50 border border-red-200 rounded-lg text-red-800">
          <AlertCircle className="w-5 h-5" />
          <p>{error}</p>
        </div>
      )}

      <form onSubmit={handleSave} className="space-y-6">
        {/* PDF Headers */}
        <Card className="border-0 shadow-lg">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="w-5 h-5 text-maroon-900" />
              Textos del PDF
            </CardTitle>
            <CardDescription>
              Estos textos aparecen en la cabecera y pie de todas las hojas de ruta
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label className="text-stone-600 font-medium text-sm uppercase tracking-wide">
                Título Principal
              </Label>
              <Input
                value={config.header_title}
                onChange={(e) => updateField('header_title', e.target.value)}
                placeholder="HOJA DE RUTA"
                className="h-12"
                data-testid="config-header-title"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-stone-600 font-medium text-sm uppercase tracking-wide">
                Línea 1 (Entidad)
              </Label>
              <Input
                value={config.header_line1}
                onChange={(e) => updateField('header_line1', e.target.value)}
                placeholder="CONSEJERIA DE MOVILIDAD..."
                className="h-12"
                data-testid="config-header-line1"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-stone-600 font-medium text-sm uppercase tracking-wide">
                Línea 2 (Servicio)
              </Label>
              <Input
                value={config.header_line2}
                onChange={(e) => updateField('header_line2', e.target.value)}
                placeholder="Servicio de Inspección..."
                className="h-12"
                data-testid="config-header-line2"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-stone-600 font-medium text-sm uppercase tracking-wide">
                Texto de Leyenda (Pie)
              </Label>
              <Textarea
                value={config.legend_text}
                onChange={(e) => updateField('legend_text', e.target.value)}
                placeholder="Es obligatorio conservar los registros..."
                rows={3}
                className="resize-none"
                data-testid="config-legend-text"
              />
            </div>
          </CardContent>
        </Card>

        {/* Retention Settings */}
        <Card className="border-0 shadow-lg">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock className="w-5 h-5 text-maroon-900" />
              Retención de Datos
            </CardTitle>
            <CardDescription>
              Configura cuándo se ocultan y eliminan las hojas de ruta
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-2 gap-6">
              <div className="space-y-2">
                <Label className="text-stone-600 font-medium text-sm uppercase tracking-wide">
                  Ocultar al usuario después de (meses)
                </Label>
                <Input
                  type="number"
                  min={1}
                  max={36}
                  value={config.hide_after_months}
                  onChange={(e) => updateField('hide_after_months', parseInt(e.target.value) || 14)}
                  className="h-12"
                  data-testid="config-hide-months"
                />
                <p className="text-xs text-stone-500">
                  Las hojas se ocultarán del histórico del usuario pero seguirán visibles para el admin
                </p>
              </div>
              <div className="space-y-2">
                <Label className="text-stone-600 font-medium text-sm uppercase tracking-wide">
                  Eliminar definitivamente después de (meses)
                </Label>
                <Input
                  type="number"
                  min={1}
                  max={60}
                  value={config.purge_after_months}
                  onChange={(e) => updateField('purge_after_months', parseInt(e.target.value) || 24)}
                  className="h-12"
                  data-testid="config-purge-months"
                />
                <p className="text-xs text-stone-500">
                  Las hojas se eliminarán permanentemente de la base de datos
                </p>
              </div>
            </div>
            
            {/* Last Retention Run Info */}
            <div className="pt-4 border-t border-stone-200">
              <div className="flex items-center gap-2 mb-3">
                <History className="w-4 h-4 text-stone-500" />
                <span className="font-medium text-stone-700 text-sm">Última Ejecución</span>
              </div>
              {lastRetentionRun ? (
                <div className="p-3 bg-stone-50 rounded-lg">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div>
                      <p className="text-stone-500 text-xs">Fecha</p>
                      <p className="font-medium text-stone-900">
                        {new Date(lastRetentionRun.run_at).toLocaleString('es-ES', {
                          day: '2-digit',
                          month: '2-digit',
                          year: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit'
                        })}
                      </p>
                    </div>
                    <div>
                      <p className="text-stone-500 text-xs">Origen</p>
                      <p className="font-medium text-stone-900">
                        {lastRetentionRun.trigger === 'internal' ? 'Automático' : 'Manual (Admin)'}
                      </p>
                    </div>
                    <div>
                      <p className="text-stone-500 text-xs">Ocultas</p>
                      <p className="font-medium text-amber-600">{lastRetentionRun.hidden_count}</p>
                    </div>
                    <div>
                      <p className="text-stone-500 text-xs">Eliminadas</p>
                      <p className="font-medium text-red-600">{lastRetentionRun.purged_count}</p>
                    </div>
                  </div>
                </div>
              ) : (
                <p className="text-sm text-stone-500 italic">No hay ejecuciones registradas</p>
              )}
            </div>
            
            {/* Retention Job Button */}
            <div className="pt-4 border-t border-stone-200">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-stone-900">Ejecutar Job de Retención</p>
                  <p className="text-sm text-stone-500">
                    Procesa manualmente las hojas pendientes de ocultar/eliminar
                  </p>
                </div>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => {
                    setRetentionResult(null);
                    setRetentionDialog(true);
                  }}
                  className="border-maroon-900 text-maroon-900"
                  data-testid="run-retention-btn"
                >
                  <Play className="w-4 h-4 mr-2" />
                  Ejecutar
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        <Button
          type="submit"
          disabled={saving}
          className="w-full md:w-auto h-12 px-8 rounded-full bg-maroon-900 hover:bg-maroon-800"
          data-testid="save-config-btn"
        >
          {saving ? (
            <>
              <Loader2 className="w-5 h-5 mr-2 animate-spin" />
              Guardando...
            </>
          ) : (
            <>
              <Save className="w-5 h-5 mr-2" />
              Guardar Configuración
            </>
          )}
        </Button>
      </form>

      {/* Retention Job Dialog */}
      <Dialog open={retentionDialog} onOpenChange={setRetentionDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Trash2 className="w-5 h-5 text-maroon-900" />
              Ejecutar Job de Retención
            </DialogTitle>
          </DialogHeader>
          
          <div className="py-4">
            {!retentionResult ? (
              <div className="space-y-4">
                <p className="text-stone-600">
                  Este proceso ocultará las hojas más antiguas de {config.hide_after_months} meses
                  y eliminará permanentemente las de más de {config.purge_after_months} meses.
                </p>
                <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg">
                  <p className="text-amber-800 text-sm">
                    <strong>Recomendación:</strong> Ejecuta primero en modo simulación para ver qué hojas se afectarán.
                  </p>
                </div>
              </div>
            ) : retentionResult.error ? (
              <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-800">
                {retentionResult.message}
              </div>
            ) : (
              <div className="space-y-4">
                <div className={`p-4 rounded-lg ${retentionResult.dry_run ? 'bg-blue-50 border border-blue-200' : 'bg-green-50 border border-green-200'}`}>
                  <p className={retentionResult.dry_run ? 'text-blue-800' : 'text-green-800'}>
                    {retentionResult.message}
                  </p>
                </div>
                
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-stone-500">Total hojas</p>
                    <p className="font-bold text-stone-900">{retentionResult.stats_before?.total || 0}</p>
                  </div>
                  <div>
                    <p className="text-stone-500">Visibles</p>
                    <p className="font-bold text-stone-900">{retentionResult.stats_before?.visible || 0}</p>
                  </div>
                  <div>
                    <p className="text-stone-500">A ocultar</p>
                    <p className="font-bold text-amber-600">{retentionResult.to_hide}</p>
                  </div>
                  <div>
                    <p className="text-stone-500">A eliminar</p>
                    <p className="font-bold text-red-600">{retentionResult.to_purge}</p>
                  </div>
                </div>
              </div>
            )}
          </div>

          <DialogFooter>
            {runningRetention ? (
              <Button disabled className="bg-maroon-900">
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Ejecutando...
              </Button>
            ) : !retentionResult ? (
              <>
                <Button variant="outline" onClick={() => runRetentionJob(true)}>
                  Simular (dry run)
                </Button>
                <Button 
                  onClick={() => runRetentionJob(false)}
                  className="bg-maroon-900 hover:bg-maroon-800"
                >
                  Ejecutar
                </Button>
              </>
            ) : retentionResult.dry_run && !retentionResult.error ? (
              <>
                <Button variant="outline" onClick={() => setRetentionResult(null)}>
                  Volver
                </Button>
                <Button 
                  onClick={() => runRetentionJob(false)}
                  className="bg-red-600 hover:bg-red-700"
                >
                  Confirmar Ejecución
                </Button>
              </>
            ) : (
              <Button variant="outline" onClick={() => setRetentionDialog(false)}>
                Cerrar
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
