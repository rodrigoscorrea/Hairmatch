import React, { useState, useContext } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  SafeAreaView,
  StatusBar,
  Modal,
  Image
} from 'react-native';

import { useNavigation } from '@react-navigation/native';
import { AuthContext } from '../index';
import { StackNavigationProp } from '@react-navigation/stack';
import { RootStackParamList } from '../models/RootStackParams.types';
import { ErrorModal } from '@/app/components/ErrorModal';

type LoginScreenNavigationProp = StackNavigationProp<RootStackParamList>;

const LoginScreen = () => {
  const navigation = useNavigation<LoginScreenNavigationProp>();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [errors, setErrors] = useState<{ [key: string]: boolean }>({});
  const [errorModalVisible, setErrorModalVisible] = useState(false);
  const [errorModalMessage, setErrorModalMessage] = useState('');

  const { signIn } = useContext<any>(AuthContext);

  const validateFields = () => {
    const newErrors: { [key: string]: boolean } = {};
    if (!email) newErrors.email = true;
    if (!password) newErrors.password = true;

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleLogin = async () => {
    if (!validateFields()) {
      setErrorModalMessage('Por favor, corrija os campos destacados.');
      setErrorModalVisible(true);
      return;
    }
    else{
      try {
        await signIn(email, password);
        navigation.navigate('Home')
      } catch (error: any) {
        const errorMessage = error.response?.data?.error || 'Login failed. Please try again.';
      }
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" backgroundColor="#FFF8F0" />
      <View style={styles.logoContainer}>
        <Image source={require('../../assets/images/HairmatchLogo.png')} />
      </View>

      <View style={styles.formContainer}>
        <Text style={styles.inputLabel}>Insira seu email</Text>
        <TextInput
          style={[
            styles.input,
            errors.email && { borderColor: 'purple', borderWidth: 2 }
          ]}
          placeholder="email@domain.com"
          value={email}
          onChangeText={setEmail}
          keyboardType="email-address"
          autoCapitalize="none"
        />
        {errors.email && <Text style={styles.errorText}>Email é obrigatório</Text>}

        <Text style={styles.inputLabel}>Insira sua senha</Text>
        <TextInput
          style={[
            styles.input,
            errors.password && { borderColor: 'purple', borderWidth: 2 }
          ]}
          placeholder="******"
          value={password}
          onChangeText={setPassword}
          secureTextEntry
        />
        {errors.password && <Text style={styles.errorText}>Senha é obrigatória</Text>}

        <TouchableOpacity style={styles.loginButton} onPress={handleLogin}>
          <Text style={styles.loginButtonText}>Entrar</Text>
        </TouchableOpacity>

        <View style={styles.signupContainer}>
          <Text style={styles.signupText}>Não possui uma conta? </Text>
          <TouchableOpacity onPress={() => navigation?.navigate('Register')}>
            <Text style={styles.signupLink}>Cadastre-se</Text>
          </TouchableOpacity>
        </View>
      </View>

      <ErrorModal
        visible={errorModalVisible}
        onClose={() => setErrorModalVisible(false)}
        message={errorModalMessage}
      />
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FFF8F0',
    padding: 20,
    alignItems: 'center',
  },
  logoContainer: {
    alignItems: 'center',
    marginTop: 60,
    marginBottom: 40,
  },
  logoText: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#FF7A00',
  },
  logoHighlight: {
    color: '#FF7A00',
  },
  scissorsText: {
    fontSize: 24,
  },
  formContainer: {
    width: '80%',
    maxWidth: 350,
  },
  inputLabel: {
    fontSize: 14,
    color: '#333',
    marginBottom: 5,
  },
  input: {
    backgroundColor: '#FFFFFF',
    borderRadius: 8,
    padding: 12,
    marginBottom: 10,
    borderWidth: 0.2,
    borderColor: '#828282',
    fontSize: 16,
  },
  errorText: {
    color: 'purple',
    fontSize: 12,
    marginBottom: 10,
    marginLeft: 4,
  },
  loginButton: {
    backgroundColor: '#FF7A00',
    borderRadius: 8,
    padding: 15,
    alignItems: 'center',
    marginTop: 10,
    width: '70%',
    alignSelf: 'center',
  },
  loginButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: 'bold',
  },
  signupContainer: {
    flexDirection: 'row',
    justifyContent: 'center',
    marginTop: 20,
  },
  signupText: {
    color: '#333',
    fontSize: 14,
  },
  signupLink: {
    color: '#FF7A00',
    fontSize: 14,
    fontWeight: 'bold',
    textDecorationLine: 'underline',
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'flex-end',
    alignItems: 'center',
  },
  modalContent: {
    backgroundColor: '#FFF',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    padding: 25,
    width: '100%',
    alignItems: 'center',
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 12,
    color: '#333',
    textDecorationLine: 'underline',
  },
  modalText: {
    fontSize: 14,
    color: '#333',
    marginBottom: 20,
    textAlign: 'center',
  },
  modalButton: {
    backgroundColor: '#FF7A00',
    paddingVertical: 12,
    paddingHorizontal: 30,
    borderRadius: 8,
  },
  modalButtonText: {
    color: '#FFF',
    fontWeight: 'bold',
    fontSize: 16,
  },
});

export default LoginScreen;
