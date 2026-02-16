/**
 * RutasFast Mobile - Profile Screen
 * Edit user profile (name, DNI, license, phone)
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
  validateProfile,
  normalizeTrim,
  normalizeUpper,
  normalizeTrimOrNull,
} from '../utils/validators';

export default function ProfileScreen({ navigation }) {
  const { user, refreshUser } = useAuth();
  const [saving, setSaving] = useState(false);

  // Form state
  const [fullName, setFullName] = useState('');
  const [dniCif, setDniCif] = useState('');
  const [licenseNumber, setLicenseNumber] = useState('');
  const [licenseCouncil, setLicenseCouncil] = useState('');
  const [phone, setPhone] = useState('');

  // Initialize form with user data
  useEffect(() => {
    if (user) {
      setFullName(user.full_name || '');
      setDniCif(user.dni_cif || '');
      setLicenseNumber(user.license_number || '');
      setLicenseCouncil(user.license_council || '');
      setPhone(user.phone || '');
    }
  }, [user]);

  const handleSave = async () => {
    const payload = {
      full_name: normalizeTrim(fullName),
      dni_cif: normalizeUpper(dniCif),
      license_number: normalizeTrimOrNull(licenseNumber),
      license_council: normalizeTrimOrNull(licenseCouncil),
      phone: normalizeTrimOrNull(phone),
    };

    // Validate
    const validation = validateProfile(payload);
    if (!validation.ok) {
      Alert.alert('Error', validation.msg);
      return;
    }

    setSaving(true);
    try {
      await updateMe(payload);
      await refreshUser();
      Alert.alert('Éxito', 'Perfil actualizado correctamente', [
        {
          text: 'OK',
          onPress: () => {
            // Safe navigation: check if we can go back, otherwise go to main screen
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
      const message = error.response?.data?.detail || 'Error al guardar el perfil';
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
            {/* Email (read-only) */}
            <Text style={styles.label}>EMAIL</Text>
            <View style={styles.readOnlyInput}>
              <Text style={styles.readOnlyText}>{user?.email}</Text>
            </View>
            <Text style={styles.hint}>El email no se puede modificar</Text>

            {/* Full Name */}
            <Text style={styles.label}>NOMBRE COMPLETO *</Text>
            <TextInput
              style={styles.input}
              value={fullName}
              onChangeText={setFullName}
              placeholder="Juan García López"
              placeholderTextColor="#999"
              autoCapitalize="words"
            />

            {/* DNI/CIF */}
            <Text style={styles.label}>DNI/CIF *</Text>
            <TextInput
              style={styles.input}
              value={dniCif}
              onChangeText={setDniCif}
              placeholder="12345678A"
              placeholderTextColor="#999"
              autoCapitalize="characters"
            />
            <Text style={styles.hint}>Se guardará en mayúsculas</Text>

            {/* License Number */}
            <Text style={styles.label}>Nº LICENCIA</Text>
            <TextInput
              style={styles.input}
              value={licenseNumber}
              onChangeText={setLicenseNumber}
              placeholder="LIC001"
              placeholderTextColor="#999"
            />

            {/* License Council */}
            <Text style={styles.label}>AYUNTAMIENTO</Text>
            <TextInput
              style={styles.input}
              value={licenseCouncil}
              onChangeText={setLicenseCouncil}
              placeholder="Oviedo"
              placeholderTextColor="#999"
            />

            {/* Phone */}
            <Text style={styles.label}>TELÉFONO</Text>
            <TextInput
              style={styles.input}
              value={phone}
              onChangeText={setPhone}
              placeholder="612345678"
              placeholderTextColor="#999"
              keyboardType="phone-pad"
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
  readOnlyInput: {
    height: 50,
    backgroundColor: '#E7E5E4',
    borderRadius: 8,
    paddingHorizontal: 16,
    justifyContent: 'center',
  },
  readOnlyText: {
    fontSize: 16,
    color: '#57534E',
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
