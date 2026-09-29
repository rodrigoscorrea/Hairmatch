import { useState, useEffect, useRef } from 'react';
import { TextInput } from 'react-native';
import { RouteProp, useNavigation, useRoute } from '@react-navigation/native';
import { RootStackParamList } from '@/app/../models/RootStackParams.types';
import { StackNavigationProp } from '@react-navigation/stack';
import { ERROR_MESSAGES } from '@/app/../constants/errorMessages';
import { useRouter } from 'expo-router';
import { useRegistration } from '@/contexts/RegistrationContext';
import { formatCEP, stripNonDigits } from '@/app/../utils/forms';
import { CepAddress } from '@/services/cep.service';
import { useCepLookup } from './useCepLookup';

type AddressScreenRouteProp = RouteProp<RootStackParamList, 'Address'>;
type AddressScreenNavigationProp = StackNavigationProp<RootStackParamList>;

export const useAddress = () =>{
  const router = useRouter();
  const { registrationData, setRegistrationData } = useRegistration();
  const route = useRoute<AddressScreenRouteProp>();
  const personalData = route.params?.personalData;
  const [errors, setErrors] = useState<{ [key: string]: boolean }>({});
  const [errorModal, setErrorModal] = useState({ visible: false, message: '' });
  const { loading: cepLoading, message: cepMessage, lookup, cancel } = useCepLookup();
  const numberInputRef = useRef<TextInput>(null);
  // Latest form state for the async lookup callback, which would otherwise see a stale closure.
  const registrationDataRef = useRef(registrationData);
  registrationDataRef.current = registrationData;
  // Values the last CEP lookup wrote, to tell them apart from what the user typed.
  const lastAutofillRef = useRef<Partial<CepAddress>>({});

  const handleInputChange = (field: keyof typeof registrationData, value: string) => {
    setRegistrationData(prev => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: false }));
    }
  };

  const applyCepAddress = (found: CepAddress) => {
    const fields = ['address', 'neighborhood', 'city', 'state'] as const;
    const current = registrationDataRef.current;
    const merged: Partial<CepAddress> = {};
    fields.forEach(field => {
      if (found[field]) {
        merged[field] = found[field];
      } else if (current[field] === lastAutofillRef.current[field]) {
        merged[field] = '';
      } else {
        merged[field] = current[field];
      }
    });
    lastAutofillRef.current = merged;
    setRegistrationData(prev => ({ ...prev, ...merged }));
    setErrors(prev => {
      const next = { ...prev };
      fields.forEach(field => { next[field] = false; });
      return next;
    });
    numberInputRef.current?.focus();
  };

  const handlePostalCodeChange = (text: string) => {
    const masked = formatCEP(text);
    handleInputChange('postal_code', masked);
    const digits = stripNonDigits(masked);
    if (digits.length === 8) {
      lookup(digits, applyCepAddress);
    } else {
      cancel();
    }
  };

  const validateFields = () => {
    const newErrors: { [key: string]: boolean } = {};
    let errorList: string[] = [];
    if (!registrationData.address) { newErrors.address = true; errorList.push(ERROR_MESSAGES.address_required); }
    if (!registrationData.number || registrationData.number.length > 6) { newErrors.number = true; errorList.push(ERROR_MESSAGES.number_invalid); }
    if (!registrationData.neighborhood) { newErrors.neighborhood = true; errorList.push(ERROR_MESSAGES.neighborhood_required); }
    if (!registrationData.postal_code) { newErrors.postal_code = true; errorList.push(ERROR_MESSAGES.postal_code_required); }
    if(registrationData.postal_code?.length !== 9) {newErrors.postal_code = true; errorList.push(ERROR_MESSAGES.postal_code_invalid);}
    if (!registrationData.city) { newErrors.city = true; errorList.push(ERROR_MESSAGES.city_required); }
    if (!registrationData.state || registrationData.state.length !== 2) { newErrors.state = true; errorList.push(ERROR_MESSAGES.state_required); }
    setErrors(newErrors);
    if (errorList.length > 0) {
      setErrorModal({ visible: true, message: errorList[0] });
      return false;
    }
    return true;
  }
  // Function for the "Next" button
  const handleNext = () => {
    if (!validateFields()) return;

    // Navigates to the next screen with all the accumulated data
    router.push('/(auth)/register/preferences');
  };


  // Function for the "Back" button
  const handleGoBack = () => {
    router.back();
  };

  useEffect(() => {
    }, [personalData]);
  
  return {
    handleInputChange,
    handlePostalCodeChange,
    cepLoading,
    cepMessage,
    numberInputRef,
    errors,
    errorModal,
    setErrorModal,
    handleNext,
    handleGoBack,
    closeErrorModal: () => setErrorModal({ ...errorModal, visible: false }),
  };
}
