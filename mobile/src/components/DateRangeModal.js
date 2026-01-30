/**
 * RutasFast Mobile - Date Range Picker Modal
 * For selecting date range for PDF export
 */
import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Modal,
  TouchableOpacity,
  Platform,
  ActivityIndicator,
} from 'react-native';
import DateTimePicker from '@react-native-community/datetimepicker';
import { formatDateToISO, validateDateRange, MAX_RANGE_DAYS } from '../utils/filename';

export default function DateRangeModal({ 
  visible, 
  onClose, 
  onConfirm, 
  loading = false 
}) {
  // Default to last 7 days
  const [fromDate, setFromDate] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() - 7);
    return d;
  });
  const [toDate, setToDate] = useState(new Date());
  
  const [showFromPicker, setShowFromPicker] = useState(false);
  const [showToPicker, setShowToPicker] = useState(false);
  const [error, setError] = useState(null);

  // Validate on date change
  useEffect(() => {
    const validation = validateDateRange(
      formatDateToISO(fromDate),
      formatDateToISO(toDate)
    );
    setError(validation.valid ? null : validation.message);
  }, [fromDate, toDate]);

  const handleConfirm = () => {
    const from = formatDateToISO(fromDate);
    const to = formatDateToISO(toDate);
    
    const validation = validateDateRange(from, to);
    if (!validation.valid) {
      setError(validation.message);
      return;
    }

    onConfirm(from, to);
  };

  const handleFromChange = (event, selectedDate) => {
    setShowFromPicker(Platform.OS === 'ios');
    if (selectedDate) {
      setFromDate(selectedDate);
    }
  };

  const handleToChange = (event, selectedDate) => {
    setShowToPicker(Platform.OS === 'ios');
    if (selectedDate) {
      setToDate(selectedDate);
    }
  };

  const formatForDisplay = (date) => {
    return date.toLocaleDateString('es-ES', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    });
  };

  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      onRequestClose={onClose}
    >
      <TouchableOpacity 
        style={styles.overlay} 
        activeOpacity={1} 
        onPress={onClose}
      >
        <TouchableOpacity 
          style={styles.content} 
          activeOpacity={1}
          onPress={() => {}}
        >
          <Text style={styles.title}>Exportar PDF por Rango</Text>
          <Text style={styles.subtitle}>
            Máximo {MAX_RANGE_DAYS} días
          </Text>

          {/* From Date */}
          <Text style={styles.label}>Desde</Text>
          <TouchableOpacity
            style={styles.dateButton}
            onPress={() => setShowFromPicker(true)}
          >
            <Text style={styles.dateText}>{formatForDisplay(fromDate)}</Text>
          </TouchableOpacity>

          {showFromPicker && (
            <DateTimePicker
              value={fromDate}
              mode="date"
              display={Platform.OS === 'ios' ? 'spinner' : 'default'}
              onChange={handleFromChange}
              maximumDate={new Date()}
            />
          )}

          {/* To Date */}
          <Text style={styles.label}>Hasta</Text>
          <TouchableOpacity
            style={styles.dateButton}
            onPress={() => setShowToPicker(true)}
          >
            <Text style={styles.dateText}>{formatForDisplay(toDate)}</Text>
          </TouchableOpacity>

          {showToPicker && (
            <DateTimePicker
              value={toDate}
              mode="date"
              display={Platform.OS === 'ios' ? 'spinner' : 'default'}
              onChange={handleToChange}
              maximumDate={new Date()}
            />
          )}

          {/* Error Message */}
          {error && (
            <View style={styles.errorContainer}>
              <Text style={styles.errorText}>{error}</Text>
            </View>
          )}

          {/* Buttons */}
          <View style={styles.buttons}>
            <TouchableOpacity
              style={styles.cancelButton}
              onPress={onClose}
              disabled={loading}
            >
              <Text style={styles.cancelButtonText}>Cancelar</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={[
                styles.confirmButton,
                (loading || error) && styles.buttonDisabled,
              ]}
              onPress={handleConfirm}
              disabled={loading || !!error}
            >
              {loading ? (
                <ActivityIndicator color="#fff" size="small" />
              ) : (
                <Text style={styles.confirmButtonText}>Compartir PDF</Text>
              )}
            </TouchableOpacity>
          </View>
        </TouchableOpacity>
      </TouchableOpacity>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
  },
  content: {
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 24,
    width: '100%',
    maxWidth: 400,
  },
  title: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#1C1917',
    textAlign: 'center',
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 14,
    color: '#57534E',
    textAlign: 'center',
    marginBottom: 24,
  },
  label: {
    fontSize: 12,
    fontWeight: '600',
    color: '#57534E',
    marginBottom: 8,
    letterSpacing: 1,
  },
  dateButton: {
    height: 50,
    backgroundColor: '#F5F5F4',
    borderRadius: 8,
    justifyContent: 'center',
    paddingHorizontal: 16,
    marginBottom: 16,
  },
  dateText: {
    fontSize: 16,
    color: '#1C1917',
  },
  errorContainer: {
    backgroundColor: '#FEE2E2',
    padding: 12,
    borderRadius: 8,
    marginBottom: 16,
  },
  errorText: {
    fontSize: 14,
    color: '#991B1B',
    textAlign: 'center',
  },
  buttons: {
    flexDirection: 'row',
    gap: 12,
    marginTop: 8,
  },
  cancelButton: {
    flex: 1,
    height: 48,
    borderRadius: 24,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#E7E5E4',
  },
  cancelButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#57534E',
  },
  confirmButton: {
    flex: 2,
    height: 48,
    borderRadius: 24,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#7A1F1F',
  },
  confirmButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
  },
  buttonDisabled: {
    opacity: 0.5,
  },
});
