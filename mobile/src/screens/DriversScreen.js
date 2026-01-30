/**
 * RutasFast Mobile - Drivers Screen
 * CRUD for additional drivers
 */
import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  Modal,
  TextInput,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useDrivers } from '../contexts/DriversContext';
import { validateDriver, normalizeTrim, normalizeUpper } from '../utils/validators';

export default function DriversScreen() {
  const { drivers, loading, refreshDrivers, addDriver, editDriver, removeDriver } = useDrivers();
  
  const [showModal, setShowModal] = useState(false);
  const [editingDriver, setEditingDriver] = useState(null);
  const [saving, setSaving] = useState(false);
  
  // Form state
  const [fullName, setFullName] = useState('');
  const [dni, setDni] = useState('');

  // Refresh on mount
  useEffect(() => {
    refreshDrivers().catch(() => {});
  }, []);

  /**
   * Open modal for adding new driver
   */
  const handleAdd = () => {
    setEditingDriver(null);
    setFullName('');
    setDni('');
    setShowModal(true);
  };

  /**
   * Open modal for editing existing driver
   */
  const handleEdit = (driver) => {
    setEditingDriver(driver);
    setFullName(driver.full_name || '');
    setDni(driver.dni || '');
    setShowModal(true);
  };

  /**
   * Confirm and delete driver
   */
  const handleDelete = (driver) => {
    Alert.alert(
      'Eliminar Conductor',
      `¿Estás seguro de eliminar a ${driver.full_name}?\n\nEsta acción no se puede deshacer.`,
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'Eliminar',
          style: 'destructive',
          onPress: async () => {
            try {
              await removeDriver(driver.id);
              Alert.alert('Éxito', 'Conductor eliminado');
            } catch (error) {
              const message = error.response?.data?.detail || 'Error al eliminar';
              Alert.alert('Error', message);
            }
          },
        },
      ]
    );
  };

  /**
   * Save driver (create or update)
   */
  const handleSave = async () => {
    const payload = {
      full_name: normalizeTrim(fullName),
      dni: normalizeUpper(dni),
    };

    // Validate
    const validation = validateDriver(payload);
    if (!validation.ok) {
      Alert.alert('Error', validation.msg);
      return;
    }

    setSaving(true);
    try {
      if (editingDriver) {
        await editDriver(editingDriver.id, payload);
        Alert.alert('Éxito', 'Conductor actualizado');
      } else {
        await addDriver(payload);
        Alert.alert('Éxito', 'Conductor añadido');
      }
      setShowModal(false);
    } catch (error) {
      const message = error.response?.data?.detail || 'Error al guardar';
      Alert.alert('Error', message);
    } finally {
      setSaving(false);
    }
  };

  /**
   * Render single driver item
   */
  const renderDriver = ({ item }) => (
    <View style={styles.driverCard}>
      <View style={styles.driverInfo}>
        <Text style={styles.driverName}>{item.full_name}</Text>
        <Text style={styles.driverDni}>DNI: {item.dni}</Text>
      </View>
      <View style={styles.driverActions}>
        <TouchableOpacity
          style={styles.editButton}
          onPress={() => handleEdit(item)}
        >
          <Text style={styles.editButtonText}>Editar</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={styles.deleteButton}
          onPress={() => handleDelete(item)}
        >
          <Text style={styles.deleteButtonText}>Eliminar</Text>
        </TouchableOpacity>
      </View>
    </View>
  );

  // Loading state
  if (loading && drivers.length === 0) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#7A1F1F" />
        <Text style={styles.loadingText}>Cargando conductores...</Text>
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.container} edges={['bottom']}>
      {/* Header with Add Button */}
      <View style={styles.header}>
        <Text style={styles.title}>Conductores Adicionales</Text>
        <Text style={styles.subtitle}>
          {drivers.length} {drivers.length === 1 ? 'conductor' : 'conductores'}
        </Text>
      </View>

      {/* Drivers List */}
      <FlatList
        data={drivers}
        renderItem={renderDriver}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.list}
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Text style={styles.emptyIcon}>👤</Text>
            <Text style={styles.emptyText}>No hay conductores</Text>
            <Text style={styles.emptySubtext}>
              Añade conductores adicionales que puedan usar tu vehículo
            </Text>
          </View>
        }
      />

      {/* Add Button */}
      <View style={styles.footer}>
        <TouchableOpacity style={styles.addButton} onPress={handleAdd}>
          <Text style={styles.addButtonText}>+ Añadir Conductor</Text>
        </TouchableOpacity>
      </View>

      {/* Add/Edit Modal */}
      <Modal
        visible={showModal}
        transparent
        animationType="fade"
        onRequestClose={() => setShowModal(false)}
      >
        <KeyboardAvoidingView
          behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
          style={styles.modalOverlay}
        >
          <TouchableOpacity
            style={styles.modalBackdrop}
            activeOpacity={1}
            onPress={() => setShowModal(false)}
          />
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>
              {editingDriver ? 'Editar Conductor' : 'Nuevo Conductor'}
            </Text>

            <Text style={styles.label}>NOMBRE COMPLETO *</Text>
            <TextInput
              style={styles.input}
              value={fullName}
              onChangeText={setFullName}
              placeholder="Nombre del conductor"
              placeholderTextColor="#999"
              autoCapitalize="words"
            />

            <Text style={styles.label}>DNI *</Text>
            <TextInput
              style={styles.input}
              value={dni}
              onChangeText={setDni}
              placeholder="12345678A"
              placeholderTextColor="#999"
              autoCapitalize="characters"
            />
            <Text style={styles.hint}>Se guardará en mayúsculas</Text>

            <View style={styles.modalButtons}>
              <TouchableOpacity
                style={styles.cancelButton}
                onPress={() => setShowModal(false)}
                disabled={saving}
              >
                <Text style={styles.cancelButtonText}>Cancelar</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[styles.saveButton, saving && styles.saveButtonDisabled]}
                onPress={handleSave}
                disabled={saving}
              >
                {saving ? (
                  <ActivityIndicator color="#fff" size="small" />
                ) : (
                  <Text style={styles.saveButtonText}>Guardar</Text>
                )}
              </TouchableOpacity>
            </View>
          </View>
        </KeyboardAvoidingView>
      </Modal>
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
    padding: 20,
    paddingBottom: 16,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#1C1917',
  },
  subtitle: {
    fontSize: 14,
    color: '#57534E',
    marginTop: 4,
  },
  list: {
    padding: 16,
    paddingTop: 0,
  },
  driverCard: {
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
  driverInfo: {
    marginBottom: 12,
  },
  driverName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1C1917',
  },
  driverDni: {
    fontSize: 14,
    color: '#57534E',
    marginTop: 4,
  },
  driverActions: {
    flexDirection: 'row',
    gap: 8,
    borderTopWidth: 1,
    borderTopColor: '#E7E5E4',
    paddingTop: 12,
  },
  editButton: {
    flex: 1,
    paddingVertical: 8,
    borderRadius: 6,
    backgroundColor: '#EFF6FF',
    alignItems: 'center',
  },
  editButtonText: {
    fontSize: 14,
    fontWeight: '500',
    color: '#1E40AF',
  },
  deleteButton: {
    flex: 1,
    paddingVertical: 8,
    borderRadius: 6,
    backgroundColor: '#FEE2E2',
    alignItems: 'center',
  },
  deleteButtonText: {
    fontSize: 14,
    fontWeight: '500',
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
  footer: {
    padding: 20,
    borderTopWidth: 1,
    borderTopColor: '#E7E5E4',
    backgroundColor: '#fff',
  },
  addButton: {
    height: 50,
    backgroundColor: '#7A1F1F',
    borderRadius: 25,
    justifyContent: 'center',
    alignItems: 'center',
  },
  addButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  // Modal styles
  modalOverlay: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  modalBackdrop: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
  },
  modalContent: {
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 24,
    width: '90%',
    maxWidth: 400,
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#1C1917',
    marginBottom: 20,
    textAlign: 'center',
  },
  label: {
    fontSize: 12,
    fontWeight: '600',
    color: '#57534E',
    marginBottom: 8,
    marginTop: 12,
    letterSpacing: 1,
  },
  input: {
    height: 50,
    backgroundColor: '#F5F5F4',
    borderRadius: 8,
    paddingHorizontal: 16,
    fontSize: 16,
    color: '#1C1917',
  },
  hint: {
    fontSize: 12,
    color: '#A8A29E',
    marginTop: 4,
  },
  modalButtons: {
    flexDirection: 'row',
    gap: 12,
    marginTop: 24,
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
  saveButton: {
    flex: 2,
    height: 48,
    borderRadius: 24,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#7A1F1F',
  },
  saveButtonDisabled: {
    opacity: 0.7,
  },
  saveButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
  },
});
