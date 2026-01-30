/**
 * RutasFast Mobile - Change Password Screen
 */
import React, { useState } from 'react';
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
import { changePassword } from '../services/meService';
import { validatePasswordChange } from '../utils/validators';

export default function ChangePasswordScreen({ navigation }) {
  const [saving, setSaving] = useState(false);
  
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  const handleSave = async () => {
    // Validate
    const validation = validatePasswordChange({
      current_password: currentPassword,
      new_password: newPassword,
      confirm_password: confirmPassword,
    });
    
    if (!validation.ok) {
      Alert.alert('Error', validation.msg);
      return;
    }

    setSaving(true);
    try {
      await changePassword(currentPassword, newPassword);
      Alert.alert('Éxito', 'Contraseña actualizada correctamente', [
        { text: 'OK', onPress: () => navigation.goBack() }
      ]);
    } catch (error) {
      const status = error.response?.status;
      let message = 'Error al cambiar la contraseña';
      
      if (status === 400) {
        message = 'La contraseña actual es incorrecta';
      } else if (error.response?.data?.detail) {
        message = error.response.data.detail;
      }
      
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
            {/* Info */}
            <View style={styles.infoCard}>
              <Text style={styles.infoText}>
                La nueva contraseña debe tener al menos 8 caracteres.
              </Text>
            </View>

            {/* Current Password */}
            <Text style={styles.label}>CONTRASEÑA ACTUAL</Text>
            <TextInput
              style={styles.input}
              value={currentPassword}
              onChangeText={setCurrentPassword}
              placeholder="••••••••"
              placeholderTextColor="#999"
              secureTextEntry
            />

            {/* New Password */}
            <Text style={styles.label}>NUEVA CONTRASEÑA</Text>
            <TextInput
              style={styles.input}
              value={newPassword}
              onChangeText={setNewPassword}
              placeholder="Mínimo 8 caracteres"
              placeholderTextColor="#999"
              secureTextEntry
            />

            {/* Confirm Password */}
            <Text style={styles.label}>CONFIRMAR NUEVA CONTRASEÑA</Text>
            <TextInput
              style={styles.input}
              value={confirmPassword}
              onChangeText={setConfirmPassword}
              placeholder="Repite la nueva contraseña"
              placeholderTextColor="#999"
              secureTextEntry
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
              <Text style={styles.saveButtonText}>Cambiar Contraseña</Text>
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
    backgroundColor: '#FEF3C7',
    padding: 16,
    borderRadius: 8,
    marginBottom: 8,
  },
  infoText: {
    fontSize: 14,
    color: '#92400E',
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
