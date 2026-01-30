/**
 * RutasFast Mobile - History Screen
 * Route sheets list with PDF download and sharing
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
  Modal,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';
import api from '../services/api';
import { ENDPOINTS } from '../services/config';
import { usePdfShare } from '../hooks/usePdfShare';

export default function HistoryScreen() {
  const [sheets, setSheets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [filter, setFilter] = useState('all'); // all, active, annulled
  const [selectedSheet, setSelectedSheet] = useState(null);
  const [showRangeModal, setShowRangeModal] = useState(false);

  const { 
    loading: pdfLoading, 
    loadingSheetId, 
    shareSheetPdf,
    downloadSheetPdf,
    shareRangePdf 
  } = usePdfShare();

  const loadSheets = useCallback(async () => {
    try {
      const params = {};
      if (filter === 'active') params.status = 'ACTIVE';
      if (filter === 'annulled') params.status = 'ANNULLED';
      
      const response = await api.get(ENDPOINTS.ROUTE_SHEETS, { params });
      setSheets(response.data);
    } catch (error) {
      console.error('Error loading sheets:', error);
      if (error.response?.status !== 401) {
        Alert.alert('Error', 'No se pudieron cargar las hojas de ruta');
      }
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

  const handleSharePdf = async (sheet) => {
    await shareSheetPdf(sheet);
  };

  const handleDownloadPdf = async (sheet) => {
    await downloadSheetPdf(sheet);
  };

  const handleAnnul = async (sheet) => {
    Alert.alert(
      'Anular Hoja',
      `¿Estás seguro de anular la hoja #${sheet.seq_number}/${sheet.year}?\n\nEsta acción no se puede deshacer.`,
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'Anular',
          style: 'destructive',
          onPress: async () => {
            try {
              await api.post(`${ENDPOINTS.ROUTE_SHEETS}/${sheet.id}/annul`, {
                reason: 'Anulada por el usuario desde la app móvil',
              });
              loadSheets();
              Alert.alert('Éxito', 'Hoja anulada correctamente');
            } catch (error) {
              const message = error.response?.data?.detail || 'No se pudo anular la hoja';
              Alert.alert('Error', message);
            }
          },
        },
      ]
    );
  };

  const showSheetOptions = (sheet) => {
    const options = [
      { text: 'Cancelar', style: 'cancel' },
      { 
        text: 'Compartir PDF', 
        onPress: () => handleSharePdf(sheet) 
      },
      { 
        text: 'Descargar PDF', 
        onPress: () => handleDownloadPdf(sheet) 
      },
    ];

    if (sheet.status === 'ACTIVE') {
      options.push({
        text: 'Anular Hoja',
        style: 'destructive',
        onPress: () => handleAnnul(sheet),
      });
    }

    Alert.alert(
      `Hoja #${sheet.seq_number}/${sheet.year}`,
      sheet.status === 'ANNULLED' ? '(Anulada)' : '',
      options
    );
  };

  const renderSheet = ({ item }) => {
    const isLoadingThis = loadingSheetId === item.id;
    
    return (
      <TouchableOpacity 
        style={styles.sheetCard}
        onPress={() => showSheetOptions(item)}
        activeOpacity={0.7}
      >
        <View style={styles.sheetHeader}>
          <View>
            <Text style={styles.sheetNumber}>
              #{item.seq_number}/{item.year}
            </Text>
            <Text style={styles.sheetDate}>
              {format(new Date(item.created_at), "d MMM yyyy, HH:mm", { locale: es })}
            </Text>
          </View>
          <View style={styles.sheetHeaderRight}>
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
        </View>

        <View style={styles.sheetBody}>
          <View style={styles.sheetRow}>
            <Text style={styles.sheetLabel}>Origen</Text>
            <Text style={styles.sheetValue} numberOfLines={1}>
              {item.pickup_address}
            </Text>
          </View>
          
          <View style={styles.sheetRow}>
            <Text style={styles.sheetLabel}>Destino</Text>
            <Text style={styles.sheetValue} numberOfLines={1}>
              {item.destination}
            </Text>
          </View>

          {item.contractor_name && (
            <View style={styles.sheetRow}>
              <Text style={styles.sheetLabel}>Contratante</Text>
              <Text style={styles.sheetValue} numberOfLines={1}>
                {item.contractor_name}
              </Text>
            </View>
          )}
        </View>

        <View style={styles.sheetActions}>
          <TouchableOpacity
            style={[styles.actionButton, isLoadingThis && styles.actionButtonDisabled]}
            onPress={() => handleSharePdf(item)}
            disabled={pdfLoading}
          >
            {isLoadingThis ? (
              <ActivityIndicator size="small" color="#fff" />
            ) : (
              <Text style={styles.actionButtonText}>Compartir</Text>
            )}
          </TouchableOpacity>
          
          {item.status === 'ACTIVE' && (
            <TouchableOpacity
              style={[styles.actionButton, styles.actionButtonSecondary]}
              onPress={() => handleAnnul(item)}
              disabled={pdfLoading}
            >
              <Text style={[styles.actionButtonText, styles.actionButtonTextSecondary]}>
                Anular
              </Text>
            </TouchableOpacity>
          )}
        </View>
      </TouchableOpacity>
    );
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#7A1F1F" />
        <Text style={styles.loadingText}>Cargando hojas...</Text>
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.header}>
        <Text style={styles.title}>Histórico</Text>
        <Text style={styles.subtitle}>
          {sheets.length} {sheets.length === 1 ? 'hoja' : 'hojas'} de ruta
        </Text>
      </View>

      {/* Filters */}
      <View style={styles.filters}>
        {[
          { key: 'all', label: 'Todas' },
          { key: 'active', label: 'Activas' },
          { key: 'annulled', label: 'Anuladas' },
        ].map((f) => (
          <TouchableOpacity
            key={f.key}
            style={[styles.filterButton, filter === f.key && styles.filterButtonActive]}
            onPress={() => setFilter(f.key)}
          >
            <Text style={[
              styles.filterButtonText,
              filter === f.key && styles.filterButtonTextActive,
            ]}>
              {f.label}
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
          <RefreshControl 
            refreshing={refreshing} 
            onRefresh={onRefresh}
            colors={['#7A1F1F']}
            tintColor="#7A1F1F"
          />
        }
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Text style={styles.emptyIcon}>📋</Text>
            <Text style={styles.emptyText}>No hay hojas de ruta</Text>
            <Text style={styles.emptySubtext}>
              {filter !== 'all' 
                ? 'Prueba cambiando el filtro'
                : 'Crea tu primera hoja desde la pestaña "Nueva"'
              }
            </Text>
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
    backgroundColor: '#F5F5F4',
  },
  loadingText: {
    marginTop: 12,
    fontSize: 16,
    color: '#57534E',
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
    marginTop: 4,
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
    fontWeight: '500',
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
    elevation: 2,
  },
  sheetHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  sheetHeaderRight: {
    alignItems: 'flex-end',
  },
  sheetNumber: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#1C1917',
  },
  sheetDate: {
    fontSize: 13,
    color: '#57534E',
    marginTop: 2,
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
    gap: 8,
  },
  sheetRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  sheetLabel: {
    fontSize: 12,
    color: '#57534E',
    width: 80,
  },
  sheetValue: {
    flex: 1,
    fontSize: 14,
    color: '#1C1917',
  },
  sheetActions: {
    flexDirection: 'row',
    gap: 8,
    borderTopWidth: 1,
    borderTopColor: '#E7E5E4',
    paddingTop: 12,
  },
  actionButton: {
    flex: 1,
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 8,
    backgroundColor: '#7A1F1F',
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 40,
  },
  actionButtonSecondary: {
    backgroundColor: '#FEE2E2',
  },
  actionButtonDisabled: {
    opacity: 0.7,
  },
  actionButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#fff',
  },
  actionButtonTextSecondary: {
    color: '#991B1B',
  },
  emptyContainer: {
    padding: 60,
    alignItems: 'center',
  },
  emptyIcon: {
    fontSize: 48,
    marginBottom: 16,
  },
  emptyText: {
    fontSize: 18,
    fontWeight: '600',
    color: '#1C1917',
    marginBottom: 8,
  },
  emptySubtext: {
    fontSize: 14,
    color: '#57534E',
    textAlign: 'center',
  },
});
