/**
 * RutasFast - Landing Page (Portada)
 */
import React from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Car, Shield, FileText } from 'lucide-react';

export function LandingPage() {
  return (
    <div 
      className="min-h-screen bg-cover bg-center bg-no-repeat relative"
      style={{ 
        backgroundImage: 'url(https://images.pexels.com/photos/17950533/pexels-photo-17950533.jpeg)',
      }}
    >
      {/* Overlay */}
      <div className="absolute inset-0 bg-gradient-to-b from-black/70 via-black/50 to-black/80" />
      
      {/* Content */}
      <div className="relative z-10 min-h-screen flex flex-col">
        {/* Header */}
        <header className="p-6">
          <div className="max-w-md mx-auto">
            <div className="flex items-center gap-2">
              <span 
                className="text-3xl font-black text-white"
                style={{ fontFamily: 'Chivo, sans-serif' }}
              >
                FAST
              </span>
            </div>
          </div>
        </header>

        {/* Main */}
        <main className="flex-1 flex flex-col justify-center px-6">
          <div className="max-w-md mx-auto w-full text-center">
            {/* Logo placeholder */}
            <div className="mb-8">
              <div 
                className="w-24 h-24 mx-auto bg-maroon-900 rounded-2xl flex items-center justify-center shadow-2xl"
              >
                <Car className="w-12 h-12 text-white" />
              </div>
            </div>

            <h1 
              className="text-4xl sm:text-5xl font-black text-white mb-4 tracking-tight"
              style={{ fontFamily: 'Chivo, sans-serif' }}
            >
              RutasFast
            </h1>
            
            <p className="text-lg text-stone-300 mb-8" style={{ fontFamily: 'IBM Plex Sans, sans-serif' }}>
              Hojas de Ruta digitales para taxistas de Asturias
            </p>

            {/* Features */}
            <div className="grid grid-cols-2 gap-4 mb-10">
              <div className="bg-white/10 backdrop-blur-sm rounded-xl p-4 text-left">
                <FileText className="w-6 h-6 text-gold-500 mb-2" />
                <p className="text-sm text-white font-medium">Genera hojas numeradas</p>
              </div>
              <div className="bg-white/10 backdrop-blur-sm rounded-xl p-4 text-left">
                <Shield className="w-6 h-6 text-gold-500 mb-2" />
                <p className="text-sm text-white font-medium">Cumple normativa</p>
              </div>
            </div>

            {/* CTA Buttons */}
            <div className="space-y-3">
              <Link to="/app/login" className="block">
                <Button 
                  className="w-full h-14 text-lg font-semibold rounded-full bg-maroon-900 hover:bg-maroon-800 text-white shadow-lg"
                  data-testid="landing-login-btn"
                >
                  Iniciar Sesión
                </Button>
              </Link>
              
              <Link to="/app/registro" className="block">
                <Button 
                  variant="outline"
                  className="w-full h-14 text-lg font-semibold rounded-full border-2 border-gold-500 text-white hover:bg-gold-500/20"
                  data-testid="landing-register-btn"
                >
                  Crear Cuenta
                </Button>
              </Link>
            </div>
          </div>
        </main>

        {/* Footer */}
        <footer className="p-6 text-center">
          <p className="text-sm text-stone-500">
            Federación Asturiana Sindical del Taxi
          </p>
        </footer>
      </div>
    </div>
  );
}
