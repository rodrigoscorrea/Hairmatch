import { useState, useEffect } from 'react';
import { RouteProp, useNavigation, useRoute } from '@react-navigation/native';
import { RootStackParamList } from '@/app/models/RootStackParams.types';
import { StackNavigationProp } from '@react-navigation/stack';
import { ERROR_MESSAGES } from '@/app/constants/errorMessages';

type AddressScreenRouteProp = RouteProp<RootStackParamList, 'Address'>;
type AddressScreenNavigationProp = StackNavigationProp<RootStackParamList>;

export const useAddress = () =>{
  const navigation = useNavigation<any>();
  const route = useRoute<AddressScreenRouteProp>();
  const personalData = route.params?.personalData;

  const [formData, setFormData] = useState({
      address: '',
      number: '',
      complement: '',
      neighborhood: '',
      postal_code: '',
      city: '',
      state: ''
  });
  const [errors, setErrors] = useState<{ [key: string]: boolean }>({});
  const [errorModal, setErrorModal] = useState({ visible: false, message: '' });

  const handleInputChange = (field: keyof typeof formData, value: string) => {
    //this is a generic handler for all input changes
    //TODO: how can i put this function in a separate file?
    setFormData(prev => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: false }));
    }
  };

  const validateFields = () => {
    const newErrors: { [key: string]: boolean } = {};
    let errorList: string[] = [];
    if (!formData.address) { newErrors.address = true; errorList.push(ERROR_MESSAGES.address_required); }
    if (!formData.number || formData.number.length > 6) { newErrors.number = true; errorList.push(ERROR_MESSAGES.number_invalid); }
    if (!formData.neighborhood) { newErrors.neighborhood = true; errorList.push(ERROR_MESSAGES.neighborhood_required); }
    if (!formData.postal_code) { newErrors.postal_code = true; errorList.push(ERROR_MESSAGES.postal_code_required); }
    if (!formData.city) { newErrors.city = true; errorList.push(ERROR_MESSAGES.city_required); }
    if (!formData.state || formData.state.length !== 2) { newErrors.state = true; errorList.push(ERROR_MESSAGES.state_required); }
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
    navigation.navigate('Preferences', { personalData, formData });
  };
    const handleAddress = async () => {
    if (!validateFields()) return;

    navigation.navigate('Preferences', { personalData, formData });
  };


  // Função para o botão "Voltar"
  const handleGoBack = () => {
    navigation.goBack();
  };

  useEffect(() => {
    }, [personalData]);
  
  return {
    formData,
    handleInputChange,
    errors,
    errorModal,
    setErrorModal,
    handleNext,
    handleAddress,
    handleGoBack,
    closeErrorModal: () => setErrorModal({ ...errorModal, visible: false }),
  };
}
