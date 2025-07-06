import React, { useState, useEffect, useContext } from 'react';
import { Slot, useRouter, useSegments } from 'expo-router';
import { Platform } from 'react-native';
import { Stack } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import axios from 'axios';
import axiosInstance from '../services/axios-instance';
import { UserInfo, UserRole } from '../models/User.types';
import { Preference } from '../models/Preferences.types';

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
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [userToken, setUserToken] = useState<string | null>(null);
  const [userInfo, setUserInfo] = useState<UserInfo | null>(null);

  const authContext = React.useMemo(() => ({
  signIn: async (email: string, password: string): Promise<{ success: boolean; error?: string }> => {
    try {
      await axios.post(`${API_BACKEND_URL}/api/auth/login`, {
        email,
        password
      }, { withCredentials: true });

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
  },
  signUp: async (formData: FormData) => {
    setIsLoading(true);
    try {
      if(Platform.OS === 'web') {
        const response = await axios.post(`${API_BACKEND_URL}/api/auth/register`, formData);
        console.log(response);
      } else {
        const response = await fetch(`${API_BACKEND_URL}/api/auth/register`, {
          method: 'POST',
          headers: {
            'Content-Type': 'multipart/form-data',
          },
          body: formData,
        });
      }
        
    } catch (error: any) {
      console.log(error)
        console.error('Registration error:', error.response?.data || error.message);
        throw error.response?.data || new Error("An unknown error occurred during registration.");
    } finally {
        setIsLoading(false);
    }
  },
  signOut: async () => {
    setIsLoading(true);
    try {
      await axios.post(`${API_BACKEND_URL}/api/auth/logout`);
      await AsyncStorage.removeItem('userToken');
      setUserToken(null);
      setUserInfo(null);
      delete axios.defaults.headers.common['Authorization'];
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      setIsLoading(false);
    }
  },
  userInfo,
  userToken,
  isLoading
}), [userToken, userInfo, isLoading]);

  const fetchUserInfo = async (token: string) => {
    try {
      // Set the token in headers
      const headers = { Authorization: `Bearer ${token}` };
      const response = await axios.get(`${API_BACKEND_URL}/api/user`, { headers });
      setUserInfo(response.data.user);
    } catch (error) {
      console.error('Error fetching user info:', error);
    }
  };

  useEffect(() => {
    // Check if user is logged in
    const bootstrapAsync = async () => {
      try {
        const token = await AsyncStorage.getItem('userToken');
        if (token) {
          setUserToken(token);
          axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
          fetchUserInfo(token);
        }
      } catch (e) {
        console.error('Failed to restore token:', e);
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