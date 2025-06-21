import { ActivityIndicator, Alert, Text, View, SafeAreaView, TouchableOpacity, ScrollView } from 'react-native'
import { styles } from './styles/ReserveStyle';
import React, { useEffect, useState } from 'react'
import { getCustomerReserves } from '@/app/services/reserve.service';
import { useBottomTab } from '../../contexts/BottomTabContext';
import BottomTabBar from '../../components/BottomBar';
import { format } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import { ReserveWithService } from '@/app/models/Reserve.types';
import { formatDate } from '@/app/utils/date-formater';
import { formatTime } from '@/app/utils/time-formater';
import { useNavigation } from '@react-navigation/native';
import { StackNavigationProp } from '@react-navigation/stack';
import { RootStackParamList } from '@/app/models/RootStackParams.types';
import {ServiceInfo} from '@/app/models/Service.types';
import 'dayjs/locale/pt-br';
import dayjs from 'dayjs';

type NavigationProp = StackNavigationProp<RootStackParamList>;

export default function ReservesScreen() {
  const navigation = useNavigation<NavigationProp>();
  const [isFetchingReserves, setFetchingReserves] = useState(true);
  const [reserves, setReserves] = useState<ServiceInfo[]>([]);
  const { customer, setActiveTab } = useBottomTab();
  
  const handleMoreInfo = (serviceData:ServiceInfo) => {
    navigation.navigate('ServiceInfo', { serviceData });
  };

  useEffect(() => {
    setActiveTab('Reserves');
    
    const fetchReserves = async () => {
      if (!customer) {
        console.error('Customer data is missing or incomplete');
        Alert.alert('Erro', 'Dados do cliente não disponíveis');
        setFetchingReserves(false);
        return;
      }
      
      try {
        setFetchingReserves(true);
        const reserveResponse = await getCustomerReserves(customer.id);
        const converted:ServiceInfo[] =reserveResponse.data.map((ev:any) => ({
          id: ev.id,
          name: `${ev.service.hairdresser.user.first_name} ${ev.service.hairdresser.user.last_name}`,
          rating: ev.service.hairdresser.user.rating,
          date: formatDate(ev.start_time),
          time: formatTime(ev.start_time),
          service: ev.service.name,
          address: ev.service.hairdresser.user.address,
          phone: ev.service.hairdresser.user.phone,
          status: ev.service.status,
        }));
        setReserves(converted);  
        console.log('Reserves fetched successfully:', converted);
        /*if (Array.isArray(reserveResponse.data)) { 
          setReserves(reserveResponse.data);
        }*/
      } catch (error) {
        console.error('Error fetching reserves:', error);
        Alert.alert('Erro', 'Falha ao buscar reservas');
      } finally {
        setFetchingReserves(false);
      }
    };
    
    fetchReserves();
  }, [customer]);
  
  // Helper function to get status color
  const getStatusColor = (status: string) => {
    switch(status.toLowerCase()) {
      case 'confirmado':
        return '#4CAF50'; // Green
      case 'aguardando confirmação':
        return '#FF9800'; // Orange
      case 'finalizado':
        return '#2196F3'; // Blue
      default:
        return '#757575'; // Grey
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView>
        <View style={styles.content}>
          <Text style={styles.headerText}>Meus Agendamentos</Text>
          
          {isFetchingReserves ? (
            <ActivityIndicator size="large" color="#FF6B00" style={styles.loader} />
          ) : reserves.length > 0 ? (
            <View style={styles.reservesContainer}>
              {reserves.map((reserve) => (
                <View key={reserve.id} style={styles.reserveCard}>
                  <View style={styles.hairdresserInfoContainer}>
                    <View style={styles.profileCircle} />
                    <View style={styles.hairdresserDetailsContainer}>
                      <View style={{display: 'flex', flexDirection: 'row'}}>
                        <Text style={styles.hairdresserFirstName}>
                          {reserve.name || 'Camilly Borgaco'}
                        </Text>
                      </View>
                      <Text style={styles.reserveDetailText}>
                        {`Dia: ${(reserve.date)}`}
                        <Text style={styles.spacer}> · </Text>
                        {`Hora: ${(reserve.time)}`}
                      </Text>
                      <Text style={styles.reserveDetailText}>
                        {`Serviço: ${reserve.service || 'SOS Cachos'}`}
                      </Text>
                      <View style={styles.statusContainer}>
                        <Text style={styles.statusLabel}>Status:</Text>
                        <Text style={[styles.statusValue, { color: getStatusColor('aguardando confirmação') }]}>
                          { 'Aguardando confirmação' }
                        </Text>
                      </View>
                      <TouchableOpacity style={styles.moreInfoButton} onPress={()=>handleMoreInfo(reserve)}>
                        <Text style={styles.moreInfoButtonText}>Mais Informações</Text>
                    </TouchableOpacity>
                    </View>
                  </View>
                </View>
              ))}
            </View>
          ) : (
            <View style={styles.emptyContainer}>
              <Text style={styles.emptyText}>Você não possui agendamentos</Text>
            </View>
          )}
        </View>
      </ScrollView>
      <BottomTabBar />
    </SafeAreaView>
  );
}
