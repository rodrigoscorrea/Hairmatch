import React, { useState, useContext, useEffect } from 'react';
import { View, Text, Alert, TextInput, TouchableOpacity, StyleSheet, KeyboardAvoidingView } from 'react-native';
import { RouteProp, useNavigation, useRoute } from '@react-navigation/native';
import { AuthContext } from '../index';
import { StackNavigationProp } from '@react-navigation/stack';

// Define your navigation param list
type RootStackParamList = {
  Home: undefined;
  Login: undefined;
  Register: undefined;
  Address: {
    personalData: {
      first_name1: string;
      last_name1: string;
      phone1: string;
      email1: string;
      cnpj1?: string;
      cpf1?: string;
      password1: string;
      role1: string;
    }
  };
};

// Define the route and navigation prop types
type AddressScreenRouteProp = RouteProp<RootStackParamList, 'Address'>;
type AddressScreenNavigationProp = StackNavigationProp<RootStackParamList>;

export default function Address() {
  // Use the hooks to get navigation and route
  const navigation = useNavigation<AddressScreenNavigationProp>();
  const route = useRoute<AddressScreenRouteProp>();
  
  // Extract params from route
  const personalData = route.params?.personalData;

  const [address, setAddress] = useState('');
  const [number, setNumber] = useState('');
  const [complement, setComplement] = useState('');
  const [neighborhood, setNeighborhood] = useState('');
  const [postal_code, setPostalCode] = useState('');
  const [city, setCity] = useState('');
  const [state, setState] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { signUp } = useContext<any>(AuthContext);

  // Debug log to check the received params
  useEffect(() => {
    console.log("Received personal data:", personalData);
  }, [personalData]);

  const handleRegister = async () => {
    if (!personalData) {
      Alert.alert('Error', 'Personal information is missing');
      return;
    }

    const { first_name1, last_name1, phone1, email1, password1, role1, cpf1, cnpj1 } = personalData;
    
    if (!first_name1 || !email1 || !password1) {
      Alert.alert('Error', 'Personal information is incomplete');
      return;
    }

    if (!address || !postal_code || !city || !state) {
      Alert.alert('Error', 'Please fill in all required address fields');
      return;
    }

    setIsLoading(true);
    try {
      await signUp(
        first_name1, 
        last_name1,
        phone1, 
        email1, 
        password1, 
        address, 
        number, 
        complement, 
        postal_code, 
        state, 
        city, 
        role1, 
        cpf1, 
        cnpj1
      );
      Alert.alert(
        'Success', 
        'Registration successful! Please log in.',
        [{ text: 'OK', onPress: () => navigation.navigate('Login') }]
      );
    } catch (error: any) {
      console.log(error)
      const errorMessage = error.response?.data?.error || 'Registration failed';
      Alert.alert('Error', errorMessage);
    } finally {
      setIsLoading(false);
    }
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

          {/* Botão Confirmar */}
          <TouchableOpacity style={styles.button} onPress={handleRegister}>
            <Text style={styles.buttonText}>Confirmar</Text>
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