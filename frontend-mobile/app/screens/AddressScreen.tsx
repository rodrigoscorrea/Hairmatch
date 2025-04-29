import React, { useState, useContext } from 'react';
import { View, Text, Alert ,TextInput, TouchableOpacity, StyleSheet, KeyboardAvoidingView, Platform } from 'react-native';
import { RouteProp, useNavigation, useRoute } from '@react-navigation/native';
import { AuthContext } from '../index';

type RegisterRouteParams = {
  PersonalData: {
    first_name: string 
    last_name: string 
    phone: string 
    email: string 
    cnpj?: string 
    cpf?: string 
    password: string 
    role: string
  }
}

type RegisterScreenRouteProp = RouteProp<RegisterRouteParams, 'PersonalData'>

type Props = {
  route: RegisterScreenRouteProp;
  navigation: any
}

export default function Address({route, navigation}: Props) {
  //const navigation = useNavigation<any>();
  //const router = useRoute();
  const {first_name, last_name, phone, email, cnpj, cpf, password, role} = route.params;

  const [address, setAddress] = useState('');
  const [number, setNumber] = useState('');
  const [complement, setComplement] = useState('');
  const [neighborhood, setNeighborhood] = useState('');
  const [postal_code, setPostalCode] = useState('');
  const [city, setCity] = useState('');
  const [state, setState] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { signUp } = useContext<any>(AuthContext);

  const handleRegister = async () => {
      if (!first_name || !email || !password) {
        Alert.alert('Error', 'Please fill in all fields');
        return;
      }
      
      /* if (password !== confirmPassword) {
        Alert.alert('Error', 'Passwords do not match');
        return;
      } */
  
      if (password.length < 8) {
        Alert.alert('Error', 'Password must be at least 8 characters');
        return;
      }
  
      setIsLoading(true);
      try {
        // Register the 
        await signUp(first_name, last_name,phone, email, password, 
                    address, number, complement, postal_code, state, 
                    city, role, cpf, cnpj);
        Alert.alert(
          'Success', 
          'Registration successful! Please log in.',
          [{ text: 'OK', onPress: () => navigation.navigate('Login') }]
        );
      } catch (error: any) {
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
          <TouchableOpacity style={styles.button} onPress={() => {handleRegister()}}>
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
    marginTop: 80, // Ajustado para menos espaço entre os botões
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
