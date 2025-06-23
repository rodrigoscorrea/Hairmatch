// hooks/useDescriptionForm.ts
import { useState, useEffect } from 'react';
import { useRouter } from 'expo-router';
import { Alert } from 'react-native';

import { useRegistration } from '@/contexts/RegistrationContext';
import { useAuth } from '@/app/_layout';
import { requestAiResume } from '@/services/auth-user.service';
import { stripNonDigits } from '@/utils/forms';

export const useDescriptionForm = () => {
  const router = useRouter();
  const { registrationData, setRegistrationData } = useRegistration();
  const { signUp } = useAuth();

  const [isLoading, setIsLoading] = useState(false);
  const [showAiDescriptionModal, setShowAiDescriptionModal] = useState(true); // Show modal on entry

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
    try {
      const payload = {
        ...registrationData,
        phone: stripNonDigits(registrationData.phone!),
        postal_code: stripNonDigits(registrationData.postal_code!),
        cpf: stripNonDigits(registrationData.cpf!),
        cnpj: stripNonDigits(registrationData.cnpj!),
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
        5.0, // rating
        payload.cpf, 
        payload.cnpj,
        payload.preferences,
        payload.experience_time,
        payload.experiences,
        payload.products,
        payload.resume
      );
      
      Alert.alert(
        'Sucesso', 
        'Cadastro realizado com sucesso! Faça login para continuar.',
        [{ text: 'OK', onPress: () => router.replace('/(auth)/login') }]
      );
    } catch (error: any) {
      console.error('Final registration error:', error);
      Alert.alert("Erro no Cadastro", error.message || "Não foi possível completar o cadastro.");
    } finally {
      setIsLoading(false);
    }
  };
  
  const handleBack = () => {
    router.back();
  };

  return {
    isLoading,
    showAiDescriptionModal,
    setShowAiDescriptionModal,
    formData: registrationData,
    handleResumeChange,
    handleRequestAiResume,
    handleFinish,
    handleBack,
  };
};