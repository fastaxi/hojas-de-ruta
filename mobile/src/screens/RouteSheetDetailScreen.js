/**
 * RutasFast Mobile - Route Sheet Detail Screen
 * Shows complete route sheet information
 */
import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import api from '../services/api';
import { ENDPOINTS } from '../services/config';
import { useAuth } from '../contexts/AuthContext';
import { formatDateTimeES } from '../utils/dateFormat';
import { usePdfView } from '../hooks/usePdfView';
import { usePdfShare } from '../hooks/usePdfShare';

export default function RouteSheetDetailScreen({ navigation, route }) {
  const { sheetId } = route.params;
  const { user } = useAuth();
  
  const [sheet, setSheet] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  const { viewPdf, isViewingPdf } = usePdfView();
  const { shareSheetPdf, isPreparingSheet } = usePdfShare();

  useEffect(() => {
    loadSheetDetails();
  }, [sheetId]);

  const loadSheetDetails = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await api.get(`${ENDPOINTS.ROUTE_SHEETS}/${sheetId}`);
      setSheet(response.data);
      
    } catch (err) {
      console.log('[Detail] Error loading sheet:', err.message, err.response?.status);
      
      if (err.response?.status === 401 || err.response?.status === 403) {
        Alert.alert('Sesión caducada', 'Por favor, vuelve a iniciar sesión', [
          { text: 'OK', onPress: () => navigation.navigate('Login') }
        ]);
        return;
      }
      
      setError(err.message || 'Error al cargar la hoja');
    } finally {
      setLoading(false);
    }
  };

  const getSheetNumber = () => {
    if (sheet?.sheet_number) return sheet.sheet_number;
    if (sheet?.seq_number && sheet?.year) {
      return `${String(sheet.seq_number).padStart(3, '0')}/${sheet.year}`;
    }
    return '---';
  };

  const getDriverName = () => {
    if (!sheet?.conductor_driver_id) return 'Titular';
    
    // Find driver in user's drivers array
    const driver = user?.drivers?.find(d => d.id === sheet.conductor_driver_id);
    if (driver) {
      return `${driver.full_name} (${driver.dni_cif})`;
    }
    return 'Conductor asignado';
  };

  const handleViewPdf = () => {
    viewPdf(sheetId, getSheetNumber());
  };

  const handleSharePdf = () => {
    shareSheetPdf(sheetId, getSheetNumber());
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.container} edges={['top']}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#7A1F1F" />
          <Text style={styles.loadingText}>Cargando hoja...</Text>
        </View>
      </SafeAreaView>
    );
  }

  if (error) {
    return (
      <SafeAreaView style={styles.container} edges={['top']}>
        <View style={styles.errorContainer}>
          <Text style={styles.errorText}>{error}</Text>
          <TouchableOpacity style={styles.retryButton} onPress={loadSheetDetails}>
            <Text style={styles.retryButtonText}>Reintentar</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  const isAnnulled = sheet?.status === 'ANNULLED';
  const sheetNumber = getSheetNumber();

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <ScrollView style={styles.scroll} showsVerticalScrollIndicator={false}>
        
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.sheetNumberLabel}>Hoja Nº</Text>
          <Text style={styles.sheetNumber}>{sheetNumber}</Text>
          <View style={[styles.statusBadge, isAnnulled && styles.statusBadgeAnnulled]}>
            <Text style={[styles.statusText, isAnnulled && styles.statusTextAnnulled]}>
              {isAnnulled ? 'ANULADA' : 'ACTIVA'}
            </Text>
          </View>
        </View>

        {/* Titular y Vehículo */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>DATOS DEL TITULAR Y VEHÍCULO</Text>
          
          <View style={styles.row}>
            <Text style={styles.label}>Titular:</Text>
            <Text style={styles.value}>{user?.full_name || '-'}</Text>
          </View>
          <View style={styles.row}>
            <Text style={styles.label}>DNI/CIF:</Text>
            <Text style={styles.value}>{user?.dni_cif || '-'}</Text>
          </View>
          <View style={styles.row}>
            <Text style={styles.label}>Nº Licencia:</Text>
            <Text style={styles.value}>{user?.license_number || '-'}</Text>
          </View>
          <View style={styles.row}>
            <Text style={styles.label}>Concejo:</Text>
            <Text style={styles.value}>{user?.license_council || '-'}</Text>
          </View>
          <View style={styles.row}>
            <Text style={styles.label}>Teléfono:</Text>
            <Text style={styles.value}>{user?.phone || '-'}</Text>
          </View>
          <View style={styles.row}>
            <Text style={styles.label}>Vehículo:</Text>
            <Text style={styles.value}>
              {user?.vehicle_brand} {user?.vehicle_model}
            </Text>
          </View>
          <View style={styles.row}>
            <Text style={styles.label}>Matrícula:</Text>
            <Text style={styles.value}>{user?.vehicle_plate || '-'}</Text>
          </View>
          {user?.vehicle_license_number && (
            <View style={styles.row}>
              <Text style={styles.label}>Lic. Vehículo:</Text>
              <Text style={styles.value}>{user.vehicle_license_number}</Text>
            </View>
          )}
          <View style={styles.row}>
            <Text style={styles.label}>Conductor:</Text>
            <Text style={styles.value}>{getDriverName()}</Text>
          </View>
        </View>

        {/* Contratación */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>DATOS DE CONTRATACIÓN</Text>
          
          <View style={styles.row}>
            <Text style={styles.label}>Contratante:</Text>
            <Text style={styles.value}>
              {sheet?.contractor_phone ? `Tel: ${sheet.contractor_phone}` : ''}
              {sheet?.contractor_phone && sheet?.contractor_email ? ' / ' : ''}
              {sheet?.contractor_email || ''}
              {!sheet?.contractor_phone && !sheet?.contractor_email ? '-' : ''}
            </Text>
          </View>
          <View style={styles.row}>
            <Text style={styles.label}>Fecha precontratación:</Text>
            <Text style={styles.value}>{formatDateTimeES(sheet?.prebooked_date)}</Text>
          </View>
          <View style={styles.row}>
            <Text style={styles.label}>Localidad:</Text>
            <Text style={styles.value}>{sheet?.prebooked_locality || '-'}</Text>
          </View>
        </View>

        {/* Servicio */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>DATOS DEL SERVICIO</Text>
          
          <View style={styles.row}>
            <Text style={styles.label}>Tipo recogida:</Text>
            <Text style={styles.value}>
              {sheet?.pickup_type === 'AIRPORT' ? 'Aeropuerto' : 'Otra dirección'}
            </Text>
          </View>
          <View style={styles.row}>
            <Text style={styles.label}>Lugar recogida:</Text>
            <Text style={styles.value}>
              {sheet?.pickup_type === 'AIRPORT' 
                ? `Aeropuerto de Asturias` 
                : sheet?.pickup_address || '-'}
            </Text>
          </View>
          {sheet?.pickup_type === 'AIRPORT' && sheet?.flight_number && (
            <View style={styles.row}>
              <Text style={styles.label}>Nº Vuelo:</Text>
              <Text style={styles.value}>{sheet.flight_number}</Text>
            </View>
          )}
          <View style={styles.row}>
            <Text style={styles.label}>Fecha y hora:</Text>
            <Text style={styles.value}>{formatDateTimeES(sheet?.pickup_datetime)}</Text>
          </View>
          <View style={styles.row}>
            <Text style={styles.label}>Destino:</Text>
            <Text style={styles.value}>{sheet?.destination || '-'}</Text>
          </View>
          <View style={styles.row}>
            <Text style={styles.label}>Pasajero(s):</Text>
            <Text style={styles.value}>{sheet?.passenger_info || '-'}</Text>
          </View>
        </View>

        {/* Anulación (si aplica) */}
        {isAnnulled && (
          <View style={[styles.section, styles.sectionAnnulled]}>
            <Text style={[styles.sectionTitle, styles.sectionTitleAnnulled]}>
              HOJA ANULADA
            </Text>
            
            <View style={styles.row}>
              <Text style={[styles.label, styles.labelAnnulled]}>Motivo:</Text>
              <Text style={[styles.value, styles.valueAnnulled]}>
                {sheet?.annul_reason || 'No especificado'}
              </Text>
            </View>
            {sheet?.annulled_at && (
              <View style={styles.row}>
                <Text style={[styles.label, styles.labelAnnulled]}>Fecha anulación:</Text>
                <Text style={[styles.value, styles.valueAnnulled]}>
                  {formatDateTimeES(sheet.annulled_at)}
                </Text>
              </View>
            )}
          </View>
        )}

        {/* Spacer for buttons */}
        <View style={{ height: 100 }} />
      </ScrollView>

      {/* Footer buttons */}
      <View style={styles.footer}>
        <TouchableOpacity
          style={styles.primaryButton}
          onPress={handleViewPdf}
          disabled={isViewingPdf(sheetId)}
        >
          {isViewingPdf(sheetId) ? (
            <ActivityIndicator color="#fff" size="small" />
          ) : (
            <Text style={styles.primaryButtonText}>Ver PDF</Text>
          )}
        </TouchableOpacity>
        
        <TouchableOpacity
          style={styles.secondaryButton}
          onPress={handleSharePdf}
          disabled={isPreparingSheet(sheetId)}
        >
          {isPreparingSheet(sheetId) ? (
            <ActivityIndicator color="#7A1F1F" size="small" />
          ) : (
            <Text style={styles.secondaryButtonText}>Compartir PDF</Text>
          )}
        </TouchableOpacity>
      </View>
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
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 12,
    fontSize: 16,
    color: '#78716C',
  },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  errorText: {
    fontSize: 16,
    color: '#DC2626',
    textAlign: 'center',
    marginBottom: 16,
  },
  retryButton: {
    backgroundColor: '#7A1F1F',
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 8,
  },
  retryButtonText: {
    color: '#fff',
    fontWeight: '600',
  },
  header: {
    backgroundColor: '#7A1F1F',
    padding: 20,
    alignItems: 'center',
  },
  sheetNumberLabel: {
    color: 'rgba(255,255,255,0.7)',
    fontSize: 14,
  },
  sheetNumber: {
    color: '#fff',
    fontSize: 32,
    fontWeight: 'bold',
    marginVertical: 8,
  },
  statusBadge: {
    backgroundColor: 'rgba(255,255,255,0.2)',
    paddingHorizontal: 16,
    paddingVertical: 6,
    borderRadius: 20,
  },
  statusBadgeAnnulled: {
    backgroundColor: '#DC2626',
  },
  statusText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 12,
  },
  statusTextAnnulled: {
    color: '#fff',
  },
  section: {
    backgroundColor: '#fff',
    margin: 16,
    marginBottom: 0,
    borderRadius: 12,
    padding: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 1,
  },
  sectionAnnulled: {
    backgroundColor: '#FEE2E2',
    borderWidth: 1,
    borderColor: '#DC2626',
  },
  sectionTitle: {
    fontSize: 12,
    fontWeight: '700',
    color: '#7A1F1F',
    marginBottom: 12,
    letterSpacing: 0.5,
  },
  sectionTitleAnnulled: {
    color: '#DC2626',
  },
  row: {
    flexDirection: 'row',
    paddingVertical: 6,
    borderBottomWidth: 1,
    borderBottomColor: '#F5F5F4',
  },
  label: {
    flex: 0.4,
    fontSize: 13,
    color: '#78716C',
    fontWeight: '500',
  },
  labelAnnulled: {
    color: '#991B1B',
  },
  value: {
    flex: 0.6,
    fontSize: 13,
    color: '#1C1917',
  },
  valueAnnulled: {
    color: '#991B1B',
  },
  footer: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    backgroundColor: '#fff',
    padding: 16,
    paddingBottom: 24,
    flexDirection: 'row',
    gap: 12,
    borderTopWidth: 1,
    borderTopColor: '#E7E5E4',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: -2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 5,
  },
  primaryButton: {
    flex: 1,
    backgroundColor: '#7A1F1F',
    height: 48,
    borderRadius: 24,
    justifyContent: 'center',
    alignItems: 'center',
  },
  primaryButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  secondaryButton: {
    flex: 1,
    backgroundColor: '#fff',
    height: 48,
    borderRadius: 24,
    borderWidth: 2,
    borderColor: '#7A1F1F',
    justifyContent: 'center',
    alignItems: 'center',
  },
  secondaryButtonText: {
    color: '#7A1F1F',
    fontSize: 16,
    fontWeight: '600',
  },
});
