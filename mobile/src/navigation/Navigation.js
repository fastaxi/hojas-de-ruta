/**
 * RutasFast Mobile - Navigation
 */
import React from 'react';
import { Text, View } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { useAuth } from '../contexts/AuthContext';

// Auth Screens
import LoginScreen from '../screens/LoginScreen';
import RegisterScreen from '../screens/RegisterScreen';

// Main Screens
import HomeScreen from '../screens/HomeScreen';
import HistoryScreen from '../screens/HistoryScreen';
import SettingsScreen from '../screens/SettingsScreen';

// Settings Sub-screens
import ProfileScreen from '../screens/ProfileScreen';
import VehicleScreen from '../screens/VehicleScreen';
import DriversScreen from '../screens/DriversScreen';
import ChangePasswordScreen from '../screens/ChangePasswordScreen';

const Stack = createNativeStackNavigator();
const Tab = createBottomTabNavigator();
const SettingsStack = createNativeStackNavigator();

// Tab Icon component
function TabIcon({ name, color, size }) {
  const icons = {
    '+': '+',
    '≡': '≡',
    '⚙': '⚙',
  };
  return (
    <View style={{ width: size, height: size, justifyContent: 'center', alignItems: 'center' }}>
      <Text style={{ fontSize: size - 4, color: color, fontWeight: 'bold' }}>
        {icons[name] || name}
      </Text>
    </View>
  );
}

// Auth Stack (Login/Register)
function AuthStack() {
  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      <Stack.Screen name="Login" component={LoginScreen} />
      <Stack.Screen name="Register" component={RegisterScreen} />
    </Stack.Navigator>
  );
}

// Settings Stack Navigator
function SettingsStackNavigator() {
  return (
    <SettingsStack.Navigator
      screenOptions={{
        headerStyle: { backgroundColor: '#F5F5F4' },
        headerTintColor: '#7A1F1F',
        headerTitleStyle: { fontWeight: '600' },
        headerBackTitle: 'Atrás',
      }}
    >
      <SettingsStack.Screen 
        name="SettingsHome" 
        component={SettingsScreen}
        options={{ headerShown: false }}
      />
      <SettingsStack.Screen 
        name="Profile" 
        component={ProfileScreen}
        options={{ title: 'Mi Perfil' }}
      />
      <SettingsStack.Screen 
        name="Vehicle" 
        component={VehicleScreen}
        options={{ title: 'Vehículo' }}
      />
      <SettingsStack.Screen 
        name="Drivers" 
        component={DriversScreen}
        options={{ title: 'Conductores' }}
      />
      <SettingsStack.Screen 
        name="ChangePassword" 
        component={ChangePasswordScreen}
        options={{ title: 'Cambiar Contraseña' }}
      />
    </SettingsStack.Navigator>
  );
}

// Main Tab Navigator
function MainTabs() {
  return (
    <Tab.Navigator
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: '#7A1F1F',
        tabBarInactiveTintColor: '#A8A29E',
        tabBarStyle: {
          backgroundColor: '#fff',
          borderTopColor: '#E7E5E4',
          paddingTop: 8,
          paddingBottom: 8,
          height: 60,
        },
        tabBarLabelStyle: {
          fontSize: 12,
          fontWeight: '500',
        },
      }}
    >
      <Tab.Screen
        name="Home"
        component={HomeScreen}
        options={{
          tabBarLabel: 'Nueva',
          tabBarIcon: ({ color, size }) => (
            <TabIcon name="+" color={color} size={size} />
          ),
        }}
      />
      <Tab.Screen
        name="History"
        component={HistoryScreen}
        options={{
          tabBarLabel: 'Histórico',
          tabBarIcon: ({ color, size }) => (
            <TabIcon name="≡" color={color} size={size} />
          ),
        }}
      />
      <Tab.Screen
        name="Settings"
        component={SettingsStackNavigator}
        options={{
          tabBarLabel: 'Ajustes',
          tabBarIcon: ({ color, size }) => (
            <TabIcon name="⚙" color={color} size={size} />
          ),
        }}
      />
    </Tab.Navigator>
  );
}

// Main Navigation
export default function Navigation() {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#1C1917' }}>
        <Text style={{ color: '#fff', fontSize: 24, fontWeight: 'bold' }}>RutasFast</Text>
      </View>
    );
  }

  return (
    <NavigationContainer>
      {isAuthenticated ? <MainTabs /> : <AuthStack />}
    </NavigationContainer>
  );
}
