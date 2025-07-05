// app/(app)/(customer)/reserves/[id].tsx
import React from 'react';
import { View, Text, TouchableOpacity, SafeAreaView, ScrollView, Modal, ActivityIndicator } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { styles } from '@/styles/customer/reservation/styles/ReservationDetailsStyles';
import { useReserveDetails } from '@/hooks/customerHooks/useReserveDetails';
import { formatDate} from '@/utils/date-formater';
import { formatTime } from '@/utils/time-formater';

export default function ReserveInfoScreen() {
  const {
    loading,
    reserve,
    modalVisible,
    setModalVisible,
    evaluationEnabled,
    handleBack,
    confirmCancel,
    handleReviewScreen
  } = useReserveDetails();

  if (loading) {
    return <ActivityIndicator size="large" style={{ flex: 1 }} />;
  }

  if (!reserve) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.header}>
            <TouchableOpacity style={styles.backButton} onPress={handleBack}>
                <Ionicons name="chevron-back" size={24} color="#333" />
            </TouchableOpacity>
            <Text style={styles.headerTitle}>Agendamento não encontrado</Text>
        </View>
      </SafeAreaView>
    );
  }


  const { service, start_time } = reserve;
  const { hairdresser } = service;

  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity style={styles.backButton} onPress={handleBack}>
          <Ionicons name="chevron-back" size={24} color="#333" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Detalhes do Agendamento</Text>
      </View>

      <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
        {/* Profile Card */}
        <View style={styles.profileCard}>
            <View style={styles.profileHeader}>
                <View style={styles.avatar} />
                <View style={styles.profileInfo}>
                    <View style={styles.nameContainer}>
                        <Text style={styles.name}>{`${hairdresser.user.first_name} ${hairdresser.user.last_name}`}</Text>
                        <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                            <Ionicons name="star" size={16} color="#FF9F66" />
                            <Text style={styles.rating}>{hairdresser.user.rating}</Text>
                        </View>
                    </View>
                    <View style={styles.detailRow}>
                        <Text style={styles.detailLabel}>Dia:</Text>
                        <Text style={styles.detailValue}>{formatDate(start_time)}</Text>
                    </View>
                    <View style={styles.detailRow}>
                        <Text style={styles.detailLabel}>Hora:</Text>
                        <Text style={styles.detailValue}>{formatTime(start_time)}</Text>
                    </View>
                    <View style={styles.detailRow}>
                        <Text style={styles.detailLabel}>Serviço:</Text>
                        <Text style={styles.detailValue}>{service.name}</Text>
                    </View>
                </View>
            </View>
        </View>

        {/* Address & Phone Cards */}
        <View style={styles.infoCard}>
            <Text style={styles.infoLabel}>Endereço:</Text>
            <Text style={styles.infoValue}>{`${hairdresser.user.address}, ${hairdresser.user.number}`}</Text>
        </View>
        <View style={styles.infoCard}>
            <Text style={styles.infoLabel}>Telefone:</Text>
            <Text style={styles.infoValue}>{hairdresser.user.phone}</Text>
        </View>
      </ScrollView>
      
      {/* Action Buttons */}
      <View style={styles.buttonContainer}>
        <TouchableOpacity 
          style={[styles.button, styles.cancelButton, evaluationEnabled && styles.disabledCancelButton]} 
          onPress={() => setModalVisible(true)}
          disabled={evaluationEnabled}
        >
          <Text style={styles.cancelButtonText}>Cancelar Agendamento</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.button, styles.evaluateButton, !evaluationEnabled && styles.disabledButton]}
          onPress={() => handleReviewScreen(reserve.id)}
          disabled={!evaluationEnabled}
        >
          <Text style={[styles.evaluateButtonText, !evaluationEnabled && styles.disabledButtonText]}>
            Fazer Avaliação
          </Text>
        </TouchableOpacity>
      </View>
      
      {/* Cancellation Modal */}
      <Modal visible={modalVisible} transparent={true} animationType="slide">
        <View style={styles.modalOverlay}>
            <View style={styles.modalContainer}>
                <Text style={styles.modalTitle}>Cancelar Agendamento</Text>
                <Text style={styles.modalText}>Tem certeza de que deseja cancelar este agendamento?</Text>
                <View style={styles.modalButtonGroup}>
                    <TouchableOpacity style={styles.modalBackButton} onPress={() => setModalVisible(false)}>
                        <Text style={styles.modalBackButtonText}>Voltar</Text>
                    </TouchableOpacity>
                    <TouchableOpacity style={styles.modalAcceptButton} onPress={confirmCancel}>
                        <Text style={styles.modalAcceptButtonText}>Cancelar</Text>
                    </TouchableOpacity>
                </View>
            </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
};