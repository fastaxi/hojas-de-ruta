/**
 * RutasFast Mobile - History Screen
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  RefreshControl,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';
import * as Print from 'expo-print';
import * as Sharing from 'expo-sharing';
import api from '../services/api';
import { ENDPOINTS, API_BASE_URL } from '../services/config';
import { tokenService } from '../services/api';

export default function HistoryScreen() {
  const [sheets, setSheets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [filter, setFilter] = useState('all'); // all, active, annulled

  const loadSheets = useCallback(async () => {
    try {
      const params = {};
      if (filter === 'active') params.status = 'ACTIVE';
      if (filter === 'annulled') params.status = 'ANNULLED';
      
      const response = await api.get(ENDPOINTS.ROUTE_SHEETS, { params });
      setSheets(response.data);
    } catch (error) {
      console.error('Error loading sheets:', error);
      Alert.alert('Error', 'No se pudieron cargar las hojas de ruta');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [filter]);

  useEffect(() => {
    loadSheets();
  }, [loadSheets]);

  const onRefresh = () => {
    setRefreshing(true);
    loadSheets();
  };

  const handleDownloadPdf = async (sheet) => {
    try {
      const token = await tokenService.getAccessToken();
      const pdfUrl = `${API_BASE_URL}${ENDPOINTS.ROUTE_SHEETS}/${sheet.id}/pdf`;
      
      // For now, open in browser or share
      Alert.alert(
        'Descargar PDF',
        `Hoja #${sheet.seq_number}/${sheet.year}`,
        [
          { text: 'Cancelar', style: 'cancel' },
          { 
            text: 'Compartir', 
            onPress: async () => {
              // Use expo-sharing
              if (await Sharing.isAvailableAsync()) {
                // Would need to download file first
                Alert.alert('Info', 'Funcionalidad de compartir en desarrollo');
              }
            }
          },
        ]
      );
    } catch (error) {
      Alert.alert('Error', 'No se pudo descargar el PDF');
    }
  };

  const handleAnnul = async (sheet) => {
    Alert.alert(
      'Anular Hoja',
      `¿Estás seguro de anular la hoja #${sheet.seq_number}/${sheet.year}?`,
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'Anular',
          style: 'destructive',
          onPress: async () => {
            try {
              await api.post(`${ENDPOINTS.ROUTE_SHEETS}/${sheet.id}/annul`, {
                reason: 'Anulada por el usuario',
              });
              loadSheets();
              Alert.alert('Éxito', 'Hoja anulada correctamente');
            } catch (error) {
              Alert.alert('Error', 'No se pudo anular la hoja');
            }
          },
        },
      ]
    );
  };

  const renderSheet = ({ item }) => (
    <View style={styles.sheetCard}>
      <View style={styles.sheetHeader}>
        <View>
          <Text style={styles.sheetNumber}>
            #{item.seq_number}/{item.year}
          </Text>
          <Text style={styles.sheetDate}>
            {format(new Date(item.created_at), "d MMM yyyy, HH:mm", { locale: es })}
          </Text>
        </View>
        <View style={[
          styles.statusBadge,
          item.status === 'ANNULLED' && styles.statusBadgeAnnulled,
        ]}>
          <Text style={[
            styles.statusText,
            item.status === 'ANNULLED' && styles.statusTextAnnulled,
          ]}>
            {item.status === 'ACTIVE' ? 'Activa' : 'Anulada'}
          </Text>
        </View>
      </View>

      <View style={styles.sheetBody}>
        <Text style={styles.sheetLabel}>Origen</Text>
        <Text style={styles.sheetValue}>{item.pickup_address}</Text>
        
        <Text style={styles.sheetLabel}>Destino</Text>
        <Text style={styles.sheetValue}>{item.destination}</Text>
      </View>

      <View style={styles.sheetActions}>
        <TouchableOpacity
          style={styles.actionButton}
          onPress={() => handleDownloadPdf(item)}
        >
          <Text style={styles.actionButtonText}>PDF</Text>
        </TouchableOpacity>
        
        {item.status === 'ACTIVE' && (
          <TouchableOpacity
            style={[styles.actionButton, styles.actionButtonDanger]}
            onPress={() => handleAnnul(item)}
          >
            <Text style={[styles.actionButtonText, styles.actionButtonTextDanger]}>
              Anular
            </Text>
          </TouchableOpacity>
        )}
      </View>
    </View>
  );

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#7A1F1F" />
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.header}>
        <Text style={styles.title}>Histórico</Text>
        <Text style={styles.subtitle}>{sheets.length} hojas de ruta</Text>
      </View>

      {/* Filters */}
      <View style={styles.filters}>
        {['all', 'active', 'annulled'].map((f) => (
          <TouchableOpacity
            key={f}
            style={[styles.filterButton, filter === f && styles.filterButtonActive]}
            onPress={() => setFilter(f)}
          >
            <Text style={[
              styles.filterButtonText,
              filter === f && styles.filterButtonTextActive,
            ]}>
              {f === 'all' ? 'Todas' : f === 'active' ? 'Activas' : 'Anuladas'}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      <FlatList
        data={sheets}
        renderItem={renderSheet}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.list}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Text style={styles.emptyText}>No hay hojas de ruta</Text>
          </View>
        }
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F4',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
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
  subtitle: {
    fontSize: 16,
    color: '#57534E',
  },
  filters: {
    flexDirection: 'row',
    paddingHorizontal: 16,
    gap: 8,
    marginBottom: 16,
  },
  filterButton: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#E7E5E4',
  },
  filterButtonActive: {
    backgroundColor: '#7A1F1F',
    borderColor: '#7A1F1F',
  },
  filterButtonText: {
    fontSize: 14,
    color: '#57534E',
  },
  filterButtonTextActive: {
    color: '#fff',
  },
  list: {
    padding: 16,
    paddingTop: 0,
  },
  sheetCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 1,
  },
  sheetHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  sheetNumber: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#1C1917',
  },
  sheetDate: {
    fontSize: 14,
    color: '#57534E',
  },
  statusBadge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
    backgroundColor: '#D1FAE5',
  },
  statusBadgeAnnulled: {
    backgroundColor: '#FEE2E2',
  },
  statusText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#065F46',
  },
  statusTextAnnulled: {
    color: '#991B1B',
  },
  sheetBody: {
    marginBottom: 12,
  },
  sheetLabel: {
    fontSize: 12,
    color: '#57534E',
    marginBottom: 2,
  },
  sheetValue: {
    fontSize: 15,
    color: '#1C1917',
    marginBottom: 8,
  },
  sheetActions: {
    flexDirection: 'row',
    gap: 8,
    borderTopWidth: 1,
    borderTopColor: '#E7E5E4',
    paddingTop: 12,
  },
  actionButton: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 6,
    backgroundColor: '#7A1F1F',
  },
  actionButtonDanger: {
    backgroundColor: '#FEE2E2',
  },
  actionButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#fff',
  },
  actionButtonTextDanger: {
    color: '#991B1B',
  },
  emptyContainer: {
    padding: 40,
    alignItems: 'center',
  },
  emptyText: {
    fontSize: 16,
    color: '#57534E',
  },
});
