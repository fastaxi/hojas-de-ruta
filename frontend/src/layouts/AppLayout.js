/**
 * RutasFast - App Layout (Mobile-first for users)
 * Bottom navigation for taxistas
 */
import React from 'react';
import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { FileText, History, Settings, LogOut } from 'lucide-react';

export function AppLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/app/login');
  };

  return (
    <div className="min-h-screen bg-stone-100 pb-20">
      {/* Header */}
      <header className="bg-white border-b border-stone-200 px-4 py-3 sticky top-0 z-40">
        <div className="max-w-md mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-2xl font-black text-maroon-900" style={{ fontFamily: 'Chivo, sans-serif' }}>
              FAST
            </span>
            <span className="text-sm text-stone-500">RutasFast</span>
          </div>
          <button
            onClick={handleLogout}
            className="p-2 text-stone-500 hover:text-maroon-900 transition-colors"
            data-testid="logout-btn"
          >
            <LogOut className="w-5 h-5" />
          </button>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-md mx-auto px-4 py-6">
        <Outlet />
      </main>

      {/* Bottom Navigation */}
      <nav 
        className="fixed bottom-0 left-0 right-0 bg-white border-t border-stone-200 z-50"
        data-testid="bottom-nav"
      >
        <div className="max-w-md mx-auto flex items-center justify-around h-16">
          <NavLink
            to="/app/nueva-hoja"
            className={({ isActive }) =>
              `flex flex-col items-center gap-1 px-4 py-2 rounded-lg transition-colors ${
                isActive 
                  ? 'text-maroon-900 bg-maroon-50' 
                  : 'text-stone-500 hover:text-maroon-700'
              }`
            }
            data-testid="nav-nueva-hoja"
          >
            <FileText className="w-5 h-5" />
            <span className="text-xs font-medium">Nueva</span>
          </NavLink>

          <NavLink
            to="/app/historico"
            className={({ isActive }) =>
              `flex flex-col items-center gap-1 px-4 py-2 rounded-lg transition-colors ${
                isActive 
                  ? 'text-maroon-900 bg-maroon-50' 
                  : 'text-stone-500 hover:text-maroon-700'
              }`
            }
            data-testid="nav-historico"
          >
            <History className="w-5 h-5" />
            <span className="text-xs font-medium">Histórico</span>
          </NavLink>

          <NavLink
            to="/app/configuracion"
            className={({ isActive }) =>
              `flex flex-col items-center gap-1 px-4 py-2 rounded-lg transition-colors ${
                isActive 
                  ? 'text-maroon-900 bg-maroon-50' 
                  : 'text-stone-500 hover:text-maroon-700'
              }`
            }
            data-testid="nav-configuracion"
          >
            <Settings className="w-5 h-5" />
            <span className="text-xs font-medium">Ajustes</span>
          </NavLink>
        </div>
      </nav>
    </div>
  );
}
