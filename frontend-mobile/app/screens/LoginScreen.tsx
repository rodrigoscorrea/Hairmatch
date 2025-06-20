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
import { styles } from './styles/LoginStyle';
import { Ionicons } from '@expo/vector-icons';
import { ErrorModal } from '../components/modals/ErrorModal/ErrorModal';
import { useLogin } from '@/app/hooks/useLogin'; 

const LoginScreen = () => {
  // 2. Usa o hook e desestrutura todos os estados e funções necessários
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
        {/* Campo de Email - Atualizado para usar o hook */}
        <View style={styles.inputContainer}>
          <Text style={styles.inputLabel}>Insira seu email</Text>
          <TextInput
            style={[styles.input, errors.email && styles.inputError]}
            placeholder="email@domain.com"
            value={formData.email} // Usa o formData do hook
            onChangeText={text => handleInputChange('email', text)} // Usa o handler genérico
            keyboardType="email-address"
            autoCapitalize="none"
          />
          {errors.email && <Text style={styles.errorText}>Por favor, insira um email válido.</Text>}
        </View>

        {/* Campo de senha - Atualizado para usar o hook */}
        <Text style={styles.inputLabel}>Insira sua senha</Text>
        <View style={[styles.passwordContainer, errors.password && styles.inputError]}> 
          <TextInput
            style={styles.inputInner} 
            placeholder="****"
            value={formData.password} // Usa o formData do hook
            onChangeText={text => handleInputChange('password', text)} // Usa o handler genérico
            secureTextEntry={!passwordVisibility.showPassword} // Usa a visibilidade do hook
          />
          <TouchableOpacity onPress={passwordVisibility.toggle} style={styles.eyeIconAbsolute}>
            <Ionicons
              name={passwordVisibility.showPassword ? 'eye' : 'eye-off'} // Usa a visibilidade do hook
              size={24}
              color="#888"
            />
          </TouchableOpacity>
        </View>
        {errors.password && <Text style={styles.errorText}>Por favor, insira sua senha.</Text>}

        {/* Botão de Login - Atualizado para usar o hook */}
        <TouchableOpacity style={styles.loginButton} onPress={handleLogin}>
          <Text style={styles.loginButtonText}>Entrar</Text>
        </TouchableOpacity>

        {/* Botão de Cadastro - Atualizado para usar o hook */}
        <TouchableOpacity onPress={handleGoRegister}>
          <View style={styles.signupContainer}>
            <Text style={styles.signupText}>Não possui uma conta? </Text>
            <Text style={styles.signupLink}>Cadastre-se</Text>
          </View>
        </TouchableOpacity>
      </View>

      {/* Modal de erro - Atualizado para usar o hook */}
      <ErrorModal
        visible={errorModal.visible}
        onClose={closeErrorModal}
        message={errorModal.message}
      />
    </SafeAreaView>
  );
};

export default LoginScreen;