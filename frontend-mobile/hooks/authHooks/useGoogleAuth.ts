import { useRef, useState } from 'react';
import axios from 'axios';
import { usePathname, useRouter } from 'expo-router';
import { useAuth } from '@/app/_layout';
import { INITIAL_REGISTRATION_DATA, useRegistration } from '@/contexts/RegistrationContext';
import { loginWithGoogle } from '@/services/google-auth.service';
import { useGoogleIdToken } from './useGoogleIdToken';

const GOOGLE_DEFAULT_ERROR = 'Não foi possível entrar com o Google. Tente novamente.';

// SPEC_DEVIATION: the design only accounts for `error.response.data.error` or the default text.
// Reason: errors that don't come from axios (e.g. "Google login unavailable on Expo Go...", required by T14)
// need to show their own message. Axios errors without `error` (e.g. backend unreachable) use the default text (GAUTH-09).
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
  // Avoids two flows from taps in the same frame, before the button re-renders disabled (GAUTH-10).
  const inFlight = useRef(false);

  const handleGoogle = async () => {
    if (inFlight.current) return;
    inFlight.current = true;
    setIsGoogleLoading(true);

    try {
      // First await of the flow: on web, the popup must open in the same tick as the tap, or the browser blocks it.
      const idToken = await getIdToken();
      if (!idToken) return; // Cancellation: stays on the screen, no modal (GAUTH-08).

      const response = await loginWithGoogle(idToken);

      if (response.status === 'authenticated') {
        // RootLayoutNav leads to the role's home after the session loads (GAUTH-07, 29).
        const session = await loadSession();
        if (!session.success) {
          setGoogleError({ visible: true, message: GOOGLE_DEFAULT_ERROR });
        }
        return;
      }

      // signup_required: opens the wizard in Google mode (GAUTH-24, 28).
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
