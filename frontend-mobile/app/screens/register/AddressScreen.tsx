import React, { useState, useContext, useEffect } from 'react';
import { View, Text, Alert, TextInput, TouchableOpacity, StyleSheet, KeyboardAvoidingView } from 'react-native';
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
    <KeyboardAvoidingView style={styles.container}>
      {/* Parte superior */}
      <View style={styles.header}>
        <Text style={styles.title}>HairMatch</Text>
        <Text style={styles.subtitle}>Informe seu endereço</Text>
      </View>

      {/* Inputs centralizados */}
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

        {/* Botões */}
        <View style={styles.buttonContainer}>
          {/* Botão Voltar */}
          <TouchableOpacity style={styles.backButton} onPress={() => navigation.goBack()}>
            <Text style={styles.backButtonText}>Voltar</Text>
          </TouchableOpacity>

          {/* Botão Próximo (modificado de "Confirmar") */}
          <TouchableOpacity style={styles.button} onPress={handleNext}>
            <Text style={styles.buttonText}>Próximo</Text>
          </TouchableOpacity>
        </View>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FFECE3',
    alignItems: 'center',
    padding: 20,
    justifyContent: 'flex-start',
  },
  header: {
    marginTop: 70,
    marginBottom: 10,
    alignItems: 'center',
  },
  form: {
    width: '100%',
    marginTop: 50,
  },
  title: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#FF6B00',
  },
  subtitle: {
    fontSize: 20,
    marginVertical: 10,
    color: '#555',
    textAlign: 'center',
  },
  row: {
    flexDirection: 'row',
    width: '100%',
  },
  input: {
    backgroundColor: 'white',
    width: '100%',
    borderRadius: 10,
    paddingHorizontal: 15,
    paddingVertical: 12,
    marginVertical: 5,
  },
  buttonContainer: {
    flexDirection: 'row',
    marginTop: 80,
    width: '100%',
    justifyContent: 'space-between',
  },
  backButton: {
    backgroundColor: '#FFFFFF',
    padding: 14,
    borderRadius: 8,
    flex: 1,
    marginRight: 8,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 3.84,
    elevation: 5,
  },
  backButtonText: {
    color: '#9B59B6',
    fontWeight: 'bold',
  },
  button: {
    backgroundColor: '#FF6B00',
    borderRadius: 10,
    padding: 15,
    alignItems: 'center',
    flex: 1,
  },
  buttonText: {
    color: 'white',
    fontWeight: '700',
    fontSize: 16,
  },
});