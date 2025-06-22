// hooks/hairdresserHooks/useServiceForm.ts
import { useState, useEffect } from 'react';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { useAuth } from '@/app/_layout';
import { createService, editService, getServiceById } from '@/services/service.service';

export const useServiceForm = () => {
  const router = useRouter();
  const { userInfo } = useAuth();
  const hairdresserId = userInfo?.hairdresser?.id;

  // Check for an 'id' in the URL. If it exists, we are in "edit" mode.
  const { id: serviceId } = useLocalSearchParams<{ id?: string }>();
  const isEditMode = !!serviceId;

  // Form state
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [duration, setDuration] = useState(30);
  const [price, setPrice] = useState('');
  const [loading, setLoading] = useState(isEditMode);

  useEffect(() => {
    const fetchServiceData = async () => {
      if (!isEditMode) return;
      try {
        const response = await getServiceById(Number(serviceId));
        const service = response.data;
        setName(service.name);
        setDescription(service.description);
        setDuration(service.duration);
        setPrice(String(service.price));
      } catch (error) {
        console.error("Failed to fetch service for editing:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchServiceData();
  }, [isEditMode, serviceId]);

  const handleDurationChange = (text: string) => {
    const numericText = text.replace(/[^0-9]/g, '');
    const newDuration = parseInt(numericText, 10);

    setDuration(isNaN(newDuration) ? 0 : newDuration);
  };

  const handleSubmit = async () => {
    if (!hairdresserId) return;

    const serviceData = {
      hairdresser: hairdresserId,
      name,
      description,
      price,
      duration,
    };

    try {
      if (isEditMode) {
        await editService({ id: Number(serviceId), ...serviceData });
      } else {
        await createService(serviceData);
      }
      // Go back to the manager list after successful creation/edit
      router.back();
    } catch (error) {
      console.error("Error saving service:", error);
    }
  };
  
  const handleBack = () => router.back();

  return {
    isEditMode,
    loading,
    name, setName,
    description, setDescription,
    duration, setDuration,
    price, setPrice,
    handleSubmit,
    handleBack,
    handleDurationChange
  };
};