/**
 * RutasFast Mobile - Main App Entry
 */
import React from 'react';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { AuthProvider } from './src/contexts/AuthContext';
import { DriversProvider } from './src/contexts/DriversContext';
import Navigation from './src/navigation/Navigation';

export default function App() {
  return (
    <SafeAreaProvider>
      <AuthProvider>
        <DriversProvider>
          <StatusBar style="light" />
          <Navigation />
        </DriversProvider>
      </AuthProvider>
    </SafeAreaProvider>
  );
}
