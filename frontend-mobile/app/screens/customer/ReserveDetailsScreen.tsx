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
  const navigation = useNavigation<any>();
  const serviceData = route.params?.serviceData;

  const handleCancel = () => {
    console.log('Cancelar pressed');
  };

  const handleEvaluate = () => {
    console.log('Fazer Avaliação pressed');
  };

  const handleBack = () => {
    console.log('Back pressed');
    navigation.goBack();
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
          style={[styles.button, styles.evaluateButton]} 
          onPress={handleEvaluate}
        >
          <Text style={styles.evaluateButtonText}>Fazer Avaliação</Text>
        </TouchableOpacity>
      </View>
      <BottomTabBar />
    </SafeAreaView>
  );
};

