import React, { useState, useEffect } from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';
import AsyncStorage from '@react-native-async-storage/async-storage';
import axios from 'axios';
import LoginScreen from './screens/LoginScreen';
import RegisterScreen from './screens/RegisterScreen';
import AddressScreen from './screens/AddressScreen';
import HomeScreen from './screens/HomeScreen'
import {
  View,
  Text
} from 'react-native';
import { Hairdresser } from './types/Hairdresser.types';
import { Customer } from './types/Customer.types';


const API_URL = 'https://47cc-2804-14d-14bc-22f-4a54-ee9b-72a7-6b5.ngrok-free.app'; // For Android emulator pointing to localhost

// Create AuthContext
export const AuthContext = React.createContext({});

const Stack = createStackNavigator();

function App() {

  const [isLoading, setIsLoading] = useState<any>(true);
  const [userToken, setUserToken] = useState<any>(null);
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
          const userResponse = await axios.get(`${API_URL}/api/user`);
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
      data: Hairdresser | Customer
    ) => {
      setIsLoading(true);
      try {
        const response = await axios.post(`${API_URL}/api/auth/register`, {
          data
        });
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

  const fetchUserInfo = async (token: any) => {
    try {
      // Set the token in headers
      const headers = { Authorization: `Bearer ${token}` };
      const response = await axios.get(`${API_URL}/api/user`, { headers });
      console.log(response.data.user)
      setUserInfo(response.data.user);
    } catch (error) {
      console.error('Error fetching user info:', error);
    }
  };

  useEffect(() => {
    // Check if user is logged in
    const bootstrapAsync = async () => {
      try {
        const token: any = await AsyncStorage.getItem('userToken');
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
    return null; // You could show a splash screen or loading indicator here
  }

  return (
    
      <Stack.Navigator initialRouteName="Home" screenOptions={{ headerShown: false }}>
        <Stack.Screen name="Home" component={HomeScreen} />
        <Stack.Screen name="Login" component={LoginScreen} />
        <Stack.Screen name="Register" component={RegisterScreen} />
        <Stack.Screen name="Address" component={AddressScreen} />
      </Stack.Navigator>
    
  );
}

export default App;
