import { useState } from 'react';
import * as WebBrowser from 'expo-web-browser';
import * as Crypto from 'expo-crypto';
import {
  makeRedirectUri,
  ResponseType,
  useAuthRequest,
  useAutoDiscovery,
} from 'expo-auth-session';

// Closes the Google popup when this page is loaded in it, after the redirect.
WebBrowser.maybeCompleteAuthSession();

export type UseGoogleIdTokenResult = {
  ready: boolean;
  // Returns the Google id_token, or null when the user cancels or closes the popup.
  getIdToken: () => Promise<string | null>;
};

const GOOGLE_WEB_CLIENT_ID = process.env.EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID ?? '';

export function useGoogleIdToken(): UseGoogleIdTokenResult {
  const discovery = useAutoDiscovery('https://accounts.google.com');
  // Google requires a nonce in the implicit id_token flow. Kept stable to avoid recreating the request on every render.
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

  // No await before promptAsync: window.open must fire directly from the tap, or the browser blocks the popup.
  const getIdToken = async (): Promise<string | null> => {
    const result = await promptAsync();
    if (result.type !== 'success') {
      return null;
    }
    if (!result.params.id_token) {
      // Success without an id_token is not a cancellation: let the error bubble up to the modal.
      throw new Error('O Google não devolveu o id_token.');
    }
    return result.params.id_token;
  };

  return { ready: !!request, getIdToken };
}
