import React, { useState, useEffect } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, KeyboardAvoidingView, Image, ScrollView } from 'react-native';
import { RouteProp, useNavigation, useRoute } from '@react-navigation/native';
import { StackNavigationProp } from '@react-navigation/stack';
import { RootStackParamList } from '@/app/models/RootStackParams.types';
import { ErrorModal } from '@/app/components/ErrorModal'; 

type AddressScreenRouteProp = RouteProp<RootStackParamList, 'Address'>;
type AddressScreenNavigationProp = StackNavigationProp<RootStackParamList>;

export default function Address() {
  const navigation = useNavigation<AddressScreenNavigationProp>();
  const route = useRoute<AddressScreenRouteProp>();
  const personalData = route.params?.personalData;

  const [address, setAddress] = useState('');
  const [number, setNumber] = useState('');
  const [complement, setComplement] = useState('');
  const [neighborhood, setNeighborhood] = useState('');
  const [postal_code, setPostalCode] = useState('');
  const [city, setCity] = useState('');
  const [state, setState] = useState('');
  const [errors, setErrors] = useState<{ [key: string]: boolean }>({});
  const [errorModalVisible, setErrorModalVisible] = useState(false);
  const [errorModalMessage, setErrorModalMessage] = useState('');

  const validateFields = () => {
    const newErrors: { [key: string]: boolean } = {};
    if (!address) newErrors.address = true;
    if (!number || number.length > 6) newErrors.number = true;
    if (!neighborhood) newErrors.neighborhood = true;
    if (!postal_code) newErrors.postal_code = true;
    if (!city) newErrors.city = true;
    if (!state || state.length != 2) newErrors.state = true;
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const formatCEP = (value: string) => {
    return value
      .replace(/\D/g, '')                  
      .replace(/^(\d{5})(\d)/, '$1-$2')    
      .slice(0, 9);                        
  };

  const formatNumber = (value: string) => {
  return value.replace(/\D/g, '').slice(0, 6);
};


  const handleAddress = async () => {
    if (!validateFields()) {
      setErrorModalMessage('Por favor, corrija os campos destacados.');
      setErrorModalVisible(true);
      return;
    }

    const addressData = { address, number, complement, neighborhood, postal_code, city, state };
    navigation.navigate('Preferences', { personalData, addressData });
  };

  return (
    <ScrollView>
      <KeyboardAvoidingView style={styles.container}>
        <View style={styles.header}>
          <Image source={require('../../../assets/images/HairmatchLogo.png')} />
          <Text style={styles.subtitle}>Informe seu endereço</Text>
        </View>

        <View style={styles.form}>
          <View style={styles.row}>
            <TextInput
              placeholder="Endereço"
              style={[styles.input, { flex: 2, marginRight: 5 }, errors.address && styles.inputError]}
              value={address}
              onChangeText={setAddress}
            />
            <TextInput
              placeholder="Número"
              style={[styles.input, { flex: 1 }, errors.number && styles.inputError]}
              value={number}
              onChangeText={(text) => setNumber(formatNumber(text))}
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
              style={[styles.input, { flex: 1, marginRight: 5 }, errors.neighborhood && styles.inputError]}
              value={neighborhood}
              onChangeText={setNeighborhood}
            />
            <TextInput
              placeholder="CEP"
              style={[styles.input, { flex: 1 }, errors.postal_code && { borderColor: '#9B59B6', borderWidth: 2 }]}
              value={postal_code}
              onChangeText={(text) => setPostalCode(formatCEP(text))}
              keyboardType="numeric"
            />

          </View>

          <View style={styles.row}>
            <TextInput
              placeholder="Cidade"
              style={[styles.input, { flex: 2, marginRight: 5 }, errors.city && styles.inputError]}
              value={city}
              onChangeText={setCity}
            />
            <TextInput
              placeholder="UF"
              style={[styles.input, { flex: 1 }, errors.state && styles.inputError]}
              value={state}
              onChangeText={setState}
              maxLength={2}
            />
          </View>

          <View style={styles.buttonContainer}>
            <TouchableOpacity style={styles.backButton} onPress={() => navigation.goBack()}>
              <Text style={styles.backButtonText}>Voltar</Text>
            </TouchableOpacity>

            <TouchableOpacity style={styles.button} onPress={handleAddress}>
              <Text style={styles.buttonText}>Próximo</Text>
            </TouchableOpacity>
          </View>

          <ErrorModal
            visible={errorModalVisible}
            onClose={() => setErrorModalVisible(false)}
            message={errorModalMessage}
          />
        </View>
      </KeyboardAvoidingView>
    </ScrollView>
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
    borderWidth: 1,
    borderColor: '#ccc',
  },
  inputError: {
    borderWidth: 1.5,
    borderColor: 'purple',
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
