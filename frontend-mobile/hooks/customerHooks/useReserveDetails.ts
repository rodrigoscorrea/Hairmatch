import { useState, useEffect, useMemo, useCallback } from 'react';
import { useRouter, useLocalSearchParams, useFocusEffect } from 'expo-router';
import { Alert } from 'react-native';
import { getReserveById } from '@/services/reserve.service'; 
import { ReserveWithService } from '@/models/Reserve.types';
import { deleteReview } from '@/services/review.service';

export const useReserveDetails = () => {
  const router = useRouter();
  const { id } = useLocalSearchParams<{ id: string }>();
  const [menuVisible, setMenuVisible] = useState<boolean>(false);
  const [deletionModalVisible, setDeletionModalVisible] = useState<boolean>(false);
  const [reserve, setReserve] = useState<ReserveWithService | null>(null);
  const [loading, setLoading] = useState(true);
  const [modalVisible, setModalVisible] = useState(false);

  const fetchReserve = useCallback(async () => {
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
  }, [id]);

  useFocusEffect(
    useCallback(() => {
      fetchReserve();
    }, [fetchReserve])
  );

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

  const handleDeleteReview = async () => {
    if (!reserve?.review?.id) {
        Alert.alert("Erro", "Não foi possível encontrar a avaliação para excluir.");
        return;
    }
    try {
        await deleteReview(reserve.review.id);
        setReserve(currentReserve => {
            if (!currentReserve) return null;
            return { ...currentReserve, review: null };
        });
        setDeletionModalVisible(false);
        setMenuVisible(false);
    } catch (error) {
        console.log('error to deletion review', error);
        Alert.alert("Erro", "Não foi possível excluir a avaliação. Tente novamente.");
    }
  }

  return {
    loading,
    reserve,
    modalVisible,
    setModalVisible,
    evaluationEnabled,
    handleBack,
    confirmCancel,
    handleReviewScreen,
    menuVisible,
    setMenuVisible,
    deletionModalVisible,
    setDeletionModalVisible,
    handleDeleteReview
  };
};