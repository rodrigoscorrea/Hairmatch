// Versão nativa (Android). No web, o Metro resolve useGoogleIdToken.web.ts.
import type { UseGoogleIdTokenResult } from './useGoogleIdToken.web';

type GoogleSigninModule = typeof import('@react-native-google-signin/google-signin');

const GOOGLE_WEB_CLIENT_ID = process.env.EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID ?? '';
const EXPO_GO_MESSAGE = 'Login com Google indisponível no Expo Go. Use o build do app.';

let isConfigured = false;

// O módulo nativo só existe no build do app. No Expo Go, importar no topo derrubaria a tela de login.
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
      // Sucesso sem idToken (ex.: webClientId inválido) não é cancelamento: deixa o erro subir para o modal.
      throw new Error('O Google não devolveu o id_token.');
    }
    return response.data.idToken;
  };

  return { ready: true, getIdToken };
}
