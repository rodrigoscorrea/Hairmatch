import { useState, useEffect } from 'react';
import { Alert } from 'react-native';
import { useRouter } from 'expo-router';
import { useAuth } from '@/app/_layout';
import { useBottomTab } from '@/contexts/BottomTabContext';
import { getCustomerReserves } from '@/services/reserve.service';
import { ReserveWithService } from '@/models/Reserve.types';

export const useReserves = () => {
  const { userInfo } = useAuth();
  const { setActiveTab } = useBottomTab();
  const router = useRouter(); 
  const [reserves, setReserves] = useState<ReserveWithService[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    setActiveTab('Reserves');
    
    const fetchReserves = async () => {
      // Get the customer ID directly from our main Auth context
      const customerId = userInfo?.customer?.id;

      if (!customerId) {
        // Don't fetch if we don't have the ID yet. The effect will re-run when userInfo is available.
        setIsLoading(false);
        return;
      }
      
      try {
        setIsLoading(true);
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
  }, [userInfo]); // This effect depends on userInfo to get the ID

  // Helper function to get status color
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