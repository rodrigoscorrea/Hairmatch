import { ActivityIndicator, Alert, StyleSheet, Text, View, SafeAreaView, TouchableOpacity, ScrollView } from 'react-native'
import React, { useEffect, useState } from 'react'
import { getCustomerReserves } from '@/app/services/reserve.service';
import { useBottomTab } from '../../contexts/BottomTabContext';
import BottomTabBar from '../../components/BottomBar';
import { format } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import { ReserveWithService } from '@/app/models/Reserve.types';
import { formatDate } from '@/app/utils/date-formater';
import { formatTime } from '@/app/utils/time-formater';

export default function ReservesScreen() {
  const [isFetchingReserves, setFetchingReserves] = useState(true);
  const [reserves, setReserves] = useState<ReserveWithService[]>([]);
  const { customer, setActiveTab } = useBottomTab();
  
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
        if (Array.isArray(reserveResponse.data)) { 
          setReserves(reserveResponse.data);
        }
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
                          {reserve.service.hairdresser.user.first_name || 'Camilly Borgaco'}
                        </Text>
                        <Text style={styles.hairdresserLastName}>
                          {reserve.service.hairdresser.user.last_name || 'Camilly Borgaco'}
                        </Text>
                      </View>
                      <Text style={styles.reserveDetailText}>
                        {`Dia: ${formatDate(reserve.start_time)}`}
                        <Text style={styles.spacer}> · </Text>
                        {`Hora: ${formatTime(reserve.start_time)}`}
                      </Text>
                      <Text style={styles.reserveDetailText}>
                        {`Serviço: ${reserve.service.name || 'SOS Cachos'}`}
                      </Text>
                      <View style={styles.statusContainer}>
                        <Text style={styles.statusLabel}>Status:</Text>
                        <Text style={[styles.statusValue, { color: getStatusColor('aguardando confirmação') }]}>
                          { 'Aguardando confirmação' }
                        </Text>
                      </View>
                    </View>
                  </View>
                  
                  <TouchableOpacity style={styles.moreInfoButton}>
                    <Text style={styles.moreInfoButtonText}>Mais Informações</Text>
                  </TouchableOpacity>
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

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FFF8F3', // Light cream background as in the image
  },
  content: {
    flex: 1,
    padding: 16,
    paddingTop: 60, // Extra padding at the top
  },
  headerText: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 20,
    textAlign: 'center',
    color: '#333',
  },
  loader: {
    flex: 1,
    justifyContent: 'center',
  },
  reservesContainer: {
    flex: 1,
  },
  reserveCard: {
    backgroundColor: '#FFEBDA', // Light orange background for cards
    borderRadius: 16,
    padding: 16,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  hairdresserInfoContainer: {
    flexDirection: 'row',
    marginBottom: 12,
  },
  profileCircle: {
    width: 50,
    height: 50,
    borderRadius: 25,
    backgroundColor: '#E0E0E0', // Gray circle for profile placeholder
    marginRight: 12,
  },
  hairdresserDetailsContainer: {
    flex: 1,
    justifyContent: 'center',
  },
  hairdresserFirstName: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 4,
  },
  hairdresserLastName: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 4,
    marginLeft: 4
  },
  reserveDetailText: {
    fontSize: 14,
    color: '#555',
    marginBottom: 2,
  },
  spacer: {
    color: '#999',
  },
  statusContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 4,
  },
  statusLabel: {
    fontSize: 14,
    color: '#555',
    marginRight: 4,
  },
  statusValue: {
    fontSize: 14,
    fontWeight: '600',
  },
  moreInfoButton: {
    backgroundColor: '#FF6B00', // Orange button
    borderRadius: 8,
    padding: 12,
    alignItems: 'center',
    marginTop: 8,
  },
  moreInfoButtonText: {
    color: '#FFF',
    fontWeight: '600',
    fontSize: 14,
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  emptyText: {
    fontSize: 16,
    color: '#666',
    textAlign: 'center',
  },
});