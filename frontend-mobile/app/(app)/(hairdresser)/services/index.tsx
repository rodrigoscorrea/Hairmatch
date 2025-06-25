// app/(app)/(hairdresser)/services/index.tsx
import React from 'react';
import { View, Text, ScrollView, TouchableOpacity, ActivityIndicator } from 'react-native';
import { Accordion } from '@/components/Accordion';
import { Ionicons } from '@expo/vector-icons';
import { styles } from '@/styles/hairdresser/service/styles/HairdresserServiceManager'; // Adjust path
import ConfirmationModal from '@/components/modals/confirmationModal/ConfirmationModal';
import { useServiceManager } from '@/hooks/hairdresserHooks/useServiceManager';
import { serviceTimeFormater } from '@/utils/serviceTime-formater';
import { ErrorModal } from '@/components/modals/ErrorModal/ErrorModal';

export default function ServiceManagerScreen() {
  const {
    isLoading,
    services,
    modalVisible,
    setModalVisible,
    selectedServiceId,
    handleDelete,
    confirmDelete,
    goToCreate,
    goToEdit,
    errorModal,
    closeErrorModal
  } = useServiceManager();

  return (
    <View style={{ flex: 1 }}>
      <ScrollView style={styles.container}>
        <View>
          <Text style={styles.title}>Seus Serviços</Text>
        </View>
        
        
        {isLoading ? (
          <ActivityIndicator size="large" color="#000" />
        ) : services && services.length > 0 ? (
          services.map((service) => (
            <Accordion key={service.id} title={service.name}>
              <View style={styles.card}>
                <View style={styles.cardHeader}>
                  <Text style={styles.label}>Tempo: <Text style={styles.bold}>{serviceTimeFormater(service.duration)}</Text></Text>
                  <View style={styles.iconRow}>
                    <TouchableOpacity onPress={() => handleDelete(service.id)}>
                      <Ionicons name="trash-outline" size={18} color="#000" />
                    </TouchableOpacity>
                    <TouchableOpacity style={{ marginLeft: 10 }} onPress={() => goToEdit(service.id)}>
                      <Ionicons name="pencil-outline" size={18} color="#000" />
                    </TouchableOpacity>
                  </View>
                </View>
                <Text>Valor: <Text style={styles.bold}>R$ {service.price}</Text></Text>
                <Text style={styles.label}>Descrição: <Text style={styles.description}>{service.description}</Text></Text>
              </View>
            </Accordion>
          ))
        ) : (
          <View>
            <Text>Você ainda não cadastrou nenhum serviço.</Text>
          </View>
          
        )}
      </ScrollView>

      <TouchableOpacity style={styles.addButton} onPress={goToCreate}>
        <Ionicons name="add" size={28} color="#000" />
      </TouchableOpacity>

      <ConfirmationModal
        visible={modalVisible}
        title="Confirmar exclusão"
        description="Tem certeza de que deseja excluir este serviço?"
        confirmText="Sim, excluir"
        onConfirm={confirmDelete}
        onCancel={() => setModalVisible(false)}
      />

      <ErrorModal
        visible={errorModal.visible}
        message={errorModal.message}
        onClose={closeErrorModal}
      />
    </View>
  );
};