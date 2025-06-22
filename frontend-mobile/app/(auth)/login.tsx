import React from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  SafeAreaView,
  StatusBar,
  Image
} from 'react-native';
import { styles } from '../../styles/register/styles/LoginStyle';
import { Ionicons } from '@expo/vector-icons';
import { ErrorModal } from '../../components/modals/ErrorModal/ErrorModal';
import { useLogin } from '@/hooks/authHooks/useLogin'; 

const LoginScreen = () => {
  const {
    formData,
    handleInputChange,
    handleGoRegister,
    errors,
    errorModal,
    handleLogin,
    closeErrorModal,
    passwordVisibility,
  } = useLogin();


  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" />
      <View style={styles.logoContainer}>
        <Image source={require('../../assets/images/HairmatchLogo.png')}></Image>
      </View>

      <View style={styles.formContainer}>
        <View style={styles.inputContainer}>
          <Text style={styles.inputLabel}>Insira seu email</Text>
          <TextInput
            style={[styles.input, errors.email && styles.inputError]}
            placeholder="email@domain.com"
            value={formData.email} 
            onChangeText={text => handleInputChange('email', text)}
            keyboardType="email-address"
            autoCapitalize="none"
          />
          {errors.email && <Text style={styles.errorText}>Por favor, insira um email válido.</Text>}
        </View>

        <Text style={styles.inputLabel}>Insira sua senha</Text>
        <View style={[styles.passwordContainer, errors.password && styles.inputError]}> 
          <TextInput
            style={styles.inputInner} 
            placeholder="****"
            value={formData.password}
            onChangeText={text => handleInputChange('password', text)}
            secureTextEntry={!passwordVisibility.showPassword}
          />
          <TouchableOpacity onPress={passwordVisibility.toggle} style={styles.eyeIconAbsolute}>
            <Ionicons
              name={passwordVisibility.showPassword ? 'eye' : 'eye-off'}
              size={24}
              color="#888"
            />
          </TouchableOpacity>
        </View>
        {errors.password && <Text style={styles.errorText}>Por favor, insira sua senha.</Text>}

        <TouchableOpacity style={styles.loginButton} onPress={handleLogin}>
          <Text style={styles.loginButtonText}>Entrar</Text>
        </TouchableOpacity>

        <TouchableOpacity onPress={handleGoRegister}>
          <View style={styles.signupContainer}>
            <Text style={styles.signupText}>Não possui uma conta? </Text>
            <Text style={styles.signupLink}>Cadastre-se</Text>
          </View>
        </TouchableOpacity>
      </View>

      <ErrorModal
        visible={errorModal.visible}
        onClose={closeErrorModal}
        message={errorModal.message}
      />
    </SafeAreaView>
  );
};

export default LoginScreen;