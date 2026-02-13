/**
 * RutasFast Mobile - Settings Screen
 * Main settings menu with navigation to sub-screens
 */
import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuth } from '../contexts/AuthContext';
import { useDrivers } from '../contexts/DriversContext';

export default function SettingsScreen({ navigation }) {
  const { user, logout } = useAuth();
  const { drivers } = useDrivers();

  const handleLogout = () => {
    Alert.alert(
      'Cerrar Sesión',
      '¿Estás seguro de que quieres cerrar sesión?',
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'Cerrar Sesión',
          style: 'destructive',
          onPress: logout,
        },
      ]
    );
  };

  const menuItems = [
    {
      title: 'Mi Perfil',
      subtitle: user?.full_name || 'Configurar perfil',
      onPress: () => navigation.navigate('Profile'),
    },
    {
      title: 'Vehículo',
      subtitle: user?.vehicle_plate 
        ? `${user.vehicle_brand || ''} ${user.vehicle_model || ''} - ${user.vehicle_plate}`.trim()
        : 'Configurar vehículo',
      onPress: () => navigation.navigate('Vehicle'),
    },
    {
      title: 'Conductores',
      subtitle: drivers.length > 0 
        ? `${drivers.length} conductor${drivers.length > 1 ? 'es' : ''} adicional${drivers.length > 1 ? 'es' : ''}`
        : 'Gestionar conductores',
      onPress: () => navigation.navigate('Drivers'),
    },
    {
      title: 'Empresas de Asistencia',
      subtitle: 'Gestionar empresas de asistencia en carretera',
      onPress: () => navigation.navigate('AssistanceCompanies'),
    },
    {
      title: 'Cambiar Contraseña',
      subtitle: 'Actualiza tu contraseña de acceso',
      onPress: () => navigation.navigate('ChangePassword'),
    },
  ];

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <ScrollView style={styles.scroll}>
        <View style={styles.header}>
          <Text style={styles.title}>Configuración</Text>
        </View>

        {/* User Info Card */}
        <View style={styles.userCard}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>
              {user?.full_name?.charAt(0)?.toUpperCase() || 'U'}
            </Text>
          </View>
          <View style={styles.userInfo}>
            <Text style={styles.userName}>{user?.full_name || 'Usuario'}</Text>
            <Text style={styles.userEmail}>{user?.email}</Text>
            {user?.license_number && (
              <Text style={styles.userLicense}>
                Licencia: {user.license_number}
                {user.license_council ? ` - ${user.license_council}` : ''}
              </Text>
            )}
          </View>
        </View>

        {/* Menu Items */}
        <View style={styles.menu}>
          {menuItems.map((item, index) => (
            <TouchableOpacity
              key={index}
              style={[
                styles.menuItem,
                index === menuItems.length - 1 && styles.menuItemLast,
              ]}
              onPress={item.onPress}
            >
              <View style={styles.menuItemContent}>
                <Text style={styles.menuItemTitle}>{item.title}</Text>
                <Text style={styles.menuItemSubtitle} numberOfLines={1}>
                  {item.subtitle}
                </Text>
              </View>
              <Text style={styles.menuItemArrow}>›</Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* Logout Button */}
        <TouchableOpacity style={styles.logoutButton} onPress={handleLogout}>
          <Text style={styles.logoutButtonText}>Cerrar Sesión</Text>
        </TouchableOpacity>

        {/* App Version */}
        <Text style={styles.version}>RutasFast v1.0.0</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F4',
  },
  scroll: {
    flex: 1,
  },
  header: {
    padding: 24,
    paddingBottom: 16,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#1C1917',
  },
  userCard: {
    flexDirection: 'row',
    backgroundColor: '#fff',
    margin: 16,
    marginTop: 0,
    padding: 16,
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 1,
  },
  avatar: {
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: '#7A1F1F',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 16,
  },
  avatarText: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#fff',
  },
  userInfo: {
    flex: 1,
    justifyContent: 'center',
  },
  userName: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#1C1917',
  },
  userEmail: {
    fontSize: 14,
    color: '#57534E',
    marginTop: 2,
  },
  userLicense: {
    fontSize: 12,
    color: '#7A1F1F',
    marginTop: 4,
  },
  menu: {
    backgroundColor: '#fff',
    margin: 16,
    marginTop: 0,
    borderRadius: 12,
    overflow: 'hidden',
  },
  menuItem: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#F5F5F4',
  },
  menuItemLast: {
    borderBottomWidth: 0,
  },
  menuItemContent: {
    flex: 1,
  },
  menuItemTitle: {
    fontSize: 16,
    fontWeight: '500',
    color: '#1C1917',
  },
  menuItemSubtitle: {
    fontSize: 14,
    color: '#57534E',
    marginTop: 2,
  },
  menuItemArrow: {
    fontSize: 24,
    color: '#A8A29E',
    marginLeft: 8,
  },
  logoutButton: {
    margin: 16,
    marginTop: 8,
    padding: 16,
    borderRadius: 12,
    backgroundColor: '#FEE2E2',
    alignItems: 'center',
  },
  logoutButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#991B1B',
  },
  version: {
    textAlign: 'center',
    fontSize: 12,
    color: '#A8A29E',
    marginVertical: 24,
  },
});
