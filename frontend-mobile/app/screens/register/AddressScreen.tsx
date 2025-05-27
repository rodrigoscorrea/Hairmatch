import React, { useState, useContext, useEffect } from 'react';
import { View, Text, Alert, TextInput, TouchableOpacity, KeyboardAvoidingView, Image, ScrollView } from 'react-native';
import { styles } from './styles/AdressStyle';
import { RouteProp, useNavigation, useRoute } from '@react-navigation/native';
import { AuthContext } from '../../index';
import { StackNavigationProp } from '@react-navigation/stack';
import { RootStackParamList } from '@/app/models/RootStackParams.types';

// Define the route and navigation prop types
type AddressScreenRouteProp = RouteProp<RootStackParamList, 'Address'>;
type AddressScreenNavigationProp = StackNavigationProp<RootStackParamList>;

export default function Address() {
  // Use the hooks to get navigation and route
  const navigation = useNavigation<AddressScreenNavigationProp>();
  const route = useRoute<AddressScreenRouteProp>();
  
  // Extract params from route
  const personalData = route.params?.personalData;

  const [address, setAddress] = useState<string>('');
  const [number, setNumber] = useState<string>('');
  const [complement, setComplement] = useState<string>('');
  const [neighborhood, setNeighborhood] = useState<string>('');
  const [postal_code, setPostalCode] = useState<string>('');
  const [city, setCity] = useState<string>('');
  const [state, setState] = useState<string>('');

  // Debug log to check the received params
  useEffect(() => {
  }, [personalData]);

  const handleNext = () => {
    if (!personalData) {
      Alert.alert('Error', 'Personal information is missing');
      return;
    }

    if (!address || !postal_code || !city || !state) {
      Alert.alert('Error', 'Please fill in all required address fields');
      return;
    }

    // Create addressData object
    const addressData = {
      address,
      number,
      complement,
      neighborhood,
      postal_code,
      city,
      state
    };

    // Navigate to Preferences screen with all data
    navigation.navigate('Preferences', {
      personalData,
      addressData
    });
  };

  return (
    <KeyboardAvoidingView style={{ flex: 1 }} > 
      <ScrollView contentContainerStyle={styles.container}> 
        <View style={styles.header}>
          <Image source={require('../../../assets/images/HairmatchLogo.png')} />
          <Text style={styles.subtitle}>Informe seu endereço</Text>
        </View>
        <View style={styles.form}>
          <View style={styles.row}>
            <TextInput
              placeholder="Endereço"
              style={[styles.input, { flex: 2, marginRight: 5 }]}
              value={address}
              onChangeText={setAddress}
            />
            <TextInput
              placeholder="Número"
              style={[styles.input, { flex: 1 }]}
              value={number}
              onChangeText={setNumber}
            />
          </View>
          <TextInput
            placeholder="Complemento"
            style={styles.input}
            value={complement}
            onChangeText={setComplement}
          />
          <View style={styles.row}>
            <TextInput
              placeholder="Bairro"
              style={[styles.input, { flex: 1, marginRight: 5 }]}
              value={neighborhood}
              onChangeText={setNeighborhood}
            />
            <TextInput
              placeholder="CEP"
              style={[styles.input, { flex: 1 }]}
              value={postal_code}
              onChangeText={setPostalCode}
              keyboardType="numeric"
            />
          </View>
          <View style={styles.row}>
            <TextInput
              placeholder="Cidade"
              style={[styles.input, { flex: 2, marginRight: 5 }]}
              value={city}
              onChangeText={setCity}
            />
            <TextInput
              placeholder="UF"
              style={[styles.input, { flex: 1 }]}
              value={state}
              onChangeText={setState}
              maxLength={2}
            />
          </View>
          <View style={styles.buttonContainer}>
            <TouchableOpacity style={styles.backButton} onPress={() => navigation.goBack()}>
              <Text style={styles.backButtonText}>Voltar</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.button} onPress={handleNext}>
              <Text style={styles.buttonText}>Próximo</Text>
            </TouchableOpacity>
          </View>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

