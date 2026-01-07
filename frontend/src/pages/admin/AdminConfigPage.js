/**
 * RutasFast - Admin Config Page
 */
import React, { useState, useEffect } from 'react';
import { useAdminAuth } from '../../contexts/AdminAuthContext';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Loader2, Save, Check, Settings, FileText, Clock } from 'lucide-react';

export function AdminConfigPage() {
  const { adminRequest } = useAdminAuth();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);
  const [config, setConfig] = useState({
    header_title: '',
    header_line1: '',
    header_line2: '',
    legend_text: '',
    hide_after_months: 14,
    purge_after_months: 24
  });

  useEffect(() => {
    fetchConfig();
  }, []);

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
    setSaving(true);

    try {
      await adminRequest('put', '/admin/config', config);
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      console.error('Error saving config:', err);
    } finally {
      setSaving(false);
    }
  };

  const updateField = (field, value) => {
    setConfig(prev => ({ ...prev, [field]: value }));
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
          <CardContent>
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
    </div>
  );
}
