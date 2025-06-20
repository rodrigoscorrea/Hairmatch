import React from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  SafeAreaView,
  ScrollView,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { styles } from './styles/ReserveDetailsStyle';
import { ServiceInfo } from '@/app/models/Service.types';

import { RootStackParamList } from '@/app/models/RootStackParams.types';
import { StackNavigationProp } from '@react-navigation/stack';
import { useNavigation, RouteProp, useRoute } from '@react-navigation/native';
import BottomTabBar from '../../components/BottomBar';


type ServiceInfoRouteProp = RouteProp<RootStackParamList, 'ServiceInfo'>;

export default function InfoScreen() {
    const route = useRoute<ServiceInfoRouteProp>();
  // Dados estáticos baseados na imagem
  const serviceData: ServiceInfo = {
    name: 'Camilly Borgaço',
    rating: 5.0,
    date: '20/04/2025',
    time: '15h',
    service: 'SOS Cachos',
    location: 'CBCachos',
    address: 'Rua Mayoruna, 42 Alvorada 1, Manaus - AM, 69043-110',
    phone: '(92) 9 8431-7533',
    status: 'Aguardando Confirmação',
  };

  const handleCancel = () => {
    console.log('Cancelar pressed');
  };

  const handleEvaluate = () => {
    console.log('Fazer Avaliação pressed');
  };

  const handleBack = () => {
    console.log('Back pressed');
  };

  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity style={styles.backButton} onPress={handleBack}>
          <Ionicons name="chevron-back" size={24} color="#333" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Agendamentos</Text>
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

        {/* Location Card */}
        <View style={styles.infoCard}>
          <Text style={styles.infoLabel}>Local:</Text>
          <Text style={styles.infoValue}>{serviceData.location}</Text>
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

        {/* Status Card */}
        <View style={styles.infoCard}>
          <Text style={styles.infoLabel}>Status:</Text>
          <Text style={styles.infoValue}>{serviceData.status}</Text>
        </View>
        
        {/* Action Buttons */}
        <View style={styles.buttonContainer}>
        <TouchableOpacity 
          style={[styles.button, styles.cancelButton]} 
          onPress={handleCancel}
        >
          <Text style={styles.cancelButtonText}>Cancelar</Text>
        </TouchableOpacity>
        
        <TouchableOpacity 
          style={[styles.button, styles.evaluateButton]} 
          onPress={handleEvaluate}
        >
          <Text style={styles.evaluateButtonText}>Fazer Avaliação</Text>
        </TouchableOpacity>
      </View>
      </ScrollView>
      <BottomTabBar />
    </SafeAreaView>
  );
};

