/**
 * RutasFast Mobile - Register Screen (Multi-step)
 */
import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuth } from '../contexts/AuthContext';

const STEPS = [
  { id: 1, title: 'Datos Personales' },
  { id: 2, title: 'Licencia' },
  { id: 3, title: 'Vehículo' },
  { id: 4, title: 'Credenciales' },
];

export default function RegisterScreen({ navigation }) {
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  
  const [formData, setFormData] = useState({
    // Step 1 - Personal
    full_name: '',
    dni_cif: '',
    phone: '',
    // Step 2 - License
    license_number: '',
    license_council: '',
    // Step 3 - Vehicle
    vehicle_brand: '',
    vehicle_model: '',
    vehicle_plate: '',
    vehicle_license_number: '',
    // Step 4 - Credentials
    email: '',
    password: '',
    confirmPassword: '',
  });

  const updateField = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const validateStep = () => {
    switch (step) {
      case 1:
        if (!formData.full_name || !formData.dni_cif || !formData.phone) {
          Alert.alert('Error', 'Completa todos los campos');
          return false;
        }
        break;
      case 2:
        if (!formData.license_number || !formData.license_council) {
          Alert.alert('Error', 'Completa todos los campos');
          return false;
        }
        break;
      case 3:
        if (!formData.vehicle_brand || !formData.vehicle_model || 
            !formData.vehicle_plate || !formData.vehicle_license_number) {
          Alert.alert('Error', 'Completa todos los campos');
          return false;
        }
        break;
      case 4:
        if (!formData.email || !formData.password || !formData.confirmPassword) {
          Alert.alert('Error', 'Completa todos los campos');
          return false;
        }
        if (formData.password !== formData.confirmPassword) {
          Alert.alert('Error', 'Las contraseñas no coinciden');
          return false;
        }
        if (formData.password.length < 8) {
          Alert.alert('Error', 'La contraseña debe tener al menos 8 caracteres');
          return false;
        }
        break;
    }
    return true;
  };

  const handleNext = () => {
    if (validateStep()) {
      if (step < 4) {
        setStep(step + 1);
      } else {
        handleSubmit();
      }
    }
  };

  const handleBack = () => {
    if (step > 1) {
      setStep(step - 1);
    } else {
      navigation.goBack();
    }
  };

  const handleSubmit = async () => {
    setLoading(true);
    try {
      const { confirmPassword, ...submitData } = formData;
      await register(submitData);
      Alert.alert(
        'Registro Enviado',
        'Tu solicitud está pendiente de aprobación. Recibirás acceso cuando un administrador apruebe tu cuenta.',
        [{ text: 'OK', onPress: () => navigation.navigate('Login') }]
      );
    } catch (error) {
      const message = error.response?.data?.detail || 'Error al registrar';
      Alert.alert('Error', message);
    } finally {
      setLoading(false);
    }
  };

  const renderStepContent = () => {
    switch (step) {
      case 1:
        return (
          <>
            <Text style={styles.label}>NOMBRE COMPLETO</Text>
            <TextInput
              style={styles.input}
              value={formData.full_name}
              onChangeText={(v) => updateField('full_name', v)}
              placeholder="Juan García López"
              placeholderTextColor="#999"
            />
            <Text style={styles.label}>DNI/CIF</Text>
            <TextInput
              style={styles.input}
              value={formData.dni_cif}
              onChangeText={(v) => updateField('dni_cif', v)}
              placeholder="12345678A"
              placeholderTextColor="#999"
              autoCapitalize="characters"
            />
            <Text style={styles.label}>TELÉFONO</Text>
            <TextInput
              style={styles.input}
              value={formData.phone}
              onChangeText={(v) => updateField('phone', v)}
              placeholder="612345678"
              placeholderTextColor="#999"
              keyboardType="phone-pad"
            />
          </>
        );
      case 2:
        return (
          <>
            <Text style={styles.label}>Nº LICENCIA</Text>
            <TextInput
              style={styles.input}
              value={formData.license_number}
              onChangeText={(v) => updateField('license_number', v)}
              placeholder="LIC001"
              placeholderTextColor="#999"
            />
            <Text style={styles.label}>AYUNTAMIENTO</Text>
            <TextInput
              style={styles.input}
              value={formData.license_council}
              onChangeText={(v) => updateField('license_council', v)}
              placeholder="Oviedo"
              placeholderTextColor="#999"
            />
          </>
        );
      case 3:
        return (
          <>
            <Text style={styles.label}>MARCA</Text>
            <TextInput
              style={styles.input}
              value={formData.vehicle_brand}
              onChangeText={(v) => updateField('vehicle_brand', v)}
              placeholder="Toyota"
              placeholderTextColor="#999"
            />
            <Text style={styles.label}>MODELO</Text>
            <TextInput
              style={styles.input}
              value={formData.vehicle_model}
              onChangeText={(v) => updateField('vehicle_model', v)}
              placeholder="Prius"
              placeholderTextColor="#999"
            />
            <Text style={styles.label}>MATRÍCULA</Text>
            <TextInput
              style={styles.input}
              value={formData.vehicle_plate}
              onChangeText={(v) => updateField('vehicle_plate', v)}
              placeholder="1234ABC"
              placeholderTextColor="#999"
              autoCapitalize="characters"
            />
            <Text style={styles.label}>Nº LICENCIA VEHÍCULO</Text>
            <TextInput
              style={styles.input}
              value={formData.vehicle_license_number}
              onChangeText={(v) => updateField('vehicle_license_number', v)}
              placeholder="VH001"
              placeholderTextColor="#999"
            />
          </>
        );
      case 4:
        return (
          <>
            <Text style={styles.label}>EMAIL</Text>
            <TextInput
              style={styles.input}
              value={formData.email}
              onChangeText={(v) => updateField('email', v)}
              placeholder="tu@email.com"
              placeholderTextColor="#999"
              keyboardType="email-address"
              autoCapitalize="none"
            />
            <Text style={styles.label}>CONTRASEÑA</Text>
            <TextInput
              style={styles.input}
              value={formData.password}
              onChangeText={(v) => updateField('password', v)}
              placeholder="Mínimo 8 caracteres"
              placeholderTextColor="#999"
              secureTextEntry
            />
            <Text style={styles.label}>CONFIRMAR CONTRASEÑA</Text>
            <TextInput
              style={styles.input}
              value={formData.confirmPassword}
              onChangeText={(v) => updateField('confirmPassword', v)}
              placeholder="Repite la contraseña"
              placeholderTextColor="#999"
              secureTextEntry
            />
          </>
        );
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.content}
      >
        {/* Progress */}
        <View style={styles.progress}>
          {STEPS.map((s) => (
            <View
              key={s.id}
              style={[
                styles.progressDot,
                s.id <= step && styles.progressDotActive,
              ]}
            />
          ))}
        </View>

        <Text style={styles.stepTitle}>{STEPS[step - 1].title}</Text>
        <Text style={styles.stepSubtitle}>Paso {step} de 4</Text>

        <ScrollView style={styles.form} showsVerticalScrollIndicator={false}>
          {renderStepContent()}
        </ScrollView>

        <View style={styles.buttons}>
          <TouchableOpacity style={styles.backButton} onPress={handleBack}>
            <Text style={styles.backButtonText}>
              {step === 1 ? 'Cancelar' : 'Atrás'}
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.nextButton, loading && styles.buttonDisabled]}
            onPress={handleNext}
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.nextButtonText}>
                {step === 4 ? 'Enviar' : 'Siguiente'}
              </Text>
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
    backgroundColor: '#1C1917',
  },
  content: {
    flex: 1,
    padding: 24,
  },
  progress: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 8,
    marginBottom: 24,
  },
  progressDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
    backgroundColor: '#57534E',
  },
  progressDotActive: {
    backgroundColor: '#7A1F1F',
  },
  stepTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#fff',
    textAlign: 'center',
  },
  stepSubtitle: {
    fontSize: 14,
    color: '#A8A29E',
    textAlign: 'center',
    marginBottom: 24,
  },
  form: {
    flex: 1,
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 24,
  },
  label: {
    fontSize: 12,
    fontWeight: '600',
    color: '#57534E',
    marginBottom: 8,
    letterSpacing: 1,
  },
  input: {
    height: 50,
    backgroundColor: '#F5F5F4',
    borderRadius: 8,
    paddingHorizontal: 16,
    fontSize: 16,
    color: '#1C1917',
    marginBottom: 16,
  },
  buttons: {
    flexDirection: 'row',
    gap: 12,
    marginTop: 16,
  },
  backButton: {
    flex: 1,
    height: 50,
    borderRadius: 25,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#57534E',
  },
  backButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  nextButton: {
    flex: 2,
    height: 50,
    borderRadius: 25,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#7A1F1F',
  },
  nextButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  buttonDisabled: {
    opacity: 0.7,
  },
});
