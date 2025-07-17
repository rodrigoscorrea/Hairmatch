import { useState, useCallback } from 'react';
import { Alert } from 'react-native';
import { useRouter, useFocusEffect } from 'expo-router';
import { useAuth } from '@/app/_layout';
import { getCustomerReserves } from '@/services/reserve.service';
import { ReserveWithService } from '@/models/Reserve.types';

export const useReserves = () => {
  const { userInfo } = useAuth();
  const router = useRouter(); 
  const [reserves, setReserves] = useState<ReserveWithService[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useFocusEffect(
    useCallback(() => {
      const fetchReserves = async () => {
        const customerId = userInfo?.customer?.id;

        if (!customerId) {
          setIsLoading(false);
          return;
        }
        setIsLoading(true); 
        try {
          const reserveResponse = await getCustomerReserves(customerId);
          if (Array.isArray(reserveResponse.data)) { 
            setReserves(reserveResponse.data);
          }
        } catch (error) {
          console.error('Error fetching reserves:', error);
          Alert.alert('Erro', 'Falha ao buscar seus agendamentos.');
        } finally {
          setIsLoading(false);
        }
      };
      
      fetchReserves();
      return () => {
      };
    }, [userInfo])
  );

  const getStatusColor = (status: string) => {
    switch(status?.toLowerCase()) {
      case 'confirmado': return '#4CAF50'; // Green
      case 'aguardando confirmação': return '#FF9800'; // Orange
      case 'finalizado': return '#2196F3'; // Blue
      default: return '#757575'; // Grey
    }
  };

  const handleNavigateToDetails = (reserveId: number) => {
    router.push(`/(app)/(customer)/reserves/${reserveId}`);
  };

  return {
    isLoading,
    reserves,
    getStatusColor,
    handleNavigateToDetails
  };
};