import React, { useState, useEffect } from 'react';
import { createStackNavigator } from '@react-navigation/stack';
import AsyncStorage from '@react-native-async-storage/async-storage';
import axios from 'axios';
import LoginScreen from './screens/LoginScreen';
import RegisterScreen from './screens/register/RegisterScreen';
import AddressScreen from './screens/register/AddressScreen';
import PreferencesScreen from './screens/register/PreferencesScreen';
import HomeScreen from './screens/HomeScreen';
import ServiceBookingScreen from './screens/customer/reservation/ServiceReservationScreen';
import CustomerHomeScreen from './screens/customer/home/CustomerHomeScreen';
import SearchScreen from './screens/customer/SearchScreen';
import ProfileScreen from './screens/customer/ProfileScreen';
import ReservesScreen from './screens/customer/ReservesScreen';
import ProfessionalStory from './screens/register/ProfessionalStory';
import DescriptionScreen from './screens/register/DescriptionScreen';
import { RootStackParamList } from './models/RootStackParams.types';
import HairdresserProfileReservationScreen from './screens/customer/reservation/HairdresserProfileReservationScreen';
import { UserInfo, UserRole } from './models/User.types';
import { Preference } from './models/Preferences.types';
import { StackNavigationProp } from '@react-navigation/stack';
import { Stack } from 'expo-router';
import { useNavigation } from '@react-navigation/native';
import { BottomTabProvider } from './contexts/BottomTabContext';
import HairdresserProfileScreen from './screens/hairdresser/profile/HairdresserProfileScreen';
import HairdresserServiceManageScreen from './screens/hairdresser/service/HaidresserServiceManager';
import HairdresserServiceCreationScreen from './screens/hairdresser/service/HaidresserServiceCreationScreen';
import HairdresserServiceEditScreen from './screens/hairdresser/service/HairdresserServiceEditScreen';
import AvailabilityManagerScreen from './screens/hairdresser/availability/AvailabilityManagerScreen';
import AvailabilityCreateScreen from './screens/hairdresser/availability/AvailabilityCreateScreen';
import AvailabilityEditScreen from './screens/hairdresser/availability/AvailabilityEditScreen';
import AgendaManagerScreen from './screens/hairdresser/agenda/AgendaManagerScreen';
import axiosInstance from './services/axios-instance';
import HairdresserSettingsScreen from './screens/hairdresser/profile/HairdresserSettingsScreen';
export const API_BACKEND_URL = process.env.EXPO_PUBLIC_API_BACKEND_URL

export const AuthContext = React.createContext<any>({});

type IndexNavigationProp = StackNavigationProp<RootStackParamList>;

function App() {
  const API_BACKEND_URL = process.env.EXPO_PUBLIC_API_BACKEND_URL;
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [userToken, setUserToken] = useState<string | null>(null);
  const [userInfo, setUserInfo] = useState<UserInfo | null>(null);
  const navigation = useNavigation<IndexNavigationProp>();

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
    signUp: async (
      first_name: string,
      last_name: string,
      phone: string,
      email: string,
      password: string,
      address: string,
      number: string,
      neighborhood: string,
      complement: string,
      postal_code: string,
      state: string,
      city: string,
      role: string,
      rating: number,
      cpf?: string,
      cnpj?: string,
      preferences?: Preference[],
      experience_time?: string,
      experiences?: string,
      products?: string,
      resume?: string
    ) => {
      setIsLoading(true);
      try {
        // Construct the data object based on role
        const userData = role === UserRole.CUSTOMER 
          ? {
              first_name,
              last_name,
              phone,
              email,
              password,
              address,
              number,
              complement,
              neighborhood,
              postal_code,
              state,
              city,
              role,
              rating,
              cpf,
              preferences
            }
          : {
              first_name,
              last_name,
              phone,
              email,
              password,
              address,
              number, 
              complement,
              neighborhood,
              postal_code,
              state,
              city,
              role,
              rating,
              cnpj,
              preferences,
              experience_time,
              experiences,
              products,
              resume
            };  
        const response = await axios.post(`${API_BACKEND_URL}/api/auth/register`, userData);
        return response.data;
      } catch (error: any) {
        console.error('Registration error:', error.response?.data || error.message);
        throw error;
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
    userInfo
  }), [userToken, userInfo]);

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
      {userToken == null ? (
        <Stack screenOptions={{ headerShown: false }}>
          <Stack.Screen name="Login"  />
          <Stack.Screen name="Register"  />
          <Stack.Screen name="Address"  />
          <Stack.Screen name="Preferences"  />
          <Stack.Screen name="ProfessionalStory" />
          <Stack.Screen name="Description"  />
        </Stack>
      ) : (
        <BottomTabProvider>
          {userInfo?.customer?.user.role === UserRole.CUSTOMER ? (
            <>
              <Stack screenOptions={{ headerShown: false }}>
                <Stack.Screen name="CustomerHome"/>
                <Stack.Screen name="ServiceBooking"/>
                <Stack.Screen name="HairdresserProfileReservation" />
                <Stack.Screen name="Home"  />
                <Stack.Screen name="Search" />
                <Stack.Screen name="Reserves" />
                <Stack.Screen name="Profile"  />
              </Stack>
            </>
          ):(
            <>
              <Stack screenOptions={{ headerShown: false }}>
                <Stack.Screen name="HairdresserProfile" />
                <Stack.Screen name="HairdresserSettings"/>
                <Stack.Screen name="Home" />
                <Stack.Screen name="Search" />
                <Stack.Screen name="HairdresserServiceManager"  />
                <Stack.Screen name="HairdresserServiceCreation" />
                <Stack.Screen name="HairdresserServiceEdit" />
                <Stack.Screen name="AvailabilityManager"  />
                <Stack.Screen name="AvailabilityCreate" />
                <Stack.Screen name="AvailabilityEdit"  />
                <Stack.Screen name="AgendaManager"  />
              </Stack>
            </>
          )}
        </BottomTabProvider>
      )}
    </AuthContext.Provider>
  );
}

export default App;