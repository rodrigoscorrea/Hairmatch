import React, { useState, useEffect } from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';
import AsyncStorage from '@react-native-async-storage/async-storage';
import axios from 'axios';
import LoginScreen from './screens/LoginScreen';
import RegisterScreen from './screens/register/RegisterScreen';
import AddressScreen from './screens/register/AddressScreen';
import PreferencesScreen from './screens/register/PreferencesScreen';
import HomeScreen from './screens/HomeScreen';
import { RootStackParamList } from './models/RootStackParams.types';
import HairdresserProfileScreen from './screens/customer/reservation/HairdresserProfileScreen';
import { AuthContextType } from './models/Auth.types';
import { UserRole } from './models/User.types';

export const API_URL = 'https://7a03-2804-214-d-2495-505d-40ab-5d6a-805c.ngrok-free.app';

export const AuthContext = React.createContext<AuthContextType>({});

const Stack = createStackNavigator<RootStackParamList>();

function App() {
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [userToken, setUserToken] = useState<string | null>(null);
  const [userInfo, setUserInfo] = useState<any>(null);

  const authContext = React.useMemo(() => ({
    signIn: async (email: string, password: string) => {
      setIsLoading(true);
      try {
        // Step 1: Make login POST request (sets HttpOnly cookie)
        await axios.post(`${API_URL}/api/auth/login`, {
          email,
          password
        });
        
        // Step 2: Check authentication with GET request
        const authResponse = await axios.get(`${API_URL}/api/auth/user`);
        console.log('Auth check response:', authResponse.data);
        
        if (authResponse.data.authenticated) {
          console.log('User is authenticated');
          setUserToken('authenticated'); // Just need a non-null value to trigger navigation
          
          // Step 3: Fetch user info
          const userResponse = await axios.get(`${API_URL}/api/user/authenticated`);
          setUserInfo(userResponse.data.user);
        } else {
          console.log('Authentication failed');
        }
      } catch (error: any) {
        console.error('Login error:', error.response?.data || error.message);
        throw error;
      } finally {
        setIsLoading(false);
        
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
      cnpj?: string
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
              cpf
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
              cnpj
            };
        const response = await axios.post(`${API_URL}/api/auth/register`, userData);
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
        await axios.post(`${API_URL}/api/auth/logout`);
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
      const response = await axios.get(`${API_URL}/api/user`, { headers });
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
        <Stack.Navigator screenOptions={{ headerShown: false }}>
          <Stack.Screen name="Home" component={HomeScreen} />
          <Stack.Screen name="Login" component={LoginScreen} />
          <Stack.Screen name="Register" component={RegisterScreen} />
          <Stack.Screen name="Address" component={AddressScreen} />
          <Stack.Screen name="Preferences" component={PreferencesScreen} />
          <Stack.Screen name="MockedHairdresserProfile" component={HairdresserProfileScreen} />
        </Stack.Navigator>
    </AuthContext.Provider>
  );
}

export default App;