// hooks/usePreferencesForm.ts
import { useState, useEffect } from 'react';
import { useRouter } from 'expo-router';
import { Alert } from 'react-native';
import { Platform } from 'react-native';
import { useRegistration } from '@/contexts/RegistrationContext';
import { useAuth } from '@/app/_layout'; // Use the useAuth hook from our root layout
import { listPreferences } from '@/services/preferences.service';
import { Preference } from '@/models/Preferences.types';
import { UserRole } from '@/models/User.types';

import { stripNonDigits } from '@/utils/forms';

export const usePreferencesForm = () => {
  const router = useRouter();
  const { registrationData, setRegistrationData } = useRegistration();
  const { signUp, loadSession } = useAuth(); // Get signUp from the AuthContext
  const isGoogleMode = !!registrationData.google_signup_token;

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
    
    const formData = new FormData();
    
    const allData: any = { ...registrationData, preferences: finalPreferences, rating: 5};
    
    allData.phone = stripNonDigits(allData.phone!);
    allData.postal_code = stripNonDigits(allData.postal_code!);
    if (allData.cpf) allData.cpf = stripNonDigits(allData.cpf);
    if (allData.cnpj) allData.cnpj = stripNonDigits(allData.cnpj);

    // Modo Google: sem senha e sem e-mail (o backend usa o e-mail do token), mas com o token de cadastro.
    if (isGoogleMode) {
        delete allData.password;
        delete allData.confirmPassword;
        delete allData.email;
    } else {
        delete allData.google_signup_token;
    }
  
    Object.keys(allData).forEach(key => {
        if (key !== 'profile_picture' && allData[key] !== null && allData[key] !== undefined) {
            if (key === 'preferences') {
                formData.append(key, JSON.stringify(allData[key]));
            } else {
                formData.append(key, allData[key].toString());
            }
        }
    });

    if (registrationData.profile_picture) {
        if (Platform.OS === 'web') {
          registrationData.profile_picture.name = `${registrationData.email}/${registrationData.profile_picture.name}`;
          const response = await fetch(registrationData.profile_picture.uri);
          const blob = await response.blob();
          formData.append('profile_picture', blob, registrationData.profile_picture.name);
        } else {
            const fileData = {
              uri: registrationData.profile_picture.uri,
              name: `${registrationData.email}/${registrationData.profile_picture.name}`,
              type: registrationData.profile_picture.type,
          };

          formData.append('profile_picture', fileData as any);
        }
    } else {
        console.log('No profile picture found in registrationData');
    }

    try {
        await signUp(formData);

        if (isGoogleMode) {
          // O 201 já trouxe o cookie de sessão: o RootLayoutNav leva à home do papel (GAUTH-26).
          const session = await loadSession();
          if (!session.success) {
            setErrorModal({ visible: true, message: session.error || 'Erro desconhecido' });
          }
          return;
        }
    
        Alert.alert(
          "Cadastro concluído!",
          "Sua conta foi criada com sucesso. Agora você será direcionado para a tela de login."
        );
        router.replace('/(auth)/login'); 

    } catch (error: any) {
      const errorMessage = error.error || error.message || "Erro desconhecido";
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
      // Em modo Google, o erro do envio final mantém o usuário no wizard (GAUTH-27).
      if (!isGoogleMode) {
        router.replace('/(auth)/login');
      }
    },
  };
};