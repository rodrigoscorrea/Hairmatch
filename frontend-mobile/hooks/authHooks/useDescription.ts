import { useState } from 'react';
import { useRouter } from 'expo-router';
import { Alert, Platform } from 'react-native';
import { useRegistration } from '@/contexts/RegistrationContext';
import { useAuth } from '@/app/_layout';
import { requestAiResume } from '@/services/auth-user.service';
import { stripNonDigits } from '@/utils/forms';

export const useDescriptionForm = () => {
  const router = useRouter();
  const { registrationData, setRegistrationData } = useRegistration();
  const { signUp, loadSession } = useAuth();
  const isGoogleMode = !!registrationData.google_signup_token;

  const [isLoading, setIsLoading] = useState(false);
  const [showAiDescriptionModal, setShowAiDescriptionModal] = useState(true);
  const [errorModal, setErrorModal] = useState({ visible: false, message: '' });

  const handleResumeChange = (text: string) => {
    setRegistrationData(prev => ({ ...prev, resume: text }));
  };

  const handleRequestAiResume = async () => {
    setShowAiDescriptionModal(false);
    setIsLoading(true);
    try {
      const responseData = await requestAiResume({
        first_name: registrationData.first_name!,
        last_name: registrationData.last_name!,
        experience_time: registrationData.experience_time!,
        experiences: registrationData.experiences!,
        products: registrationData.products!,
        preferences: registrationData.preferences!,
      });
      setRegistrationData(prev => ({ ...prev, resume: responseData }));
    } catch (error) {
      console.error("AI Resume Error:", error);
      Alert.alert("Erro", "Não foi possível gerar a descrição com IA.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleFinish = async () => {
    setIsLoading(true);    
    const formData = new FormData();
    
    const allData: any = { ...registrationData, rating: 5};
    
    allData.phone = stripNonDigits(allData.phone!);
    allData.postal_code = stripNonDigits(allData.postal_code!);
    if (allData.cpf) allData.cpf = stripNonDigits(allData.cpf);
    if (allData.cnpj) allData.cnpj = stripNonDigits(allData.cnpj);

    // Google mode: no password and no email (the backend uses the token's email), but with the signup token.
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
          // The 201 already brought the session cookie: RootLayoutNav leads to the agenda (GAUTH-26).
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
        console.error("Full sign-up error:", error);
        
        const errorMessage = error.error || error.message || "Erro desconhecido";
        setErrorModal({ visible: true, message: errorMessage }); 
    } finally {
        setIsLoading(false);
    }
  };
  
  const handleBack = () => {
    router.back();
  };

  // --- FIX START ---
  // Dedicated function to close the modal and redirect.
  // Ensures the user sees the error before being navigated away.
  const handleCloseErrorModal = () => {
    setErrorModal({ visible: false, message: '' }); // First, hide the modal
    // In Google mode, the final submission error keeps the user on the wizard (GAUTH-27).
    if (!isGoogleMode) {
      router.replace('/(auth)/login'); // Second, redirect the user
    }
  };
  // --- FIX END ---

  return {
    isLoading,
    showAiDescriptionModal,
    setShowAiDescriptionModal,
    formData: registrationData,
    handleResumeChange,
    handleRequestAiResume,
    handleFinish,
    handleBack,
    errorModal,
    // Ensures the `closeErrorModal` prop uses the new fixed function
    closeErrorModal: handleCloseErrorModal,
  };
};