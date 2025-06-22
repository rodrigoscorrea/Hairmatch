import { useState } from 'react';
import { useRouter } from 'expo-router';
import { useRegistration } from '@/contexts/RegistrationContext';
import { UserRole } from '@/app/../models/User.types';
import { ERROR_MESSAGES } from '@/app/../constants/errorMessages';
import { stripNonDigits, isValidEmail, validatePassword } from '@/app/../utils/forms';

export const useRegisterForm = () => {
  const router = useRouter();
  const { registrationData, setRegistrationData } = useRegistration();
  
  const [role, setRole] = useState<UserRole>(UserRole.CUSTOMER);
  const [errors, setErrors] = useState<{ [key: string]: boolean }>({});
  const [errorModal, setErrorModal] = useState({ visible: false, message: '' });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const handleInputChange = (field: keyof typeof registrationData, value: string) => {
    setRegistrationData(prev => ({ ...prev, [field]: value }))
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: false }));
    }
  };

  const handleGoBack = () => {
    router.back();
  };

  const validateFields = () => {
    const newErrors: { [key: string]: boolean } = {};
    let errorList: string[] = [];
    
    if (!registrationData.first_name) { newErrors.first_name = true; errorList.push(ERROR_MESSAGES.first_name_required); }
    if (!registrationData.last_name) { newErrors.last_name = true; errorList.push(ERROR_MESSAGES.last_name_required); }
    if (!registrationData.password) { newErrors.password = true; errorList.push(ERROR_MESSAGES.password_required); }
    if (role === UserRole.CUSTOMER) {
        if(!registrationData.cpf) {
            newErrors.cpf = true;
            errorList.push(ERROR_MESSAGES.cpf_required);
        }
        else{
            const sanitizedCpf = stripNonDigits(registrationData.cpf);
            if (sanitizedCpf.length !== 11) {
                newErrors.cpf = true;
                errorList.push(ERROR_MESSAGES.cpf_invalid);
            }
        }
    }
    else{
        if(!registrationData.cnpj) {
            newErrors.cnpj = true;
            errorList.push(ERROR_MESSAGES.cnpj_required);
        }
        else{
            const sanitizedCnpj = stripNonDigits(registrationData.cnpj);
            if (sanitizedCnpj.length !== 14) {
                newErrors.cnpj = true;
                errorList.push(ERROR_MESSAGES.cnpj_invalid);
            }
        }
    }
    if (!registrationData.email) { newErrors.email = true; errorList.push(ERROR_MESSAGES.email_required); }
    else if (!isValidEmail(registrationData.email)) {
      newErrors.email = true;
      errorList.push(ERROR_MESSAGES.email_invalid);
    }
    if (!registrationData.phone) { newErrors.phone = true; errorList.push(ERROR_MESSAGES.phone_required); }
    else {
      const sanitizedPhone = stripNonDigits(registrationData.phone);
      if (sanitizedPhone.length < 10 || sanitizedPhone.length > 11) {
        newErrors.phone = true;
        errorList.push(ERROR_MESSAGES.phone_invalid);
      }
    }
    if (!registrationData.password) { newErrors.password = true; errorList.push(ERROR_MESSAGES.password_required); }
    else if (!validatePassword(registrationData.password)) {
      newErrors.password = true;
      errorList.push(ERROR_MESSAGES.password_invalid);
    }
    if (!registrationData.confirmPassword) {
      newErrors.confirmPassword = true;
      errorList.push(ERROR_MESSAGES.confirm_password_required);
    } else if (registrationData.confirmPassword !== registrationData.password) {
      newErrors.confirmPassword = true;
      newErrors.password = true; // Optionally mark password as well
      errorList.push(ERROR_MESSAGES.passwords_not_match);
    }

    setErrors(newErrors);
    if (errorList.length > 0) {
      setErrorModal({ visible: true, message: errorList[0] });
      return false;
    }
    return true;
  };

  const handleRegister = async () => {
    if (!validateFields()) return;

    setRegistrationData(prev => ({ ...prev, role: role }));
    
    router.push('/(auth)/register/address');
  };

  return {
    formData: registrationData, 
    handleInputChange,
    handleGoBack,
    role,
    setRole,
    errors,
    handleRegister,
    errorModal,
    closeErrorModal: () => setErrorModal({ ...errorModal, visible: false }),
    passwordVisibility: {
        showPassword,
        toggle: () => setShowPassword(p => !p)
    },
    confirmPasswordVisibility: {
        showConfirmPassword,
        toggle: () => setShowConfirmPassword(p => !p)
    }
  };
};