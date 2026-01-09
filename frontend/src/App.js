/**
 * RutasFast - Main App with Routes
 */
import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { AdminAuthProvider, useAdminAuth } from './contexts/AdminAuthContext';
import { Toaster } from './components/ui/sonner';

// Layouts
import { AppLayout } from './layouts/AppLayout';
import { AdminLayout } from './layouts/AdminLayout';

// Pages
import { LandingPage } from './pages/LandingPage';
import { LoginPage } from './pages/app/LoginPage';
import { RegisterPage } from './pages/app/RegisterPage';
import { CambiarPasswordPage } from './pages/app/CambiarPasswordPage';
import { NuevaHojaPage } from './pages/app/NuevaHojaPage';
import { HistoricoPage } from './pages/app/HistoricoPage';
import { ConfiguracionPage } from './pages/app/ConfiguracionPage';
import { AdminLoginPage } from './pages/admin/AdminLoginPage';
import { AdminUsersPage } from './pages/admin/AdminUsersPage';
import { AdminSheetsPage } from './pages/admin/AdminSheetsPage';
import { AdminConfigPage } from './pages/admin/AdminConfigPage';

import './App.css';

// Protected Route for Users - Redirects to change password if needed
function ProtectedUserRoute({ children }) {
  const { isAuthenticated, loading, mustChangePassword } = useAuth();
  
  if (loading) {
    return (
      <div className="min-h-screen bg-stone-100 flex items-center justify-center">
        <div className="w-8 h-8 border-4 border-maroon-900 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }
  
  if (!isAuthenticated) {
    return <Navigate to="/app/login" replace />;
  }
  
  // Force password change if required
  if (mustChangePassword) {
    return <Navigate to="/app/cambiar-password" replace />;
  }
  
  return children;
}

// Route for change password page - must be logged in but allows mustChangePassword
function ChangePasswordRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();
  
  if (loading) {
    return (
      <div className="min-h-screen bg-stone-100 flex items-center justify-center">
        <div className="w-8 h-8 border-4 border-maroon-900 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }
  
  if (!isAuthenticated) {
    return <Navigate to="/app/login" replace />;
  }
  
  return children;
}

// Protected Route for Admin
function ProtectedAdminRoute({ children }) {
  const { isAdmin, loading } = useAdminAuth();
  
  if (loading) {
    return (
      <div className="min-h-screen bg-stone-900 flex items-center justify-center">
        <div className="w-8 h-8 border-4 border-white border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }
  
  if (!isAdmin) {
    return <Navigate to="/admin/login" replace />;
  }
  
  return children;
}

function AppRoutes() {
  return (
    <Routes>
      {/* Landing */}
      <Route path="/" element={<LandingPage />} />
      
      {/* App Routes (Users) */}
      <Route path="/app/login" element={<LoginPage />} />
      <Route path="/app/registro" element={<RegisterPage />} />
      
      {/* Change password - protected but allows mustChangePassword */}
      <Route path="/app/cambiar-password" element={
        <ChangePasswordRoute>
          <CambiarPasswordPage />
        </ChangePasswordRoute>
      } />
      
      <Route path="/app" element={
        <ProtectedUserRoute>
          <AppLayout />
        </ProtectedUserRoute>
      }>
        <Route index element={<Navigate to="/app/nueva-hoja" replace />} />
        <Route path="nueva-hoja" element={<NuevaHojaPage />} />
        <Route path="historico" element={<HistoricoPage />} />
        <Route path="configuracion" element={<ConfiguracionPage />} />
      </Route>
      
      {/* Admin Routes */}
      <Route path="/admin/login" element={<AdminLoginPage />} />
      
      <Route path="/admin" element={
        <ProtectedAdminRoute>
          <AdminLayout />
        </ProtectedAdminRoute>
      }>
        <Route index element={<Navigate to="/admin/usuarios" replace />} />
        <Route path="usuarios" element={<AdminUsersPage />} />
        <Route path="hojas" element={<AdminSheetsPage />} />
        <Route path="config" element={<AdminConfigPage />} />
      </Route>
      
      {/* Catch all */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AdminAuthProvider>
          <AppRoutes />
          <Toaster position="top-center" />
        </AdminAuthProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
