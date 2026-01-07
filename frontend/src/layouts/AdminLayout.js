/**
 * RutasFast - Admin Layout (Desktop sidebar)
 */
import React from 'react';
import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { useAdminAuth } from '../contexts/AdminAuthContext';
import { Users, FileText, Settings, LogOut, Shield } from 'lucide-react';

export function AdminLayout() {
  const { logout } = useAdminAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/admin/login');
  };

  const navItems = [
    { to: '/admin/usuarios', icon: Users, label: 'Usuarios' },
    { to: '/admin/hojas', icon: FileText, label: 'Hojas de Ruta' },
    { to: '/admin/config', icon: Settings, label: 'Configuración' },
  ];

  return (
    <div className="min-h-screen bg-stone-100 flex">
      {/* Sidebar */}
      <aside className="w-64 bg-stone-900 text-stone-300 fixed h-full z-50">
        <div className="p-6 border-b border-stone-700">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-maroon-900 rounded-lg flex items-center justify-center">
              <Shield className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-white font-bold" style={{ fontFamily: 'Chivo, sans-serif' }}>
                RutasFast
              </h1>
              <p className="text-xs text-stone-500">Panel Admin</p>
            </div>
          </div>
        </div>

        <nav className="p-4 space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                  isActive
                    ? 'bg-maroon-900 text-white'
                    : 'text-stone-400 hover:bg-stone-800 hover:text-white'
                }`
              }
              data-testid={`admin-nav-${item.label.toLowerCase()}`}
            >
              <item.icon className="w-5 h-5" />
              <span className="font-medium">{item.label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-stone-700">
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 px-4 py-3 w-full text-stone-400 hover:bg-stone-800 hover:text-white rounded-lg transition-colors"
            data-testid="admin-logout-btn"
          >
            <LogOut className="w-5 h-5" />
            <span className="font-medium">Cerrar Sesión</span>
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="ml-64 flex-1 p-8">
        <div className="max-w-6xl mx-auto">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
