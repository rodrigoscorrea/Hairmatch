// hooks/useLogin.ts

import { useState } from 'react'; 
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useAuth } from '@/app/_layout';
import { ERROR_MESSAGES } from '@/constants/errorMessages';
import { useRegistration } from '@/contexts/RegistrationContext';
import { EMAIL_CONFIRMED_PARAM } from '@/hooks/authHooks/useConfirmEmail';

export const useLogin = () => {
    const router = useRouter();
    const { signIn } = useAuth();
    const { resetRegistration, setPendingConfirmation } = useRegistration();
    const params = useLocalSearchParams();
    const notice = params[EMAIL_CONFIRMED_PARAM] === '1' ? 'E-mail confirmado. Entre com sua senha.' : '';

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
        // New sign-up via the link: discards Google mode and data from a previous attempt (GAUTH-30).
        resetRegistration();
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
            if (result.slug === 'email-not-confirmed') {
                // Right password, e-mail not confirmed yet: the confirmation screen takes over, without an error modal.
                // The password stays in memory only, to sign in once the code is accepted.
                setPendingConfirmation({ email: formData.email, password: formData.password });
                router.push('/(auth)/confirm-email');
                return;
            }
            setErrorModal({ visible: true, message: result.error || 'Ocorreu um erro desconhecido.' });
        }
    };

    return {
        formData,
        handleInputChange,
        handleGoRegister,
        errors,
        errorModal,
        notice,
        handleLogin,
        closeErrorModal: () => setErrorModal({ ...errorModal, visible: false }),
        passwordVisibility: {
            showPassword,
            toggle: () => setShowPassword(p => !p)
        },
    };
}