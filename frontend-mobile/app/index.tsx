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
import { useNavigation } from '@react-navigation/native';
import { BottomTabProvider } from './contexts/BottomTabContext';
import HairdresserProfileScreen from './screens/hairdresser/profile/HairdresserProfileScreen';
import HairdresserServiceManageScreen from './screens/hairdresser/service/HaidresserServiceManager';
import HairdresserServiceCreationScreen from './screens/hairdresser/service/HaidresserServiceCreationScreen';
import HairdresserServiceEditScreen from './screens/hairdresser/service/HairdresserServiceEditScreen';
import AvailabilityManagerScreen from './screens/hairdresser/availability/AvailabilityManagerScreen';
import AvailabilityCreateScreen from './screens/hairdresser/availability/AvailabilityCreateScreen';
import AvailabilityEditScreen from './screens/hairdresser/availability/AvailabilityEditScreen';

export const API_BACKEND_URL = process.env.EXPO_PUBLIC_API_BACKEND_URL

export const AuthContext = React.createContext<any>({});

const Stack = createStackNavigator<RootStackParamList>();

type IndexNavigationProp = StackNavigationProp<RootStackParamList>;

function App() {
  const API_BACKEND_URL = process.env.EXPO_PUBLIC_API_BACKEND_URL;
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [userToken, setUserToken] = useState<string | null>(null);
  const [userInfo, setUserInfo] = useState<UserInfo | null>(null);
  const navigation = useNavigation<IndexNavigationProp>();

  const authContext = React.useMemo(() => ({
    signIn: async (email: string, password: string) => {
      setIsLoading(true);
      try {
        // Step 1: Make login POST request (sets HttpOnly cookie)
        await axios.post(`${API_BACKEND_URL}/api/auth/login`, {
          email,
          password
        });
        
        // Step 2: Check authentication with GET request
        const authResponse = await axios.get(`${API_BACKEND_URL}/api/auth/user`);
        console.log('Auth check response:', authResponse.data);
        
        if (authResponse.data.authenticated) {
          console.log('User is authenticated');
          setUserToken('authenticated'); // Just need a non-null value to trigger navigation
          
          // Step 3: Fetch user info
          const userResponse = await axios.get(`${API_BACKEND_URL}/api/user/authenticated`);
          setUserInfo(userResponse.data);
          return true;
        } else {
          console.log('Authentication failed');
          return false;
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
        <Stack.Navigator screenOptions={{ headerShown: false }}>
          <Stack.Screen name="Login" component={LoginScreen} />
          <Stack.Screen name="Register" component={RegisterScreen} />
          <Stack.Screen name="Address" component={AddressScreen} />
          <Stack.Screen name="Preferences" component={PreferencesScreen} />
          <Stack.Screen name="ProfessionalStory" component={ProfessionalStory} />
          <Stack.Screen name="Description" component={DescriptionScreen} />
        </Stack.Navigator>
      ) : (
        <BottomTabProvider>
          {userInfo?.customer?.user.role === UserRole.CUSTOMER ? (
            <>
              <Stack.Navigator screenOptions={{ headerShown: false }}>
                <Stack.Screen name="CustomerHome" component={CustomerHomeScreen}/>
                <Stack.Screen name="ServiceBooking" component={ServiceBookingScreen} />
                <Stack.Screen name="HairdresserProfileReservation" component={HairdresserProfileReservationScreen} />
                <Stack.Screen name="Home" component={HomeScreen} />
                <Stack.Screen name="Search" component={SearchScreen} />
                <Stack.Screen name="Reserves" component={ReservesScreen} />
                <Stack.Screen name="Profile" component={ProfileScreen} />
              </Stack.Navigator>
            </>
          ):(
            <>
              <Stack.Navigator screenOptions={{ headerShown: false }}>
                <Stack.Screen name="HairdresserProfile" component={HairdresserProfileScreen} />
                <Stack.Screen name="Home" component={HomeScreen} />
                <Stack.Screen name="Search" component={SearchScreen} />
                <Stack.Screen name="HairdresserServiceManager" component={HairdresserServiceManageScreen} />
                <Stack.Screen name="HairdresserServiceCreation" component={HairdresserServiceCreationScreen} />
                <Stack.Screen name="HairdresserServiceEdit" component={HairdresserServiceEditScreen} />
                <Stack.Screen name="AvailabilityManager" component={AvailabilityManagerScreen} />
                <Stack.Screen name="AvailabilityCreate" component={AvailabilityCreateScreen} />
                <Stack.Screen name="AvailabilityEdit" component={AvailabilityEditScreen} />
              </Stack.Navigator>
            </>
          )}
        </BottomTabProvider>
      )}
    </AuthContext.Provider>
  );
}

export default App;