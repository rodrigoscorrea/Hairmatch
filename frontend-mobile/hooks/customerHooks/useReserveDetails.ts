import { useState, useEffect, useMemo } from 'react';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { Alert } from 'react-native';
import { getReserveById } from '@/services/reserve.service'; 
import { ReserveWithService } from '@/models/Reserve.types';

export const useReserveDetails = () => {
  const router = useRouter();
  const { id } = useLocalSearchParams<{ id: string }>();

  const [reserve, setReserve] = useState<ReserveWithService | null>(null);
  const [loading, setLoading] = useState(true);
  const [modalVisible, setModalVisible] = useState(false);

  useEffect(() => {
    const fetchReserve = async () => {
      if (!id) return;
      setLoading(true);
      try {
        const response = await getReserveById(Number(id)); 
        setReserve(response.data);
      } catch (error) {
        console.error("Failed to fetch reserve details:", error);
        Alert.alert("Erro", "Não foi possível carregar os detalhes do agendamento.");
      } finally {
        setLoading(false);
      }
    };
    fetchReserve();
  }, [id]);

  const evaluationEnabled = useMemo(() => {
    if (!reserve?.start_time) return false;
    const serviceDateTime = new Date(reserve.start_time);
    const now = new Date();
    return now > serviceDateTime;
  }, [reserve]);

  const handleBack = () => {
    router.push('/(app)/(customer)/reserves');
  };

  const confirmCancel = async () => {
    if(!id) return;
    try {
      // TODO implement cancelReserve
      //await cancelReserve(Number(id)); 
      setModalVisible(false);
      Alert.alert("Sucesso", "Agendamento cancelado.");
      router.back();
    } catch (error) {
        console.error("Failed to cancel reserve:", error)
        Alert.alert("Erro", "Não foi possível cancelar o agendamento.")
    }
  };

  const handleReviewScreen = (reserveId: number) => {
    router.push(`/review/${reserveId}`);
  }

  return {
    loading,
    reserve,
    modalVisible,
    setModalVisible,
    evaluationEnabled,
    handleBack,
    confirmCancel,
    handleReviewScreen
  };
};