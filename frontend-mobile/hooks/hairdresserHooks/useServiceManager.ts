// hooks/hairdresserHooks/useServiceManager.ts
import { useState, useEffect, useCallback } from 'react';
import { useRouter, useFocusEffect } from 'expo-router';
import { useAuth } from '@/app/_layout';
import { deleteService, listServicesByHairdresser } from '@/services/service.service';
import { ServiceResponse } from '@/models/Service.types';
import axios from 'axios';

export const useServiceManager = () => {
  const router = useRouter();
  const { userInfo } = useAuth();
  const hairdresserId = userInfo?.hairdresser?.id;

  const [services, setServices] = useState<ServiceResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [modalVisible, setModalVisible] = useState(false);
  const [selectedServiceId, setSelectedServiceId] = useState<number | null>(null);
  const [errorModal, setErrorModal] = useState<{ visible: boolean; message: string }>({ visible: false, message: '' });

  useFocusEffect(
    useCallback(() => {
      // Define the async function inside the effect's callback
      const fetchServices = async () => {
        if (!hairdresserId) {
            // Set loading to false if we can't fetch, to avoid infinite spinner
            setIsLoading(false); 
            return;
        }
        
        setIsLoading(true);
        try {
          const response = await listServicesByHairdresser(hairdresserId);
          setServices(response.data);
        } catch (error) {
          console.error("Failed to fetch services:", error);
        } finally {
          setIsLoading(false);
        }
      };
      fetchServices();
      return () => {
      };
    }, [hairdresserId])
  );

  const handleDelete = (serviceId: number) => {
    setSelectedServiceId(serviceId);
    setModalVisible(true);
  };

  const confirmDelete = async () => {
    if (!selectedServiceId) return;
    try {
      await deleteService(selectedServiceId);
      setServices(currentServices => currentServices.filter(s => s.id !== selectedServiceId));
    } catch (error) {
      if (axios.isAxiosError(error) && error.response) {
        if (error.response.status === 400) {
          setErrorModal({ visible: true, message: 'Não é possível excluir esse serviço pois há um agendamento atrelado a ele' });
        } else {
          setErrorModal({ visible: true, message: "Ocorreu um erro no servidor. Tente novamente mais tarde." });
        }
      } else {
        setErrorModal({ visible: true, message: "Não foi possível conectar ao servidor." });
      }
    } finally {
      setModalVisible(false);
      setSelectedServiceId(null);
    }
  };

  const goToCreate = () => router.push('/(app)/(hairdresser)/services/create');
  
  const goToEdit = (serviceId: number) => router.push(`/(app)/(hairdresser)/services/edit/${serviceId}`);

  return {
    isLoading,
    services,
    modalVisible,
    setModalVisible,
    selectedServiceId,
    handleDelete,
    confirmDelete,
    goToCreate,
    goToEdit,
    errorModal,
    closeErrorModal: () => setErrorModal({ visible: false, message: '' }),
  };
};