import { useContext, useState } from 'react';
import { useNavigation } from '@react-navigation/native';
import { ERROR_MESSAGES } from '@/app/constants/errorMessages';
import { AuthContext } from '../index';

export const useLogin = () => {


	const navigation = useNavigation<any>();
	const [formData, setFormData] = useState({
			email: '',
			password: '',
	});
	const [errors, setErrors] = useState<{ [key: string]: boolean }>({});
	const [errorModal, setErrorModal] = useState({ visible: false, message: '' });
	const [showPassword, setShowPassword] = useState(false);
	const { signIn } = useContext<any>(AuthContext);

	const handleInputChange = (field: keyof typeof formData, value: string) => {
		//this is a generic handler for all input changes
		setFormData(prev => ({ ...prev, [field]: value }));
		if (errors[field]) {
			setErrors(prev => ({ ...prev, [field]: false }));
		}
  };

	const handleGoRegister = () => {
    navigation.navigate('Register');
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