import React, { useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StatusBar,
  Image,
  StyleSheet,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { colors } from '@/assets/colors';
import { styles } from '../../styles/register/styles/LoginStyle';
import { ErrorModal } from '../../components/modals/ErrorModal/ErrorModal';
import { CONFIRMATION_CODE_LENGTH, useConfirmEmail } from '@/hooks/authHooks/useConfirmEmail';

const ConfirmEmailScreen = () => {
  const router = useRouter();
  const {
    email,
    hasPendingConfirmation,
    isConfirmed,
    code,
    handleCodeChange,
    canSubmit,
    canResend,
    isSubmitting,
    isResending,
    cooldown,
    notice,
    submit,
    resend,
    errorModal,
    closeErrorModal,
  } = useConfirmEmail();

  // Without an account waiting for its code (the app was reloaded, or the screen was opened by hand) there is nothing to confirm.
  useEffect(() => {
    if (!hasPendingConfirmation && !isConfirmed) {
      router.replace('/(auth)/login');
    }
  }, [hasPendingConfirmation, isConfirmed]);

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" />
      <View style={styles.logoContainer}>
        <Image source={require('../../assets/images/HairmatchLogo.png')}></Image>
      </View>

      <View style={styles.formContainer}>
        <Text style={confirmStyles.title}>Confirme seu e-mail</Text>
        <Text style={confirmStyles.description}>Enviamos um código para {email}</Text>

        <Text style={styles.inputLabel}>Código de 6 dígitos</Text>
        <TextInput
          style={[styles.input, confirmStyles.codeInput]}
          placeholder="000000"
          value={code}
          onChangeText={handleCodeChange}
          keyboardType="number-pad"
          textContentType="oneTimeCode"
          autoComplete="one-time-code"
          maxLength={CONFIRMATION_CODE_LENGTH}
          editable={!isSubmitting}
        />

        <TouchableOpacity
          style={[styles.loginButton, !canSubmit && confirmStyles.disabledButton]}
          onPress={submit}
          disabled={!canSubmit}
        >
          <Text style={styles.loginButtonText}>{isSubmitting ? 'Confirmando...' : 'Confirmar'}</Text>
        </TouchableOpacity>

        <TouchableOpacity style={confirmStyles.resendButton} onPress={resend} disabled={!canResend}>
          <Text style={[confirmStyles.resendText, !canResend && confirmStyles.resendTextDisabled]}>
            {cooldown > 0 ? `Reenviar código (${cooldown}s)` : isResending ? 'Reenviando...' : 'Reenviar código'}
          </Text>
        </TouchableOpacity>
        {notice !== '' && <Text style={confirmStyles.notice}>{notice}</Text>}

        <TouchableOpacity onPress={() => router.replace('/(auth)/login')}>
          <View style={styles.signupContainer}>
            <Text style={styles.signupLink}>Voltar para o login</Text>
          </View>
        </TouchableOpacity>
      </View>

      <ErrorModal visible={errorModal.visible} onClose={closeErrorModal} message={errorModal.message} />
    </SafeAreaView>
  );
};

const confirmStyles = StyleSheet.create({
  title: {
    fontSize: 22,
    fontWeight: 'bold',
    color: colors.textPrimary,
    textAlign: 'center',
    marginBottom: 8,
  },
  description: {
    fontSize: 14,
    color: colors.textSecondary,
    textAlign: 'center',
    marginBottom: 24,
  },
  codeInput: {
    textAlign: 'center',
    fontSize: 24,
    letterSpacing: 8,
  },
  disabledButton: {
    opacity: 0.5,
  },
  resendButton: {
    alignSelf: 'center',
    marginTop: 20,
    padding: 8,
  },
  resendText: {
    color: colors.primary,
    fontSize: 15,
    fontWeight: 'bold',
    textDecorationLine: 'underline',
  },
  resendTextDisabled: {
    color: colors.textPlaceholder,
    textDecorationLine: 'none',
  },
  notice: {
    color: colors.textSecondary,
    fontSize: 13,
    textAlign: 'center',
    marginTop: 4,
  },
});

export default ConfirmEmailScreen;
