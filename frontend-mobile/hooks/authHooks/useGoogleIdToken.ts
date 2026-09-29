// Native version (Android). On web, Metro resolves useGoogleIdToken.web.ts.
import type { UseGoogleIdTokenResult } from './useGoogleIdToken.web';

type GoogleSigninModule = typeof import('@react-native-google-signin/google-signin');

const GOOGLE_WEB_CLIENT_ID = process.env.EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID ?? '';
const EXPO_GO_MESSAGE = 'Login com Google indisponível no Expo Go. Use o build do app.';

let isConfigured = false;

// The native module only exists in the app build. On Expo Go, importing it at the top would crash the login screen.
function loadGoogleSignin(): GoogleSigninModule {
  try {
    return require('@react-native-google-signin/google-signin') as GoogleSigninModule;
  } catch {
    throw new Error(EXPO_GO_MESSAGE);
  }
}

export function useGoogleIdToken(): UseGoogleIdTokenResult {
  const getIdToken = async (): Promise<string | null> => {
    const { GoogleSignin } = loadGoogleSignin();

    if (!isConfigured) {
      GoogleSignin.configure({ webClientId: GOOGLE_WEB_CLIENT_ID });
      isConfigured = true;
    }

    await GoogleSignin.hasPlayServices({ showPlayServicesUpdateDialog: true });
    const response = await GoogleSignin.signIn();

    if (response.type === 'cancelled') {
      return null;
    }
    if (!response.data.idToken) {
      // Success without an idToken (e.g. invalid webClientId) is not a cancellation: let the error bubble up to the modal.
      throw new Error('O Google não devolveu o id_token.');
    }
    return response.data.idToken;
  };

  return { ready: true, getIdToken };
}
