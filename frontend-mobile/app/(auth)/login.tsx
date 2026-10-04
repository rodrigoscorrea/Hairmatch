import React from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StatusBar,
  Image,
  StyleSheet
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { styles } from '../../styles/register/styles/LoginStyle';
import { Ionicons } from '@expo/vector-icons';
import { ErrorModal } from '../../components/modals/ErrorModal/ErrorModal';
import { useLogin } from '@/hooks/authHooks/useLogin';
import { useGoogleAuth } from '@/hooks/authHooks/useGoogleAuth';
import { GoogleSignInButton } from '@/components/GoogleSignInButton';

const LoginScreen = () => {
  const {
    formData,
    handleInputChange,
    handleGoRegister,
    errors,
    errorModal,
    notice,
    handleLogin,
    closeErrorModal,
    passwordVisibility,
  } = useLogin();
  const { handleGoogle, isGoogleLoading, ready, googleError, closeGoogleError } = useGoogleAuth();

  const closeModals = () => {
    closeErrorModal();
    closeGoogleError();
  };


  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" />
      <View style={styles.logoContainer}>
        <Image source={require('../../assets/images/HairmatchLogo.png')}></Image>
      </View>

      <View style={styles.formContainer}>
        {notice !== '' && <Text style={googleStyles.notice}>{notice}</Text>}
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

        <View style={googleStyles.divider}>
          <View style={googleStyles.dividerLine} />
          <Text style={googleStyles.dividerText}>ou</Text>
          <View style={googleStyles.dividerLine} />
        </View>

        <GoogleSignInButton
          label="Entrar com Google"
          onPress={handleGoogle}
          disabled={!ready}
          loading={isGoogleLoading}
        />

        <TouchableOpacity onPress={handleGoRegister}>
          <View style={styles.signupContainer}>
            <Text style={styles.signupText}>Não possui uma conta? </Text>
            <Text style={styles.signupLink}>Cadastre-se</Text>
          </View>
        </TouchableOpacity>
      </View>

      <ErrorModal
        visible={errorModal.visible || googleError.visible}
        onClose={closeModals}
        message={googleError.visible ? googleError.message : errorModal.message}
      />
    </SafeAreaView>
  );
};

const googleStyles = StyleSheet.create({
  notice: {
    color: '#2E7D32',
    fontSize: 14,
    textAlign: 'center',
    marginBottom: 16,
  },
  divider: {
    flexDirection: 'row',
    alignItems: 'center',
    marginVertical: 15,
  },
  dividerLine: {
    flex: 1,
    height: 1,
    backgroundColor: '#828282',
  },
  dividerText: {
    marginHorizontal: 10,
    color: '#828282',
    fontSize: 14,
  },
});

export default LoginScreen;