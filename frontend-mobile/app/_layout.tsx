import React, { useState, useEffect, useContext } from 'react';
import { Slot, useRouter, useSegments } from 'expo-router';
import { Platform } from 'react-native';
import { Stack } from 'expo-router';
import axios from 'axios';
import axiosInstance, { setSessionExpiredHandler } from '../services/axios-instance';
import { REFRESH_PATH } from '../services/auth-routes';
import { UserInfo } from '../models/User.types';
import { homeRouteFor } from '../utils/routes';
import { Preference } from '../models/Preferences.types';
import { ApiConnectionError, ApiProblem, problemMessage, toApiProblem } from '../utils/api-problem';
import * as WebBrowser from 'expo-web-browser';

// Closes the Google login popup on web. Must run at startup: in the production build, the
// expo-router only evaluates the login screen after the redirect, too late to capture the popup's return.
WebBrowser.maybeCompleteAuthSession();

export const API_BACKEND_URL = process.env.EXPO_PUBLIC_API_BACKEND_URL;

const AuthContext = React.createContext<any>(null);

export function useAuth() {
  return useContext(AuthContext);
}

function RootLayoutNav() {
  const segments = useSegments();
  const router = useRouter();
  // Get userInfo here as well
  const { userToken, userInfo, isLoading } = useAuth();

  useEffect(() => {
    if (isLoading) return;

    const inAuthGroup = segments[0] === '(auth)';
    if (userToken && inAuthGroup) {
      const home = homeRouteFor(userInfo);
      if (home) router.replace(home);
    } else if (!userToken && !inAuthGroup) {
      router.replace('/(auth)/login');
    }
    
  }, [userToken, userInfo, isLoading, segments]);

  return <Slot />;
}

export default function RootLayout() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [userToken, setUserToken] = useState<string | null>(null);
  const [userInfo, setUserInfo] = useState<UserInfo | null>(null);

  // Loads the session from the `jwt` cookie already set by the backend.
  const loadSession = React.useCallback(async (): Promise<{ success: boolean; error?: string }> => {
    try {
      const authResponse = await axiosInstance.get(`${API_BACKEND_URL}/api/auth/session`, { withCredentials: true });

      if (authResponse.data.authenticated) {
        const userResponse = await axiosInstance.get(`${API_BACKEND_URL}/api/users/me`, { withCredentials: true });
        setUserInfo(userResponse.data);
        setUserToken('authenticated');
        return { success: true };
      } else {
        return { success: false, error: 'Falha na autenticação. Verifique suas credenciais.' };
      }
    } catch (error: any) {
      return { success: false, error: problemMessage(error, 'Um erro aconteceu, tente novamente') };
    }
  }, []);

  const authContext = React.useMemo(() => {
  return {
  loadSession,
  signIn: async (email: string, password: string): Promise<{ success: boolean; error?: string; slug?: ApiProblem['slug'] }> => {
    try {
      await axiosInstance.post(`${API_BACKEND_URL}/api/auth/login`, {
        email,
        password
      }, { withCredentials: true });
    } catch (error: any) {
      // The slug lets the login screen tell an account that still has to confirm its e-mail from a wrong password.
      return {
        success: false,
        error: problemMessage(error, 'Um erro aconteceu, tente novamente'),
        slug: toApiProblem(error)?.slug,
      };
    }

    return loadSession();
  },
  signUp: async (formData: FormData) => {
    if(Platform.OS === 'web') {
      try {
        // withCredentials: the browser stores the session cookie from the 201 (Google signup).
        return await axios.post(`${API_BACKEND_URL}/api/users`, formData, { withCredentials: true });
      } catch (error: any) {
        console.error('Registration error:', error.response?.data);
        // The AxiosError goes through as is: the wizard reads it with problemMessage (toApiProblem understands it).
        throw error;
      }
    }

    let response: Response;
    try {
      response = await fetch(`${API_BACKEND_URL}/api/users`, {
        method: 'POST',
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        body: formData,
      });
    } catch {
      // fetch rejects when the request never got an answer.
      throw new ApiConnectionError();
    }

    if (!response.ok) {
      // fetch doesn't throw on 4xx/5xx: pass the problem body through to the wizard, which reads it with problemMessage.
      const errorData = await response.json().catch(() => null);
      console.error('Registration error:', errorData);
      throw errorData || new Error('Ocorreu um erro desconhecido durante o cadastro.');
    }

    return response;
  },
  signOut: async () => {
    setIsLoading(true);
    try {
      await axiosInstance.post(`${API_BACKEND_URL}/api/auth/logout`, {}, { withCredentials: true });
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      // The local session ends even when the backend could not be reached.
      setUserToken(null);
      setUserInfo(null);
      setIsLoading(false);
    }
  },
  // Ends the session in the app only, for when the backend already ended it (the account was deleted).
  // isLoading stays as is: while it is true the layout renders nothing and would drop the navigation.
  clearSession: () => {
    setUserToken(null);
    setUserInfo(null);
  },
  userInfo,
  userToken,
  isLoading
  };
}, [userToken, userInfo, isLoading, loadSession]);

  useEffect(() => {
    // When the backend cannot refresh the session anymore, go back to the login without an error modal.
    setSessionExpiredHandler(() => {
      setUserToken(null);
      setUserInfo(null);
      router.replace('/(auth)/login');
    });
  }, []);

  useEffect(() => {
    // Restores the session from the cookies: the access token first, then a refresh if it is gone.
    const bootstrapAsync = async () => {
      try {
        let session = await loadSession();
        if (!session.success) {
          try {
            await axiosInstance.post(`${API_BACKEND_URL}${REFRESH_PATH}`, {}, { withCredentials: true });
            session = await loadSession();
          } catch (refreshError) {
            // No valid refresh token: stay on the login screen.
          }
        }
      } finally {
        setIsLoading(false);
      }
    };

    bootstrapAsync();
  }, []);

  if (isLoading) {
    return null; 
  }

  return (
    <AuthContext.Provider value={authContext}>
        <RootLayoutNav />
    </AuthContext.Provider>
  );
}