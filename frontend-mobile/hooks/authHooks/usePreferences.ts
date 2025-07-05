// hooks/usePreferencesForm.ts
import { useState, useEffect } from 'react';
import { useRouter } from 'expo-router';
import { Alert } from 'react-native';

import { useRegistration } from '@/contexts/RegistrationContext';
import { useAuth } from '@/app/_layout'; // Use the useAuth hook from our root layout
import { listPreferences } from '@/services/preferences.service';
import { Preference } from '@/models/Preferences.types';
import { UserRole } from '@/models/User.types';

import { stripNonDigits } from '@/utils/forms';

export const usePreferencesForm = () => {
  const router = useRouter();
  const { registrationData, setRegistrationData } = useRegistration();
  const { signUp } = useAuth(); // Get signUp from the AuthContext

  // --- State for the UI ---
  const [isLoading, setIsLoading] = useState(false);
  const [isFetchingPreferences, setIsFetchingPreferences] = useState(true);
  const [preferences, setPreferences] = useState<Preference[]>([]);
  const [showSkipModal, setShowSkipModal] = useState(false);
  const [errorModal, setErrorModal] = useState({ visible: false, message: '' });


  // --- Fetch Preferences on Mount ---
  useEffect(() => {
    const fetchPreferences = async () => {
      try {
        setIsFetchingPreferences(true);
        const response = await listPreferences();
        if (response && Array.isArray(response)) {
          setPreferences(response);
        }
      } catch (error) {
        console.error('Error fetching preferences:', error);
        Alert.alert('Erro', 'Não foi possível carregar as preferências. Tente novamente.');
      } finally {
        setIsFetchingPreferences(false);
      }
    };

    fetchPreferences();
  }, []);

  // --- Event Handlers ---
  const togglePreference = (id: number) => {
    // Get the current list of preferences from our context state
    const currentSelected = registrationData.preferences || [];
    
    let newSelected: number[];
    if (currentSelected.includes(id)) {
      newSelected = currentSelected.filter(prefId => prefId !== id);
    } else {
      newSelected = [...currentSelected, id];
    }
    
    // Update the central context state immediately
    setRegistrationData(prev => ({ ...prev, preferences: newSelected }));
  };

  const finishRegistration = async (finalPreferences: number[]) => {
    setIsLoading(true);
    try {
      const payload = {
        ...registrationData,
        phone: stripNonDigits(registrationData.phone!),
        postal_code: stripNonDigits(registrationData.postal_code!),
        cpf: stripNonDigits(registrationData.cpf!),
        cnpj: stripNonDigits(registrationData.cnpj!),
        preferences: finalPreferences,
        };

      await signUp(
        payload.first_name,
        payload.last_name,
        payload.phone,
        payload.email,
        payload.password,
        payload.address,
        payload.number,
        payload.neighborhood,
        payload.complement,
        payload.postal_code,
        payload.state,
        payload.city,
        payload.role,
        5.0,
        payload.cpf,
        payload.cnpj,
        finalPreferences 
      );
      Alert.alert(
        "Cadastro concluído!",
        "Sua conta foi criada com sucesso. Agora você será direcionado para a tela de login."
      );
  
      router.replace('/(auth)/login'); 
      

    } catch (error: any) {
      const errorMessage = error.response?.data?.error || "Erro desconhecido";
      setErrorModal({ visible: true, message: errorMessage }); 
    } finally {
      setIsLoading(false);
    }
  };
  
  const handleNext = () => {
    const finalPreferences = registrationData.preferences || [];

    if (registrationData.role === UserRole.CUSTOMER) {
      finishRegistration(finalPreferences);
    } else {
      router.push('/(auth)/register/professional-story'); 
    }
  };

  const handleSkip = () => {
    setShowSkipModal(false);
    if (registrationData.role === UserRole.CUSTOMER) {
      finishRegistration([]);
    } else {
      setRegistrationData(prev => ({...prev, preferences: []}));
      router.push('/(auth)/register/professional-story');
    }
  };

  return {
    isLoading,
    isFetchingPreferences,
    preferences,
    selectedPreferences: registrationData.preferences || [],
    showSkipModal,
    setShowSkipModal,
    role: registrationData.role,
    togglePreference,
    handleNext,
    handleSkip,
    errorModal,
    closeErrorModal: () => {
      setErrorModal({ ...errorModal, visible: false });
      router.replace('/(auth)/login');
    },
  };
};