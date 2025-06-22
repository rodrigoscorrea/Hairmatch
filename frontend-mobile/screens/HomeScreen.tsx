import React, {useContext} from 'react';
import { View, Text, TouchableOpacity, Alert} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { AuthContext } from '../index';
import { RootStackParamList } from '../models/RootStackParams.types';
import { StackNavigationProp } from '@react-navigation/stack';

type HomeScreenNavigationProp = StackNavigationProp<RootStackParamList>;

export default function HomeScreen() {

  const navigation = useNavigation<HomeScreenNavigationProp>();
  const { signOut } = useContext<any>(AuthContext);
  const handleLogout = async () => {
    try {
      await signOut();
      navigation.navigate('Login');
    } catch (error: any) {
      const errorMessage = error.response?.data?.error || 'Login failed. Please try again.';
      Alert.alert('Error', errorMessage);
    }
  };

  const handleMock = async () =>{
    navigation.navigate('HairdresserProfile')
  }

  const handleCustomerHome = async () =>{
    navigation.navigate('CustomerHome')
  }
  return (
    <View>
      <Text>
      Hairmatch Home
      </Text>
      <TouchableOpacity onPress={()=> navigation.navigate('Login')}>
        <Text>Logar</Text>
      </TouchableOpacity>

      <TouchableOpacity onPress={handleLogout}>
        <Text>Logout</Text>
      </TouchableOpacity>

      <TouchableOpacity onPress={handleMock}>
        <Text>MockedHairdresser</Text>
      </TouchableOpacity>

      <TouchableOpacity onPress={handleCustomerHome}>
        <Text>CUSTOMER HOME TEST</Text>
      </TouchableOpacity>
    </View>
  );
}


