// hooks/authHooks/useConfirmEmail.ts
import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'expo-router';
import { useAuth } from '@/app/_layout';
import { useRegistration } from '@/contexts/RegistrationContext';
import { confirmEmail, resendConfirmationCode } from '@/services/email-confirmation.service';
import { problemMessage } from '@/utils/api-problem';

export const CONFIRMATION_CODE_LENGTH = 6;
export const RESEND_COOLDOWN_SECONDS = 60;
export const RESEND_NOTICE = 'Se a conta estiver pendente, enviamos um novo código.';
// Route param the login screen reads to show that the e-mail was confirmed. It carries no data.
export const EMAIL_CONFIRMED_PARAM = 'confirmed';

export const useConfirmEmail = () => {
  const router = useRouter();
  const { signIn } = useAuth();
  const { pendingConfirmation, clearPendingConfirmation } = useRegistration();

  const [code, setCode] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isResending, setIsResending] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const [notice, setNotice] = useState('');
  // True once the code was accepted: the screen must not send the user back to the login while it signs in.
  const [isConfirmed, setIsConfirmed] = useState(false);
  const [errorModal, setErrorModal] = useState({ visible: false, message: '' });

  const email = pendingConfirmation?.email ?? '';
  const isCoolingDown = cooldown > 0;
  const canSubmit = code.length === CONFIRMATION_CODE_LENGTH && !!email && !isSubmitting && !isConfirmed;
  const canResend = !!email && !isCoolingDown && !isResending && !isSubmitting && !isConfirmed;

  // The timer is cleared when the countdown ends and when the screen goes away.
  useEffect(() => {
    if (!isCoolingDown) return;
    const timer = setInterval(() => setCooldown((seconds) => Math.max(seconds - 1, 0)), 1000);
    return () => clearInterval(timer);
  }, [isCoolingDown]);

  // The screen can unmount (the root layout leads to the home) while signIn is still resolving.
  const mounted = useRef(true);
  useEffect(() => () => { mounted.current = false; }, []);

  const handleCodeChange = (text: string) => {
    setCode(text.replace(/\D/g, '').slice(0, CONFIRMATION_CODE_LENGTH));
  };

  const goToLoginConfirmed = () => {
    router.replace({ pathname: '/(auth)/login', params: { [EMAIL_CONFIRMED_PARAM]: '1' } });
  };

  const submit = async () => {
    if (!canSubmit) return;
    setIsSubmitting(true);
    try {
      await confirmEmail(email, code);
    } catch (error) {
      if (mounted.current) {
        setErrorModal({
          visible: true,
          message: problemMessage(error, 'Não foi possível confirmar o e-mail. Tente novamente.'),
        });
        setIsSubmitting(false);
      }
      return;
    }

    setIsConfirmed(true);
    const password = pendingConfirmation?.password;
    // The password is gone from memory whatever happens next.
    clearPendingConfirmation();
    if (!password) {
      goToLoginConfirmed();
      return;
    }
    const result = await signIn(email, password);
    // On success the root layout leads to the home of the role; otherwise the user types the password.
    if (!result.success && mounted.current) {
      goToLoginConfirmed();
    }
  };

  const resend = async () => {
    if (!canResend) return;
    setIsResending(true);
    try {
      await resendConfirmationCode(email);
      setNotice(RESEND_NOTICE);
      setCooldown(RESEND_COOLDOWN_SECONDS);
    } catch (error) {
      setErrorModal({
        visible: true,
        message: problemMessage(error, 'Não foi possível reenviar o código. Tente novamente.'),
      });
    } finally {
      setIsResending(false);
    }
  };

  return {
    email,
    hasPendingConfirmation: !!pendingConfirmation,
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
    closeErrorModal: () => setErrorModal({ ...errorModal, visible: false }),
  };
};
