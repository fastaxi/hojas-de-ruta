/**
 * RutasFast Mobile - Vehicle Screen
 * Edit vehicle information (brand, model, plate)
 */
import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  ScrollView,
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuth } from '../contexts/AuthContext';
import { updateMe } from '../services/meService';
import {
  validateVehicle,
  normalizeTrimOrNull,
  normalizeUpper,
} from '../utils/validators';

export default function VehicleScreen({ navigation }) {
  const { user, refreshUser } = useAuth();
  const [saving, setSaving] = useState(false);

  // Form state
  const [vehicleBrand, setVehicleBrand] = useState('');
  const [vehicleModel, setVehicleModel] = useState('');
  const [vehiclePlate, setVehiclePlate] = useState('');
  const [vehicleLicenseNumber, setVehicleLicenseNumber] = useState('');

  // Initialize form with user data
  useEffect(() => {
    if (user) {
      setVehicleBrand(user.vehicle_brand || '');
      setVehicleModel(user.vehicle_model || '');
      setVehiclePlate(user.vehicle_plate || '');
      setVehicleLicenseNumber(user.vehicle_license_number || '');
    }
  }, [user]);

  const handleSave = async () => {
    const payload = {
      vehicle_brand: normalizeTrimOrNull(vehicleBrand),
      vehicle_model: normalizeTrimOrNull(vehicleModel),
      vehicle_plate: normalizeUpper(vehiclePlate),
      vehicle_license_number: normalizeTrimOrNull(vehicleLicenseNumber),
    };

    // Validate
    const validation = validateVehicle(payload);
    if (!validation.ok) {
      Alert.alert('Error', validation.msg);
      return;
    }

    setSaving(true);
    try {
      await updateMe(payload);
      await refreshUser();
      Alert.alert('Éxito', 'Vehículo actualizado correctamente', [
        {
          text: 'OK',
          onPress: () => {
            if (navigation.canGoBack()) {
              navigation.goBack();
            } else {
              navigation.reset({
                index: 0,
                routes: [{ name: 'MainTabs' }],
              });
            }
          },
        },
      ]);
    } catch (error) {
      const message = error.response?.data?.detail || 'Error al guardar el vehículo';
      Alert.alert('Error', message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <SafeAreaView style={styles.container} edges={['bottom']}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.keyboardView}
      >
        <ScrollView style={styles.scroll} showsVerticalScrollIndicator={false}>
          <View style={styles.form}>
            {/* Info Card */}
            <View style={styles.infoCard}>
              <Text style={styles.infoText}>
                Los datos del vehículo aparecerán en las hojas de ruta y PDFs generados.
              </Text>
            </View>

            {/* Vehicle Brand */}
            <Text style={styles.label}>MARCA</Text>
            <TextInput
              style={styles.input}
              value={vehicleBrand}
              onChangeText={setVehicleBrand}
              placeholder="Toyota"
              placeholderTextColor="#999"
              autoCapitalize="words"
            />

            {/* Vehicle Model */}
            <Text style={styles.label}>MODELO</Text>
            <TextInput
              style={styles.input}
              value={vehicleModel}
              onChangeText={setVehicleModel}
              placeholder="Prius"
              placeholderTextColor="#999"
              autoCapitalize="words"
            />

            {/* Vehicle Plate */}
            <Text style={styles.label}>MATRÍCULA *</Text>
            <TextInput
              style={styles.input}
              value={vehiclePlate}
              onChangeText={setVehiclePlate}
              placeholder="1234ABC"
              placeholderTextColor="#999"
              autoCapitalize="characters"
            />
            <Text style={styles.hint}>Se guardará en mayúsculas</Text>

            {/* Vehicle License Number */}
            <Text style={styles.label}>Nº LICENCIA VEHÍCULO</Text>
            <TextInput
              style={styles.input}
              value={vehicleLicenseNumber}
              onChangeText={setVehicleLicenseNumber}
              placeholder="VH001"
              placeholderTextColor="#999"
            />
          </View>
        </ScrollView>

        {/* Save Button */}
        <View style={styles.footer}>
          <TouchableOpacity
            style={[styles.saveButton, saving && styles.saveButtonDisabled]}
            onPress={handleSave}
            disabled={saving}
          >
            {saving ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.saveButtonText}>Guardar Cambios</Text>
            )}
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F4',
  },
  keyboardView: {
    flex: 1,
  },
  scroll: {
    flex: 1,
  },
  form: {
    padding: 20,
  },
  infoCard: {
    backgroundColor: '#EFF6FF',
    padding: 16,
    borderRadius: 8,
    marginBottom: 8,
  },
  infoText: {
    fontSize: 14,
    color: '#1E40AF',
  },
  label: {
    fontSize: 12,
    fontWeight: '600',
    color: '#57534E',
    marginBottom: 8,
    marginTop: 16,
    letterSpacing: 1,
  },
  input: {
    height: 50,
    backgroundColor: '#fff',
    borderRadius: 8,
    paddingHorizontal: 16,
    fontSize: 16,
    color: '#1C1917',
    borderWidth: 1,
    borderColor: '#E7E5E4',
  },
  hint: {
    fontSize: 12,
    color: '#A8A29E',
    marginTop: 4,
  },
  footer: {
    padding: 20,
    borderTopWidth: 1,
    borderTopColor: '#E7E5E4',
    backgroundColor: '#fff',
  },
  saveButton: {
    height: 50,
    backgroundColor: '#7A1F1F',
    borderRadius: 25,
    justifyContent: 'center',
    alignItems: 'center',
  },
  saveButtonDisabled: {
    opacity: 0.7,
  },
  saveButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
});
