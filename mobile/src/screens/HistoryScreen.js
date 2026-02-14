/**
 * RutasFast Mobile - History Screen
 * Route sheets list with PDF download and sharing
 * 
 * Features:
 * - Filter by status (all/active/annulled)
 * - View sheet details
 * - View/Share individual PDF
 * - Share PDF by date range
 * - Double-click prevention
 * - Comprehensive error handling
 * - Cursor-based pagination (infinite scroll)
 */
import React, { useState, useEffect, useCallback, useRef } from 'react';
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
import api from '../services/api';
import { ENDPOINTS } from '../services/config';
import { usePdfShare } from '../hooks/usePdfShare';
import { usePdfView } from '../hooks/usePdfView';
import DateRangeModal from '../components/DateRangeModal';

export default function HistoryScreen({ navigation, route }) {
  const [sheets, setSheets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [filter, setFilter] = useState('all'); // all, active, annulled
  const [showRangeModal, setShowRangeModal] = useState(false);
  
  // Use ref for cursor to avoid re-render loops
  const cursorRef = useRef(null);
  const hasMoreRef = useRef(true);

  const { 
    preparingPdfId,
    preparingRange,
    isPreparingSheet,
    shareSheetPdf,
    shareRangePdf,
  } = usePdfShare();

  const { viewPdf, isViewingPdf } = usePdfView();

  const loadSheets = useCallback(async (reset = false) => {
    // Avoid loading more if already loading or no more data
    if (!reset && (loadingMore || !hasMoreRef.current)) return;
    
    try {
      if (reset) {
        setLoading(true);
        cursorRef.current = null;
        hasMoreRef.current = true;
      } else {
        setLoadingMore(true);
      }
      
      const params = { limit: 50 };
      
      // Backend uses include_annulled, not status
      if (filter === 'active') {
        params.include_annulled = false;
      } else {
        // For 'all' and 'annulled', we need to include annulled sheets
        params.include_annulled = true;
      }
      
      // Add cursor for pagination (only when not resetting)
      if (!reset && cursorRef.current) {
        params.cursor = cursorRef.current;
      }
      
      const response = await api.get(ENDPOINTS.ROUTE_SHEETS, { params });
      
      // Handle paginated response {sheets, next_cursor}
      const data = response.data;
      let list = data.sheets || [];
      const nextCursor = data.next_cursor;
      
      // For 'annulled' filter, filter client-side
      if (filter === 'annulled') {
        list = list.filter(s => s.status === 'ANNULLED');
      }
      
      // Update cursor and hasMore
      cursorRef.current = nextCursor;
      hasMoreRef.current = !!nextCursor;
      
      // Append or replace sheets
      if (reset) {
        setSheets(list);
      } else {
        setSheets(prev => [...prev, ...list]);
      }
    } catch (error) {
      // 401 handled by interceptor, only show other errors
      if (error.response?.status !== 401) {
        console.log('[History] Load error:', error.message);
        Alert.alert('Error', 'No se pudieron cargar las hojas de ruta');
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
      setLoadingMore(false);
    }
  }, [filter]);

  // Load on mount and when filter changes (reset list)
  useEffect(() => {
    loadSheets(true);
  }, [filter]);

  // Reload when screen comes into focus (e.g., after creating a new sheet)
  useEffect(() => {
    const unsubscribe = navigation.addListener('focus', () => {
      loadSheets(true);
    });
    return unsubscribe;
  }, [navigation, loadSheets]);

  const onRefresh = () => {
    setRefreshing(true);
    loadSheets(true);
  };
  
  const onEndReached = () => {
    if (!loading && !loadingMore && hasMoreRef.current) {
      loadSheets(false);
    }
  };

  /**
   * Handle share PDF for a single sheet
   * Prevents double-click and shows loading state
   */
  const handleSharePdf = async (sheet) => {
    // Prevent if already preparing this sheet
    if (isPreparingSheet(sheet.id)) return;
    await shareSheetPdf(sheet);
  };

  /**
   * Handle share PDF by date range
   */
  const handleShareRange = async (fromDate, toDate) => {
    const result = await shareRangePdf(fromDate, toDate);
    if (result.success) {
      setShowRangeModal(false);
    }
  };

  /**
   * Handle annul sheet
   */
  const handleAnnul = async (sheet) => {
    const sheetNum = sheet.sheet_number || `${String(sheet.seq_number).padStart(3,'0')}/${sheet.year}`;
    Alert.alert(
      'Anular Hoja',
      `¿Estás seguro de anular la hoja #${sheetNum}?\n\nEsta acción no se puede deshacer.`,
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

  /**
   * Show options menu for a sheet
   */
  const showSheetOptions = (sheet) => {
    const isPreparing = isPreparingSheet(sheet.id);
    const isViewing = isViewingPdf(sheet.id);
    const sheetNum = sheet.sheet_number || `${String(sheet.seq_number).padStart(3,'0')}/${sheet.year}`;
    
    const options = [
      { text: 'Cancelar', style: 'cancel' },
      { 
        text: 'Ver hoja', 
        onPress: () => navigation.navigate('RouteSheetDetail', { sheetId: sheet.id }),
      },
      { 
        text: isViewing ? 'Abriendo...' : 'Ver PDF', 
        onPress: isViewing ? undefined : () => viewPdf(sheet.id, sheetNum),
      },
      { 
        text: isPreparing ? 'Preparando...' : 'Compartir PDF', 
        onPress: isPreparing ? undefined : () => handleSharePdf(sheet),
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
      `Hoja #${sheetNum}`,
      sheet.status === 'ANNULLED' ? '(Anulada)' : '',
      options
    );
  };

  /**
   * Handle view sheet detail
   */
  const handleViewSheet = (sheet) => {
    navigation.navigate('RouteSheetDetail', { sheetId: sheet.id });
  };

  /**
   * Handle view PDF
   */
  const handleViewPdf = (sheet) => {
    const sheetNum = sheet.sheet_number || `${String(sheet.seq_number).padStart(3,'0')}/${sheet.year}`;
    viewPdf(sheet.id, sheetNum);
  };

  /**
   * Render individual sheet card
   */
  const renderSheet = ({ item }) => {
    const isPreparing = isPreparingSheet(item.id);
    const isViewing = isViewingPdf(item.id);
    const sheetNum = item.sheet_number || `${String(item.seq_number).padStart(3,'0')}/${item.year}`;
    
    return (
      <TouchableOpacity 
        style={styles.sheetCard}
        onPress={() => handleViewSheet(item)}
        activeOpacity={0.7}
      >
        <View style={styles.sheetHeader}>
          <View>
            <Text style={styles.sheetNumber}>
              #{sheetNum}
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
          {/* Ver PDF button */}
          <TouchableOpacity
            style={[
              styles.actionButton,
              styles.actionButtonOutline,
              isViewing && styles.actionButtonDisabled,
            ]}
            onPress={() => handleViewPdf(item)}
            disabled={isViewing}
          >
            {isViewing ? (
              <ActivityIndicator size="small" color="#7A1F1F" />
            ) : (
              <Text style={[styles.actionButtonText, styles.actionButtonTextOutline]}>Ver PDF</Text>
            )}
          </TouchableOpacity>

          {/* Compartir PDF button */}
          <TouchableOpacity
            style={[
              styles.actionButton,
              isPreparing && styles.actionButtonDisabled,
            ]}
            onPress={() => handleSharePdf(item)}
            disabled={isPreparing}
          >
            {isPreparing ? (
              <View style={styles.buttonContent}>
                <ActivityIndicator size="small" color="#fff" />
                <Text style={[styles.actionButtonText, styles.buttonTextWithIcon]}>
                  Preparando...
                </Text>
              </View>
            ) : (
              <Text style={styles.actionButtonText}>Compartir</Text>
            )}
          </TouchableOpacity>
          
          {item.status === 'ACTIVE' && (
            <TouchableOpacity
              style={[styles.actionButton, styles.actionButtonSecondary]}
              onPress={() => handleAnnul(item)}
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

  // Loading state
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
        <View style={styles.headerTop}>
          <View>
            <Text style={styles.title}>Histórico</Text>
            <Text style={styles.subtitle}>
              {sheets.length} {sheets.length === 1 ? 'hoja' : 'hojas'} de ruta
            </Text>
          </View>
          
          {/* Export Range Button */}
          <TouchableOpacity
            style={[
              styles.exportButton,
              preparingRange && styles.exportButtonDisabled,
            ]}
            onPress={() => setShowRangeModal(true)}
            disabled={preparingRange}
          >
            {preparingRange ? (
              <ActivityIndicator size="small" color="#7A1F1F" />
            ) : (
              <Text style={styles.exportButtonText}>Exportar</Text>
            )}
          </TouchableOpacity>
        </View>
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

      {/* Date Range Modal */}
      <DateRangeModal
        visible={showRangeModal}
        onClose={() => setShowRangeModal(false)}
        onConfirm={handleShareRange}
        loading={preparingRange}
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
  headerTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
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
  exportButton: {
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 8,
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#7A1F1F',
    minWidth: 80,
    alignItems: 'center',
  },
  exportButtonDisabled: {
    opacity: 0.7,
  },
  exportButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#7A1F1F',
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
    paddingHorizontal: 12,
    borderRadius: 8,
    backgroundColor: '#7A1F1F',
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 40,
  },
  actionButtonOutline: {
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#7A1F1F',
  },
  actionButtonSecondary: {
    backgroundColor: '#FEE2E2',
  },
  actionButtonDisabled: {
    opacity: 0.8,
  },
  actionButtonText: {
    fontSize: 13,
    fontWeight: '600',
    color: '#fff',
  },
  actionButtonTextOutline: {
    color: '#7A1F1F',
  },
  actionButtonTextSecondary: {
    color: '#991B1B',
  },
  buttonContent: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  buttonTextWithIcon: {
    marginLeft: 8,
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
