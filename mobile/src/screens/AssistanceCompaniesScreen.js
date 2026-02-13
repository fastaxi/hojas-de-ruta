/**
 * RutasFast Mobile - Assistance Companies Screen
 * CRUD for managing assistance companies
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  ScrollView,
  ActivityIndicator,
  Alert,
  Modal,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import api from '../services/api';
import { ENDPOINTS } from '../services/config';

export default function AssistanceCompaniesScreen({ navigation }) {
  const [companies, setCompanies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingCompany, setEditingCompany] = useState(null);
  
  const [formData, setFormData] = useState({
    name: '',
    cif: '',
    contact_phone: '',
    contact_email: '',
  });

  useEffect(() => {
    loadCompanies();
  }, []);

  // Refresh when screen comes into focus
  useEffect(() => {
    const unsubscribe = navigation.addListener('focus', () => {
      loadCompanies();
    });
    return unsubscribe;
  }, [navigation]);

  const loadCompanies = async () => {
    try {
      setLoading(true);
      const response = await api.get(ENDPOINTS.ASSISTANCE_COMPANIES);
      setCompanies(response.data);
    } catch (err) {
      console.error('[AssistanceCompanies] Error loading:', err.message);
      Alert.alert('Error', 'No se pudieron cargar las empresas');
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      cif: '',
      contact_phone: '',
      contact_email: '',
    });
    setEditingCompany(null);
  };

  const openModal = (company = null) => {
    if (company) {
      setEditingCompany(company);
      setFormData({
        name: company.name || '',
        cif: company.cif || '',
        contact_phone: company.contact_phone || '',
        contact_email: company.contact_email || '',
      });
    } else {
      resetForm();
    }
    setModalVisible(true);
  };

  const closeModal = () => {
    setModalVisible(false);
    resetForm();
  };

  const validateForm = () => {
    if (!formData.name.trim()) {
      Alert.alert('Error', 'El nombre es obligatorio');
      return false;
    }
    if (!formData.cif.trim()) {
      Alert.alert('Error', 'El CIF es obligatorio');
      return false;
    }
    return true;
  };

  const handleSave = async () => {
    if (!validateForm()) return;

    setSaving(true);
    try {
      const payload = {
        name: formData.name.trim(),
        cif: formData.cif.trim().toUpperCase(),
        contact_phone: formData.contact_phone.trim() || null,
        contact_email: formData.contact_email.trim().toLowerCase() || null,
      };

      if (editingCompany) {
        await api.put(`${ENDPOINTS.ASSISTANCE_COMPANIES}/${editingCompany.id}`, payload);
        Alert.alert('Éxito', 'Empresa actualizada correctamente');
      } else {
        await api.post(ENDPOINTS.ASSISTANCE_COMPANIES, payload);
        Alert.alert('Éxito', 'Empresa añadida correctamente');
      }

      closeModal();
      loadCompanies();
    } catch (err) {
      console.error('[AssistanceCompanies] Save error:', err.response?.data || err.message);
      const message = err.response?.data?.detail || 'Error al guardar la empresa';
      Alert.alert('Error', message);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = (company) => {
    Alert.alert(
      'Eliminar Empresa',
      `¿Estás seguro de eliminar "${company.name}"?`,
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'Eliminar',
          style: 'destructive',
          onPress: async () => {
            try {
              await api.delete(`${ENDPOINTS.ASSISTANCE_COMPANIES}/${company.id}`);
              Alert.alert('Éxito', 'Empresa eliminada');
              loadCompanies();
            } catch (err) {
              const message = err.response?.data?.detail || 'Error al eliminar';
              Alert.alert('Error', message);
            }
          },
        },
      ]
    );
  };

  const updateField = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.container} edges={[]}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#7A1F1F" />
          <Text style={styles.loadingText}>Cargando empresas...</Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container} edges={[]}>
      <ScrollView style={styles.scroll} showsVerticalScrollIndicator={false}>
        <View style={styles.header}>
          <Text style={styles.description}>
            Gestiona las empresas de asistencia en carretera con las que trabajas.
          </Text>
        </View>

        {/* Company List */}
        {companies.length === 0 ? (
          <View style={styles.emptyState}>
            <Text style={styles.emptyIcon}>🏢</Text>
            <Text style={styles.emptyTitle}>Sin empresas</Text>
            <Text style={styles.emptyText}>
              Añade empresas de asistencia para poder crear hojas de ruta de asistencia en carretera.
            </Text>
          </View>
        ) : (
          <View style={styles.list}>
            {companies.map((company) => (
              <View key={company.id} style={styles.companyCard}>
                <View style={styles.companyHeader}>
                  <Text style={styles.companyName}>{company.name}</Text>
                  <Text style={styles.companyCif}>{company.cif}</Text>
                </View>
                
                {(company.contact_phone || company.contact_email) && (
                  <View style={styles.companyContact}>
                    {company.contact_phone && (
                      <Text style={styles.contactText}>📞 {company.contact_phone}</Text>
                    )}
                    {company.contact_email && (
                      <Text style={styles.contactText}>✉️ {company.contact_email}</Text>
                    )}
                  </View>
                )}
                
                <View style={styles.companyActions}>
                  <TouchableOpacity
                    style={styles.editButton}
                    onPress={() => openModal(company)}
                  >
                    <Text style={styles.editButtonText}>Editar</Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    style={styles.deleteButton}
                    onPress={() => handleDelete(company)}
                  >
                    <Text style={styles.deleteButtonText}>Eliminar</Text>
                  </TouchableOpacity>
                </View>
              </View>
            ))}
          </View>
        )}

        {/* Spacer for FAB */}
        <View style={{ height: 100 }} />
      </ScrollView>

      {/* Add Button (FAB) */}
      <TouchableOpacity style={styles.fab} onPress={() => openModal()}>
        <Text style={styles.fabText}>+</Text>
      </TouchableOpacity>

      {/* Add/Edit Modal */}
      <Modal
        visible={modalVisible}
        animationType="slide"
        transparent={true}
        onRequestClose={closeModal}
      >
        <KeyboardAvoidingView
          behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
          style={styles.modalOverlay}
        >
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>
                {editingCompany ? 'Editar Empresa' : 'Nueva Empresa'}
              </Text>
              <TouchableOpacity onPress={closeModal}>
                <Text style={styles.modalClose}>✕</Text>
              </TouchableOpacity>
            </View>

            <ScrollView style={styles.modalForm}>
              <Text style={styles.inputLabel}>Nombre *</Text>
              <TextInput
                style={styles.input}
                value={formData.name}
                onChangeText={(v) => updateField('name', v)}
                placeholder="Nombre de la empresa"
                placeholderTextColor="#999"
              />

              <Text style={styles.inputLabel}>CIF *</Text>
              <TextInput
                style={styles.input}
                value={formData.cif}
                onChangeText={(v) => updateField('cif', v.toUpperCase())}
                placeholder="CIF de la empresa"
                placeholderTextColor="#999"
                autoCapitalize="characters"
              />

              <Text style={styles.inputLabel}>Teléfono de contacto</Text>
              <TextInput
                style={styles.input}
                value={formData.contact_phone}
                onChangeText={(v) => updateField('contact_phone', v)}
                placeholder="Teléfono (opcional)"
                placeholderTextColor="#999"
                keyboardType="phone-pad"
              />

              <Text style={styles.inputLabel}>Email de contacto</Text>
              <TextInput
                style={styles.input}
                value={formData.contact_email}
                onChangeText={(v) => updateField('contact_email', v.toLowerCase())}
                placeholder="Email (opcional)"
                placeholderTextColor="#999"
                keyboardType="email-address"
                autoCapitalize="none"
              />
            </ScrollView>

            <View style={styles.modalFooter}>
              <TouchableOpacity
                style={styles.cancelButton}
                onPress={closeModal}
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
                  <Text style={styles.saveButtonText}>
                    {editingCompany ? 'Guardar' : 'Añadir'}
                  </Text>
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
  header: {
    padding: 16,
  },
  description: {
    fontSize: 14,
    color: '#57534E',
    lineHeight: 20,
  },
  emptyState: {
    alignItems: 'center',
    padding: 40,
    marginTop: 40,
  },
  emptyIcon: {
    fontSize: 48,
    marginBottom: 16,
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#1C1917',
    marginBottom: 8,
  },
  emptyText: {
    fontSize: 14,
    color: '#78716C',
    textAlign: 'center',
    lineHeight: 20,
  },
  list: {
    padding: 16,
    paddingTop: 0,
  },
  companyCard: {
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
  companyHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  companyName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1C1917',
    flex: 1,
  },
  companyCif: {
    fontSize: 14,
    color: '#7A1F1F',
    fontWeight: '500',
  },
  companyContact: {
    marginBottom: 12,
  },
  contactText: {
    fontSize: 14,
    color: '#57534E',
    marginTop: 4,
  },
  companyActions: {
    flexDirection: 'row',
    gap: 12,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#F5F5F4',
  },
  editButton: {
    flex: 1,
    backgroundColor: '#F5F5F4',
    paddingVertical: 10,
    borderRadius: 8,
    alignItems: 'center',
  },
  editButtonText: {
    color: '#7A1F1F',
    fontWeight: '600',
    fontSize: 14,
  },
  deleteButton: {
    flex: 1,
    backgroundColor: '#FEE2E2',
    paddingVertical: 10,
    borderRadius: 8,
    alignItems: 'center',
  },
  deleteButtonText: {
    color: '#DC2626',
    fontWeight: '600',
    fontSize: 14,
  },
  fab: {
    position: 'absolute',
    bottom: 24,
    right: 24,
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: '#7A1F1F',
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 6,
    elevation: 8,
  },
  fabText: {
    fontSize: 28,
    color: '#fff',
    fontWeight: '300',
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: '#fff',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    maxHeight: '80%',
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#E7E5E4',
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#1C1917',
  },
  modalClose: {
    fontSize: 24,
    color: '#78716C',
    padding: 4,
  },
  modalForm: {
    padding: 20,
  },
  inputLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#7A1F1F',
    marginBottom: 8,
    marginTop: 12,
  },
  input: {
    height: 50,
    backgroundColor: '#F5F5F4',
    borderRadius: 8,
    paddingHorizontal: 16,
    fontSize: 16,
    color: '#1C1917',
  },
  modalFooter: {
    flexDirection: 'row',
    gap: 12,
    padding: 20,
    borderTopWidth: 1,
    borderTopColor: '#E7E5E4',
  },
  cancelButton: {
    flex: 1,
    backgroundColor: '#F5F5F4',
    paddingVertical: 14,
    borderRadius: 24,
    alignItems: 'center',
  },
  cancelButtonText: {
    color: '#57534E',
    fontWeight: '600',
    fontSize: 16,
  },
  saveButton: {
    flex: 1,
    backgroundColor: '#7A1F1F',
    paddingVertical: 14,
    borderRadius: 24,
    alignItems: 'center',
  },
  saveButtonDisabled: {
    opacity: 0.7,
  },
  saveButtonText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 16,
  },
});
