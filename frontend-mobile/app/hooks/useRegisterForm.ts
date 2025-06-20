import { useState } from 'react';
import { useNavigation } from '@react-navigation/native';
import { UserRole } from '@/app/models/User.types';
import { ERROR_MESSAGES } from '@/app/constants/errorMessages';
import { stripNonDigits, isValidEmail, validatePassword } from '@/app/utils/forms';

export const useRegisterForm = () => {
  const navigation = useNavigation<any>();

  // formData is the object that holds all the form fields states
  // this is better than having usesState for each field separately
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    cpf: '',
    cnpj: '',
    email: '',
    phone: '',
    password: '',
    confirmPassword: '',
  });
  
  const [role, setRole] = useState<UserRole>(UserRole.CUSTOMER);
  const [errors, setErrors] = useState<{ [key: string]: boolean }>({});
  const [errorModal, setErrorModal] = useState({ visible: false, message: '' });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const handleInputChange = (field: keyof typeof formData, value: string) => {
    //this is a generic handler for all input changes
    setFormData(prev => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: false }));
    }
  };

   const handleGoBack = () => {
    navigation.goBack();
  };

  const validateFields = () => {
    // the logic for validation is now centralized in this function
    // It now uses the `formData` state.
    const newErrors: { [key: string]: boolean } = {};
    let errorList: string[] = [];
    
    if (!formData.first_name) { newErrors.first_name = true; errorList.push(ERROR_MESSAGES.first_name_required); }
    if (!formData.last_name) { newErrors.last_name = true; errorList.push(ERROR_MESSAGES.last_name_required); }
    if (!formData.password) { newErrors.password = true; errorList.push(ERROR_MESSAGES.password_required); }
    if (role === UserRole.CUSTOMER) {
        if(!formData.cpf) {
            newErrors.cpf = true;
            errorList.push(ERROR_MESSAGES.cpf_required);
        }
        else{
            const sanitizedCpf = stripNonDigits(formData.cpf);
            if (sanitizedCpf.length !== 11) {
                newErrors.cpf = true;
                errorList.push(ERROR_MESSAGES.cpf_invalid);
            }
        }
    }
    else{
        if(!formData.cnpj) {
            newErrors.cnpj = true;
            errorList.push(ERROR_MESSAGES.cnpj_required);
        }
        else{
            const sanitizedCnpj = stripNonDigits(formData.cnpj);
            if (sanitizedCnpj.length !== 14) {
                newErrors.cnpj = true;
                errorList.push(ERROR_MESSAGES.cnpj_invalid);
            }
        }
    }
    if (!formData.email) { newErrors.email = true; errorList.push(ERROR_MESSAGES.email_required); }
    else if (!isValidEmail(formData.email)) {
      newErrors.email = true;
      errorList.push(ERROR_MESSAGES.email_invalid);
    }
    if (!formData.phone) { newErrors.phone = true; errorList.push(ERROR_MESSAGES.phone_required); }
    else {
      const sanitizedPhone = stripNonDigits(formData.phone);
      if (sanitizedPhone.length < 10 || sanitizedPhone.length > 11) {
        newErrors.phone = true;
        errorList.push(ERROR_MESSAGES.phone_invalid);
      }
    }
    if (!formData.password) { newErrors.password = true; errorList.push(ERROR_MESSAGES.password_required); }
    else if (!validatePassword(formData.password)) {
      newErrors.password = true;
      errorList.push(ERROR_MESSAGES.password_invalid);
    }
    if (!formData.confirmPassword) {
      newErrors.confirmPassword = true;
      errorList.push(ERROR_MESSAGES.confirm_password_required);
    } else if (formData.confirmPassword !== formData.password) {
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

    const { first_name, last_name, email, password, cpf, cnpj, phone } = formData;
    
    navigation?.navigate('Address', {
      personalData: {
        first_name,
        last_name,
        phone: stripNonDigits(phone),
        email,
        cnpj: role === UserRole.HAIRDRESSER ? stripNonDigits(cnpj) : '',
        cpf: role === UserRole.CUSTOMER ? stripNonDigits(cpf) : '',
        password,
        role,
      },
    });
  };

  return {
    formData,
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