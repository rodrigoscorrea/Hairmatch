import React, { useState, useContext } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  SafeAreaView,
  StatusBar,
  Modal,
  Alert,
  Image
} from 'react-native';
import { styles } from './styles/LoginStyle';
import { useNavigation } from '@react-navigation/native';
import { AuthContext } from '../index';
import { StackNavigationProp } from '@react-navigation/stack';
import { RootStackParamList } from '../models/RootStackParams.types';

type LoginScreenNavigationProp = StackNavigationProp<RootStackParamList>;

const LoginScreen = () => {
  const navigation = useNavigation<LoginScreenNavigationProp>();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [errorModalVisible, setErrorModalVisible] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const { signIn } = useContext<any>(AuthContext);

  const handleLogin = async () => {
    if (!email || !password) {
      Alert.alert('Error', 'Please enter both email and password');
      return;
    }

    setIsLoading(true);
    try {
      await signIn(email, password);
    } catch (error: any) {
      const errorMessage = error.response?.data?.error || 'Login failed. Please try again.';
      //Alert.alert('Error', errorMessage);
      setErrorModalVisible(true)
    } finally {
      setIsLoading(false);
    }
  };

  const closeErrorModal = () => {
    setErrorModalVisible(false);
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" />
      <View style={styles.logoContainer}>
        <Image source={require('../../assets/images/HairmatchLogo.png')}></Image>
      </View>

      <View style={styles.formContainer}>
        <Text style={styles.inputLabel}>Insira seu email</Text>
        <TextInput
          style={styles.input}
          placeholder="email@domain.com"
          value={email}
          onChangeText={setEmail}
          keyboardType="email-address"
          autoCapitalize="none"
        />

        <Text style={styles.inputLabel}>Insira sua senha</Text>
        <TextInput
          style={styles.input}
          placeholder="****"
          value={password}
          onChangeText={setPassword}
          secureTextEntry
        />

        <TouchableOpacity style={styles.loginButton} onPress={handleLogin}>
          <Text style={styles.loginButtonText}>Entrar</Text>
        </TouchableOpacity>

        <TouchableOpacity onPress={() => navigation?.navigate('Register')}>
          <View style={styles.signupContainer}>
            <Text style={styles.signupText}>Não possui uma conta? </Text>
            <Text style={styles.signupLink}>Cadastre-se</Text>
          </View>
          </TouchableOpacity>
        </View>

      {/* Modal de erro de login */}
      <Modal
        animationType="fade"
        transparent={true}
        visible={errorModalVisible}
        onRequestClose={closeErrorModal}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Login Incorreto</Text>
            <Text style={styles.modalText}>
              Opa! Parece que o usuário ou a senha estão errados. Confere aí e tenta de novo!
            </Text>
            <TouchableOpacity
              style={styles.modalButton}
              onPress={closeErrorModal}
            >
              <Text style={styles.modalButtonText}>Voltar</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
};

export default LoginScreen;
