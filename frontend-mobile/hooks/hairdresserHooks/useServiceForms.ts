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
  const [errors, setErrors] = useState<{ [key: string]: boolean }>({});
  const [errorModal, setErrorModal] = useState({ visible: false, message: '' });



  const validateFields = () => {
    const errors: { [key: string]: boolean } = {};
    let errorList: string[] = [];

    if (!name.trim()) {
      errors.name = true;
      errorList.push('Nome é obrigatório.');
    }
    if(name.length > 250){
      errors.name = true;
      errorList.push('Nome deve ter no máximo 250 caracteres.');
    }
    if (!description.trim()) {
      errors.description = true;
      errorList.push('Descrição é obrigatória.');
    }
    if(description.length > 500){
      errors.description = true;
      errorList.push('Descrição deve ter no máximo 500 caracteres.');
    }
    if (!price || isNaN(Number(price)) || Number(price) <= 0) {
      errors.price = true;
      errorList.push('Preço deve ser maior que 0.');
    }
    if (duration <= 0) {
      errors.duration = true;
      errorList.push('Duração deve ser maior que 0.');
    }
    if (duration.toString().length > 3) {
      errors.duration = true;
      errorList.push('Duração deve ter no máximo 4 dígitos.');
    }
    setErrors(errors);
    if (errorList.length > 0) {
      setErrorModal({ visible: true, message: errorList[0] });
      return false;
    }
    return true ;
  }

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
    if (!validateFields()) {return;}

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
    handleDurationChange,
    errors,
    errorModal,
    closeErrorModal: () => setErrorModal({ ...errorModal, visible: false }),
  };
};