import React, { useState, useEffect, useContext } from 'react';
import { Slot, useRouter, useSegments } from 'expo-router';
import { Platform } from 'react-native';
import { Stack } from 'expo-router';
import axios from 'axios';
import axiosInstance, { setSessionExpiredHandler } from '../services/axios-instance';
import { UserInfo, UserRole } from '../models/User.types';
import { Preference } from '../models/Preferences.types';
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
      if (userInfo?.customer?.user?.role === UserRole.CUSTOMER) {
        router.replace('/(app)/(customer)/home');
      } else if (userInfo?.hairdresser?.user?.role === UserRole.HAIRDRESSER) {
        router.replace('/(app)/(hairdresser)/agenda');
      }
      
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
      const authResponse = await axiosInstance.get(`${API_BACKEND_URL}/api/auth/user`, { withCredentials: true });

      if (authResponse.data.authenticated) {
        const userResponse = await axiosInstance.get(`${API_BACKEND_URL}/api/user/authenticated`, { withCredentials: true });
        setUserInfo(userResponse.data);
        setUserToken('authenticated');
        return { success: true };
      } else {
        return { success: false, error: 'Authentication failed. Please check your credentials.' };
      }
    } catch (error: any) {
        const errorMessage = error.response?.data?.error || 'Um erro aconteceu, tente novamente';
      return { success: false, error: errorMessage };
    }
  }, []);

  const authContext = React.useMemo(() => {
  return {
  loadSession,
  signIn: async (email: string, password: string): Promise<{ success: boolean; error?: string }> => {
    try {
      await axiosInstance.post(`${API_BACKEND_URL}/api/auth/login`, {
        email,
        password
      }, { withCredentials: true });
    } catch (error: any) {
        const errorMessage = error.response?.data?.error || 'Um erro aconteceu, tente novamente';
      return { success: false, error: errorMessage };
    }

    return loadSession();
  },
  signUp: async (formData: FormData) => {
    if(Platform.OS === 'web') {
      try {
        // withCredentials: the browser stores the session cookie from the 201 (Google signup).
        return await axios.post(`${API_BACKEND_URL}/api/auth/register`, formData, { withCredentials: true });
      } catch (error: any) {
        console.error('Registration error:', error.response?.data);
        throw error.response?.data || new Error("An unknown error occurred during registration.");
      }
    }

    const response = await fetch(`${API_BACKEND_URL}/api/auth/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      body: formData,
    });

    if (!response.ok) {
      // fetch doesn't throw on 4xx/5xx: pass the error JSON ({ error }) through to the wizard.
      const errorData = await response.json().catch(() => null);
      console.error('Registration error:', errorData);
      throw errorData || new Error("An unknown error occurred during registration.");
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
            await axiosInstance.post(`${API_BACKEND_URL}/api/auth/refresh`, {}, { withCredentials: true });
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