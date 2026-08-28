/**
 * RutasFast - Admin Stats Page
 */
import React, { useState, useEffect, useCallback } from 'react';
import { useAdminAuth } from '../../contexts/AdminAuthContext';
import { Card, CardContent } from '../../components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, Legend } from 'recharts';
import { format, parse } from 'date-fns';
import { es } from 'date-fns/locale';
import { FileText, Users, UserCheck, UserPlus, Loader2, Trophy } from 'lucide-react';

const formatMonth = (m) => {
  try {
    return format(parse(m, 'yyyy-MM', new Date()), 'MMM yy', { locale: es });
  } catch {
    return m;
  }
};

const StatCard = ({ icon: Icon, label, value, sub, testId }) => (
  <Card className="border-0 shadow-lg">
    <CardContent className="pt-5 pb-5">
      <div className="flex items-center gap-4">
        <div className="w-11 h-11 bg-maroon-100 rounded-lg flex items-center justify-center shrink-0">
          <Icon className="w-5 h-5 text-maroon-900" />
        </div>
        <div className="min-w-0">
          <p className="text-2xl font-bold text-stone-900" style={{ fontFamily: 'Chivo, sans-serif' }} data-testid={testId}>
            {value}
          </p>
          <p className="text-sm text-stone-500 truncate">{label}</p>
          {sub && <p className="text-xs text-stone-400 truncate">{sub}</p>}
        </div>
      </div>
    </CardContent>
  </Card>
);

export function AdminStatsPage() {
  const { adminRequest } = useAdminAuth();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [months, setMonths] = useState('12');

  const fetchStats = useCallback(async () => {
    setLoading(true);
    try {
      const data = await adminRequest('get', `/admin/stats?months=${months}`);
      setStats(data);
    } catch (err) {
      console.error('Error fetching stats:', err);
    } finally {
      setLoading(false);
    }
  }, [adminRequest, months]);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  if (loading && !stats) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="w-8 h-8 animate-spin text-maroon-900" />
      </div>
    );
  }

  const totals = stats?.totals || {};
  const chartData = (stats?.sheets_by_month || []).map((m) => ({
    label: formatMonth(m.month),
    Activas: m.total - m.annulled,
    Anuladas: m.annulled
  }));
  const topUsers = stats?.top_users || [];
  const maxCount = topUsers.length ? topUsers[0].sheets_count : 0;

  return (
    <div className="space-y-6" data-testid="admin-stats-page">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-3xl font-bold text-stone-900" style={{ fontFamily: 'Chivo, sans-serif' }}>
            Estadísticas
          </h1>
          <p className="text-stone-600">Actividad de hojas de ruta y taxistas</p>
        </div>
        <div className="w-44">
          <Select value={months} onValueChange={setMonths}>
            <SelectTrigger data-testid="stats-months-select">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="6">Últimos 6 meses</SelectItem>
              <SelectItem value="12">Últimos 12 meses</SelectItem>
              <SelectItem value="24">Últimos 24 meses</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Totals */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={FileText}
          label="Hojas totales"
          value={totals.total_sheets ?? 0}
          sub={`${totals.active_sheets ?? 0} activas · ${totals.annulled_sheets ?? 0} anuladas`}
          testId="stat-total-sheets"
        />
        <StatCard icon={Users} label="Usuarios totales" value={totals.total_users ?? 0} testId="stat-total-users" />
        <StatCard icon={UserCheck} label="Taxistas aprobados" value={totals.approved_users ?? 0} testId="stat-approved-users" />
        <StatCard icon={UserPlus} label="Pendientes de aprobar" value={totals.pending_users ?? 0} testId="stat-pending-users" />
      </div>

      {/* Sheets per month */}
      <Card className="border-0 shadow-lg">
        <CardContent className="pt-6 pb-4">
          <h2 className="text-lg font-semibold text-stone-900 mb-4" style={{ fontFamily: 'Chivo, sans-serif' }}>
            Hojas creadas por mes
          </h2>
          {chartData.length === 0 ? (
            <p className="text-stone-500 text-sm py-8 text-center">Sin datos en el periodo seleccionado</p>
          ) : (
            <div className="h-72" data-testid="stats-monthly-chart">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e7e5e4" vertical={false} />
                  <XAxis dataKey="label" tick={{ fontSize: 12, fill: '#78716c' }} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 12, fill: '#78716c' }} />
                  <Tooltip cursor={{ fill: '#f5f5f4' }} />
                  <Legend />
                  <Bar dataKey="Activas" stackId="a" fill="#7f1d1d" radius={[0, 0, 0, 0]} />
                  <Bar dataKey="Anuladas" stackId="a" fill="#d6a5a5" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Top taxistas */}
      <Card className="border-0 shadow-lg">
        <CardContent className="pt-6 pb-6">
          <div className="flex items-center gap-2 mb-4">
            <Trophy className="w-5 h-5 text-maroon-900" />
            <h2 className="text-lg font-semibold text-stone-900" style={{ fontFamily: 'Chivo, sans-serif' }}>
              Taxistas más activos
            </h2>
          </div>
          {topUsers.length === 0 ? (
            <p className="text-stone-500 text-sm py-4 text-center">Sin actividad en el periodo seleccionado</p>
          ) : (
            <div className="space-y-3" data-testid="stats-top-users">
              {topUsers.map((u, idx) => (
                <div key={u.user_id} className="flex items-center gap-3" data-testid={`top-user-${idx}`}>
                  <span className="w-6 text-sm font-bold text-stone-400 text-right shrink-0">{idx + 1}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-baseline justify-between gap-2">
                      <p className="text-sm font-medium text-stone-900 truncate">{u.full_name}</p>
                      <span className="text-sm font-bold text-maroon-900 shrink-0">{u.sheets_count}</span>
                    </div>
                    <div className="h-2 bg-stone-100 rounded-full mt-1 overflow-hidden">
                      <div
                        className="h-full bg-maroon-900 rounded-full transition-all"
                        style={{ width: `${maxCount ? Math.max((u.sheets_count / maxCount) * 100, 4) : 0}%` }}
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
