import { ActivityIndicator, Alert, StyleSheet, Text, View, SafeAreaView } from 'react-native'
import React, { useContext, useEffect, useState } from 'react'
import { getCustomerReserves } from '@/app/services/reserve.service';
import { useBottomTab } from '../../contexts/BottomTabContext'
import BottomTabBar from '../../components/BottomBar'

interface Reserve {
  id: number;
  start_time: string;
  review?: string;
}

export default function ReservesScreen() {
  const [isFetchingReserves, setFetchingReserves] = useState(true);
  const [reserves, setReserves] = useState<Reserve[]>([]);
  const { customer, setActiveTab } = useBottomTab();
  
  useEffect(() => {
    setActiveTab('Reserves');
    
    const fetchReserves = async () => {  
      if (!customer ) {
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

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        <Text style={styles.headerText}>Minhas Reservas</Text>
        
        {isFetchingReserves ? (
          <ActivityIndicator size="large" color="#FF6B00" style={styles.loader} />
        ) : reserves.length > 0 ? (
          <View style={styles.reservesContainer}>
            {reserves.map((reserve) => (
              <View key={reserve.id} style={styles.reserveItem}>
                <Text style={styles.reserveText}>
                  {`ID: ${reserve.id}`}
                </Text>
                <Text style={styles.reserveDetailText}>
                  {`Data: ${new Date(reserve.start_time).toLocaleDateString()}`}
                </Text>
                <Text style={styles.reserveDetailText}>
                  {`Horário: ${new Date(reserve.start_time).toLocaleTimeString()}`}
                </Text>
                {reserve.review && (
                  <Text style={styles.reserveDetailText}>
                    {`Avaliação: ${reserve.review}`}
                  </Text>
                )}
              </View>
            ))}
          </View>
        ) : (
          <View style={styles.emptyContainer}>
            <Text style={styles.emptyText}>Você não possui reservas</Text>
          </View>
        )}
      </View>
      
      <BottomTabBar />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
  content: {
    flex: 1,
    padding: 16,
  },
  headerText: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 20,
    marginTop: 40,
    textAlign: 'center',
    color: '#FF6B00',
  },
  loader: {
    flex: 1,
    justifyContent: 'center',
  },
  reservesContainer: {
    flex: 1,
  },
  reserveItem: {
    backgroundColor: '#FDF0E7',
    borderRadius: 8,
    padding: 16,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.2,
    shadowRadius: 1,
    elevation: 2,
  },
  reserveText: {
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 8,
    color: '#FF6B00',
  },
  reserveDetailText: {
    fontSize: 14,
    color: '#666',
    marginBottom: 4,
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