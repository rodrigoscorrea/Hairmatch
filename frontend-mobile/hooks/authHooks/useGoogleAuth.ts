import { useRef, useState } from 'react';
import axios from 'axios';
import { usePathname, useRouter } from 'expo-router';
import { useAuth } from '@/app/_layout';
import { INITIAL_REGISTRATION_DATA, useRegistration } from '@/contexts/RegistrationContext';
import { loginWithGoogle } from '@/services/google-auth.service';
import { useGoogleIdToken } from './useGoogleIdToken';

const GOOGLE_DEFAULT_ERROR = 'Não foi possível entrar com o Google. Tente novamente.';

// SPEC_DEVIATION: o design só prevê `error.response.data.error` ou o texto padrão.
// Reason: erros que não vêm do axios (ex.: "Login com Google indisponível no Expo Go...", exigido em T14)
// precisam mostrar a própria mensagem. Erros do axios sem `error` (ex.: backend fora do ar) usam o texto padrão (GAUTH-09).
const getGoogleErrorMessage = (error: any): string => {
  if (axios.isAxiosError(error)) {
    return (error.response?.data as any)?.error || GOOGLE_DEFAULT_ERROR;
  }
  return error?.message || GOOGLE_DEFAULT_ERROR;
};

export const useGoogleAuth = () => {
  const router = useRouter();
  const pathname = usePathname();
  const { loadSession } = useAuth();
  const { setRegistrationData } = useRegistration();
  const { ready, getIdToken } = useGoogleIdToken();

  const [isGoogleLoading, setIsGoogleLoading] = useState(false);
  const [googleError, setGoogleError] = useState({ visible: false, message: '' });
  // Evita dois fluxos com toques no mesmo frame, antes de o botão re-renderizar desabilitado (GAUTH-10).
  const inFlight = useRef(false);

  const handleGoogle = async () => {
    if (inFlight.current) return;
    inFlight.current = true;
    setIsGoogleLoading(true);

    try {
      // Primeiro await do fluxo: no web, o popup precisa abrir no mesmo tick do toque, senão o navegador o bloqueia.
      const idToken = await getIdToken();
      if (!idToken) return; // Cancelamento: fica na tela, sem modal (GAUTH-08).

      const response = await loginWithGoogle(idToken);

      if (response.status === 'authenticated') {
        // O RootLayoutNav leva à home do papel depois que a sessão carrega (GAUTH-07, 29).
        const session = await loadSession();
        if (!session.success) {
          setGoogleError({ visible: true, message: GOOGLE_DEFAULT_ERROR });
        }
        return;
      }

      // signup_required: abre o wizard em modo Google (GAUTH-24, 28).
      setRegistrationData({
        ...INITIAL_REGISTRATION_DATA,
        email: response.prefill.email,
        first_name: response.prefill.first_name,
        last_name: response.prefill.last_name,
        google_signup_token: response.signup_token,
      });
      if (pathname !== '/register') {
        router.push('/(auth)/register');
      }
    } catch (error: any) {
      setGoogleError({ visible: true, message: getGoogleErrorMessage(error) });
    } finally {
      inFlight.current = false;
      setIsGoogleLoading(false);
    }
  };

  return {
    handleGoogle,
    isGoogleLoading,
    ready,
    googleError,
    closeGoogleError: () => setGoogleError({ visible: false, message: '' }),
  };
};
