// hooks/useLogin.ts

import { useState } from 'react'; 
import { useRouter } from 'expo-router';
import { useAuth } from '@/app/_layout';
import { ERROR_MESSAGES } from '@/constants/errorMessages';

export const useLogin = () => {
    const router = useRouter();
    const { signIn } = useAuth();

    const [formData, setFormData] = useState({
        email: '',
        password: '',
    });
    const [errors, setErrors] = useState<{ [key: string]: boolean }>({});
    const [errorModal, setErrorModal] = useState({ visible: false, message: '' });
    const [showPassword, setShowPassword] = useState(false);
    
    const handleInputChange = (field: keyof typeof formData, value: string) => {
        setFormData(prev => ({ ...prev, [field]: value }));
        if (errors[field]) {
            setErrors(prev => ({ ...prev, [field]: false }));
        }
    };

    const handleGoRegister = () => {
        router.push('/(auth)/register');
    };

    const validateFields = () => {
        const newErrors: { [key: string]: boolean } = {};
        let errorList: string[] = [];
        if (!formData.email) {
            newErrors.email = true;
            errorList.push(ERROR_MESSAGES.email_required);
        }
        if (!formData.password) {
            newErrors.password = true;
            errorList.push(ERROR_MESSAGES.password_required);
        }
        setErrors(newErrors);
        if (errorList.length > 0) {
            setErrorModal({ visible: true, message: errorList[0] });
            return false;
        }
        return true;
    }

    const handleLogin = async () => { 
        if (!validateFields()) {
            return;
        }

        const result = await signIn(formData.email, formData.password);

        if (!result.success) {
            setErrorModal({ visible: true, message: result.error || 'An unknown error occurred.' });
        }
    };

    return {
        formData,
        handleInputChange,
        handleGoRegister,
        errors,
        errorModal,
        handleLogin,
        closeErrorModal: () => setErrorModal({ ...errorModal, visible: false }),
        passwordVisibility: {
            showPassword,
            toggle: () => setShowPassword(p => !p)
        },
    };
}