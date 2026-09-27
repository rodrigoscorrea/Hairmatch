import { useState } from 'react';
import * as WebBrowser from 'expo-web-browser';
import * as Crypto from 'expo-crypto';
import {
  makeRedirectUri,
  ResponseType,
  useAuthRequest,
  useAutoDiscovery,
} from 'expo-auth-session';

// Fecha o popup do Google quando esta página é carregada nele, depois do redirect.
WebBrowser.maybeCompleteAuthSession();

export type UseGoogleIdTokenResult = {
  ready: boolean;
  // Retorna o id_token do Google, ou null quando o usuário cancela ou fecha o popup.
  getIdToken: () => Promise<string | null>;
};

const GOOGLE_WEB_CLIENT_ID = process.env.EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID ?? '';

export function useGoogleIdToken(): UseGoogleIdTokenResult {
  const discovery = useAutoDiscovery('https://accounts.google.com');
  // O Google exige nonce no fluxo implícito de id_token. Fica estável para não recriar o request a cada render.
  const [nonce] = useState(() => Crypto.randomUUID());

  const [request, , promptAsync] = useAuthRequest(
    {
      clientId: GOOGLE_WEB_CLIENT_ID,
      responseType: ResponseType.IdToken,
      scopes: ['openid', 'email', 'profile'],
      redirectUri: makeRedirectUri(),
      usePKCE: false,
      extraParams: { nonce },
    },
    discovery,
  );

  // Sem nenhum await antes do promptAsync: o window.open precisa sair direto do toque, senão o navegador bloqueia o popup.
  const getIdToken = async (): Promise<string | null> => {
    const result = await promptAsync();
    if (result.type !== 'success') {
      return null;
    }
    if (!result.params.id_token) {
      // Sucesso sem id_token não é cancelamento: deixa o erro subir para o modal.
      throw new Error('O Google não devolveu o id_token.');
    }
    return result.params.id_token;
  };

  return { ready: !!request, getIdToken };
}
