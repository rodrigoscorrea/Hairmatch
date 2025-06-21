import React, {useState} from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  SafeAreaView,
  ScrollView,
  Modal
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { styles } from './styles/ReserveDetailsStyle';
import { ServiceInfo } from '@/app/models/Service.types';

import { RootStackParamList } from '@/app/models/RootStackParams.types';
import { StackNavigationProp } from '@react-navigation/stack';
import { useNavigation, RouteProp, useRoute } from '@react-navigation/native';
import BottomTabBar from '../../components/BottomBar';
import { set } from 'date-fns';


type ServiceInfoRouteProp = RouteProp<RootStackParamList, 'ServiceInfo'>;

export default function InfoScreen() {
  const route = useRoute<ServiceInfoRouteProp>();
  const navigation = useNavigation<any>();
  const serviceData = route.params?.serviceData;
  const [modalVisible, setModalVisible] = useState<boolean>(false);

  const isEvaluationEnabled = () => {
    if (!serviceData || !serviceData.date || !serviceData.time) {
      return false;
    }

    const [day, month, year] = serviceData.date.split('/').map(Number);
    const [hours, minutes] = serviceData.time.split(':').map(Number);
    const serviceDateTime = new Date(year, month - 1, day, hours, minutes);
    const now = new Date();
    return now > serviceDateTime;
  };

  const evaluationEnabled = isEvaluationEnabled();

  console.log('Avaliação habilitada:', evaluationEnabled);
  
  const handleCancel = () => {
    setModalVisible(true);
    console.log('Cancelar pressed');
  };

  const handleEvaluate = () => {
    console.log('Fazer Avaliação pressed');
    if (!evaluationEnabled) {
      console.log('Avaliação ainda não disponível.');
      return;
    };
  }

  const handleBack = () => {
    console.log('Back pressed');
    navigation.goBack();
  };

  const closeModal = () => {
    setModalVisible(false);
  };

  const handleCancelEvent = () => {
    console.log(`Cancelamento front-end para o serviço de: ${serviceData.name}`);
    closeModal(); // Fecha o pop-up de confirmação
    navigation.goBack(); // Volta para a tela anterior (a lista de agendamentos)
  };


  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity style={styles.backButton} onPress={handleBack}>
          <Ionicons name="chevron-back" size={24} color="#333" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}> Meus Agendamentos</Text>
      </View>

      <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
        {/* Profile Card */}
        <View style={styles.profileCard}>
          <View style={styles.profileHeader}>
            <View style={styles.avatar} />
            <View style={styles.profileInfo}>
              <View style={styles.nameContainer}>
                <Text style={styles.name}>{serviceData.name}</Text>
                <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                    <Ionicons name="star" size={16} color="#FF9F66" />
                  <Text style={styles.rating}>{serviceData.rating}</Text>
                </View>
              </View>
              <View style={styles.detailRow}>
                <Text style={styles.detailLabel}>Dia:</Text>
                <Text style={styles.detailValue}>{serviceData.date}</Text>
              </View>
              <View style={styles.detailRow}>
                <Text style={styles.detailLabel}>Hora:</Text>
                <Text style={styles.detailValue}>{serviceData.time}</Text>
              </View>
              <View style={styles.detailRow}>
                <Text style={styles.detailLabel}>Serviço:</Text>
                <Text style={styles.detailValue}>{serviceData.service}</Text>
              </View>
            </View>
          </View>
        </View>

        {/* Address Card */}
        <View style={styles.infoCard}>
          <Text style={styles.infoLabel}>Endereço:</Text>
          <Text style={styles.infoValue}>{serviceData.address}</Text>
        </View>

        {/* Phone Card */}
        <View style={styles.infoCard}>
          <Text style={styles.infoLabel}>Telefone:</Text>
          <Text style={styles.infoValue}>{serviceData.phone}</Text>
        </View>
      
      </ScrollView>
      {/* Action Buttons */}
      <View style={styles.buttonContainer}>
        <TouchableOpacity 
          style={[styles.button, styles.cancelButton]} 
          onPress={handleCancel}
        >
          <Text style={styles.cancelButtonText}>Cancelar</Text>
        </TouchableOpacity>
        
        <TouchableOpacity 
          style={[
            styles.button, 
            styles.evaluateButton,
            // Aplica um estilo de "desabilitado" se a avaliação não estiver liberada
            !evaluationEnabled && styles.disabledButton 
          ]} 
          onPress={handleEvaluate}
          // Desabilita o botão (impede o onPress e muda a opacidade)
          disabled={!evaluationEnabled}
        >
          <Text style={[
            styles.evaluateButtonText,
            !evaluationEnabled && styles.disabledButtonText
          ]}>
            Fazer Avaliação
          </Text>
        </TouchableOpacity>
      </View>
      <Modal
        visible={modalVisible}
        transparent={true}
        animationType="slide"
        onRequestClose={closeModal}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContainer}>
          <Text style={styles.modalTitle}>Cancelar Agendamento</Text>
            <Text style={styles.modalText}>
              Tem certeza de que deseja cancelar este agendamento? 
              Essa ação não poderá ser desfeita e o horário será liberado para outros clientes.
            </Text>
            <View style={styles.modalButtonGroup}>
                <TouchableOpacity
                style={styles.modalBackButton}
                onPress={closeModal}
                >
                <Text style={styles.modalBackButtonText}>Voltar</Text>
                </TouchableOpacity>
                <TouchableOpacity
                style={styles.modalAcceptButton}
                onPress={handleCancelEvent}
                >
                <Text style={styles.modalAcceptButtonText}>Cancelar</Text>
                </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
      <BottomTabBar />
    </SafeAreaView>
  );
};

