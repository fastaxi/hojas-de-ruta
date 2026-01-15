/**
 * RutasFast Mobile - Home Screen (Nueva Hoja de Ruta)
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
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';
import api from '../services/api';
import { ENDPOINTS } from '../services/config';
import { useAuth } from '../contexts/AuthContext';

export default function HomeScreen({ navigation }) {
  const { user } = useAuth();
  const [loading, setLoading] = useState(false);
  const [drivers, setDrivers] = useState([]);
  const [selectedDriver, setSelectedDriver] = useState(null);
  
  const [formData, setFormData] = useState({
    contractor_name: '',
    contractor_phone: '',
    prebooked_at: '',
    prebooked_name: '',
    prebooked_phone: '',
    pickup_address: '',
    pickup_datetime: new Date().toISOString(),
    destination: '',
  });

  useEffect(() => {
    loadDrivers();
  }, []);

  const loadDrivers = async () => {
    try {
      const response = await api.get(ENDPOINTS.DRIVERS);
      setDrivers(response.data);
    } catch (error) {
      console.error('Error loading drivers:', error);
    }
  };

  const updateField = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async () => {
    if (!formData.pickup_address || !formData.destination) {
      Alert.alert('Error', 'Origen y destino son obligatorios');
      return;
    }

    setLoading(true);
    try {
      const payload = {
        ...formData,
        conductor_driver_id: selectedDriver || undefined,
      };
      
      const response = await api.post(ENDPOINTS.ROUTE_SHEETS, payload);
      
      Alert.alert(
        'Hoja Creada',
        `Hoja de ruta #${response.data.seq_number} creada correctamente`,
        [{ 
          text: 'Ver Histórico', 
          onPress: () => navigation.navigate('History') 
        }]
      );
      
      // Reset form
      setFormData({
        contractor_name: '',
        contractor_phone: '',
        prebooked_at: '',
        prebooked_name: '',
        prebooked_phone: '',
        pickup_address: '',
        pickup_datetime: new Date().toISOString(),
        destination: '',
      });
      setSelectedDriver(null);
    } catch (error) {
      const message = error.response?.data?.detail || 'Error al crear la hoja';
      Alert.alert('Error', message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <ScrollView style={styles.scroll} showsVerticalScrollIndicator={false}>
        <View style={styles.header}>
          <Text style={styles.greeting}>Hola, {user?.full_name?.split(' ')[0]}</Text>
          <Text style={styles.date}>
            {format(new Date(), "EEEE, d 'de' MMMM", { locale: es })}
          </Text>
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Nueva Hoja de Ruta</Text>

          {/* Conductor */}
          <Text style={styles.sectionTitle}>Conductor</Text>
          <View style={styles.driverButtons}>
            <TouchableOpacity
              style={[
                styles.driverButton,
                !selectedDriver && styles.driverButtonActive,
              ]}
              onPress={() => setSelectedDriver(null)}
            >
              <Text style={[
                styles.driverButtonText,
                !selectedDriver && styles.driverButtonTextActive,
              ]}>
                Yo ({user?.full_name?.split(' ')[0]})
              </Text>
            </TouchableOpacity>
            {drivers.map((driver) => (
              <TouchableOpacity
                key={driver.id}
                style={[
                  styles.driverButton,
                  selectedDriver === driver.id && styles.driverButtonActive,
                ]}
                onPress={() => setSelectedDriver(driver.id)}
              >
                <Text style={[
                  styles.driverButtonText,
                  selectedDriver === driver.id && styles.driverButtonTextActive,
                ]}>
                  {driver.full_name.split(' ')[0]}
                </Text>
              </TouchableOpacity>
            ))}
          </View>

          {/* Contratante */}
          <Text style={styles.sectionTitle}>Contratante (opcional)</Text>
          <TextInput
            style={styles.input}
            value={formData.contractor_name}
            onChangeText={(v) => updateField('contractor_name', v)}
            placeholder="Nombre del contratante"
            placeholderTextColor="#999"
          />
          <TextInput
            style={styles.input}
            value={formData.contractor_phone}
            onChangeText={(v) => updateField('contractor_phone', v)}
            placeholder="Teléfono"
            placeholderTextColor="#999"
            keyboardType="phone-pad"
          />

          {/* Servicio */}
          <Text style={styles.sectionTitle}>Datos del Servicio *</Text>
          <TextInput
            style={styles.input}
            value={formData.pickup_address}
            onChangeText={(v) => updateField('pickup_address', v)}
            placeholder="Dirección de origen *"
            placeholderTextColor="#999"
          />
          <TextInput
            style={styles.input}
            value={formData.destination}
            onChangeText={(v) => updateField('destination', v)}
            placeholder="Destino *"
            placeholderTextColor="#999"
          />

          {/* Submit */}
          <TouchableOpacity
            style={[styles.submitButton, loading && styles.submitButtonDisabled]}
            onPress={handleSubmit}
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.submitButtonText}>Crear Hoja de Ruta</Text>
            )}
          </TouchableOpacity>
        </View>
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
  greeting: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#1C1917',
  },
  date: {
    fontSize: 16,
    color: '#57534E',
    textTransform: 'capitalize',
  },
  card: {
    backgroundColor: '#fff',
    borderRadius: 16,
    margin: 16,
    marginTop: 0,
    padding: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  cardTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#1C1917',
    marginBottom: 20,
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#7A1F1F',
    marginBottom: 12,
    marginTop: 8,
  },
  driverButtons: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginBottom: 16,
  },
  driverButton: {
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 20,
    backgroundColor: '#F5F5F4',
    borderWidth: 1,
    borderColor: '#E7E5E4',
  },
  driverButtonActive: {
    backgroundColor: '#7A1F1F',
    borderColor: '#7A1F1F',
  },
  driverButtonText: {
    fontSize: 14,
    color: '#57534E',
  },
  driverButtonTextActive: {
    color: '#fff',
  },
  input: {
    height: 50,
    backgroundColor: '#F5F5F4',
    borderRadius: 8,
    paddingHorizontal: 16,
    fontSize: 16,
    color: '#1C1917',
    marginBottom: 12,
  },
  submitButton: {
    height: 54,
    backgroundColor: '#7A1F1F',
    borderRadius: 27,
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 16,
  },
  submitButtonDisabled: {
    opacity: 0.7,
  },
  submitButtonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '600',
  },
});
