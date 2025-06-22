import { useRouter } from 'expo-router';
import { useRegistration } from '@/contexts/RegistrationContext';

export const useProfessionalStoryForm = () => {
  const router = useRouter();
  const { registrationData, setRegistrationData } = useRegistration();

  const handleInputChange = (field: keyof typeof registrationData, value: string) => {
    setRegistrationData(prev => ({ ...prev, [field]: value }));
  };

  const handleNext = () => {
    router.push('/(auth)/register/description');
  };

  const handleBack = () => {
    router.back();
  };

  return {
    formData: registrationData,
    handleInputChange,
    handleNext,
    handleBack,
  };
};