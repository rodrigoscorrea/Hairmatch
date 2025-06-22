import { useState, useEffect } from 'react';
import { RouteProp, useNavigation, useRoute } from '@react-navigation/native';
import { RootStackParamList } from '@/app/../models/RootStackParams.types';
import { StackNavigationProp } from '@react-navigation/stack';
import { ERROR_MESSAGES } from '@/app/../constants/errorMessages';
import { useRouter } from 'expo-router';
import { useRegistration } from '@/contexts/RegistrationContext';

type AddressScreenRouteProp = RouteProp<RootStackParamList, 'Address'>;
type AddressScreenNavigationProp = StackNavigationProp<RootStackParamList>;

export const useAddress = () =>{
  const router = useRouter();
  const { registrationData, setRegistrationData } = useRegistration();
  const route = useRoute<AddressScreenRouteProp>();
  const personalData = route.params?.personalData;
  const [errors, setErrors] = useState<{ [key: string]: boolean }>({});
  const [errorModal, setErrorModal] = useState({ visible: false, message: '' });

  const handleInputChange = (field: keyof typeof registrationData, value: string) => {
    setRegistrationData(prev => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: false }));
    }
  };

  const validateFields = () => {
    const newErrors: { [key: string]: boolean } = {};
    let errorList: string[] = [];
    if (!registrationData.address) { newErrors.address = true; errorList.push(ERROR_MESSAGES.address_required); }
    if (!registrationData.number || registrationData.number.length > 6) { newErrors.number = true; errorList.push(ERROR_MESSAGES.number_invalid); }
    if (!registrationData.neighborhood) { newErrors.neighborhood = true; errorList.push(ERROR_MESSAGES.neighborhood_required); }
    if (!registrationData.postal_code) { newErrors.postal_code = true; errorList.push(ERROR_MESSAGES.postal_code_required); }
    if (!registrationData.city) { newErrors.city = true; errorList.push(ERROR_MESSAGES.city_required); }
    if (!registrationData.state || registrationData.state.length !== 2) { newErrors.state = true; errorList.push(ERROR_MESSAGES.state_required); }
    setErrors(newErrors);
    if (errorList.length > 0) {
      setErrorModal({ visible: true, message: errorList[0] });
      return false;
    }
    return true;
  }
  // Função para o botão "Próximo"
  const handleNext = () => {
    if (!validateFields()) return;
    
    // Navega para a próxima tela com todos os dados acumulados
    router.push('/(auth)/register/preferences');
  };


  // Função para o botão "Voltar"
  const handleGoBack = () => {
    router.back();
  };

  useEffect(() => {
    }, [personalData]);
  
  return {
    handleInputChange,
    errors,
    errorModal,
    setErrorModal,
    handleNext,
    handleGoBack,
    closeErrorModal: () => setErrorModal({ ...errorModal, visible: false }),
  };
}
