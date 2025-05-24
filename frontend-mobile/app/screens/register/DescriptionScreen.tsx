import React, { useState, useContext } from 'react';
import { View, Text, TextInput, StyleSheet, TouchableOpacity, ScrollView, Alert } from 'react-native';
import { RouteProp, useNavigation, useRoute } from '@react-navigation/native';
import { StackNavigationProp } from '@react-navigation/stack';
import { RootStackParamList } from '@/app/models/RootStackParams.types';
import { AuthContext } from '../../index';

type DescriptionScreenRouteProp = RouteProp<RootStackParamList, 'Description'>;
type DescriptionScreenNavigationProp = StackNavigationProp<RootStackParamList>;

const DescriptionScreen = () => {
  const [resume, setResume] = useState('');
  const navigation = useNavigation<DescriptionScreenNavigationProp>();
  const route = useRoute<DescriptionScreenRouteProp>();
  const { personalData, addressData, preferences, professionalStory } = route.params;
  const { signUp } = useContext<any>(AuthContext);

  const handleBack = () => {
    navigation.navigate('ProfessionalStory', {personalData, addressData, preferences})
  };

  const handleFinish = async () => {
    try {
      const { first_name, last_name, phone, email, password, role, cpf, cnpj } = personalData;
      const { address, number, complement, neighborhood, postal_code, city, state } = addressData;
      const { experience_time, experiences, products } = professionalStory

      await signUp(
        first_name, 
        last_name,
        phone, 
        email, 
        password, 
        address, 
        number,
        neighborhood, 
        complement, 
        postal_code, 
        state, 
        city, 
        role, 
        5.0,
        cpf, 
        cnpj,
        preferences,
        experience_time,
        experiences,
        products,
        resume
      );
      Alert.alert(
        'Sucesso', 
        'Cadastro realizado com sucesso! Faça login para continuar.',
        [{ text: 'OK', onPress: () => navigation.navigate('Login') }]
      );
    } catch (error) {
      console.log('error', error);
    }
    console.log({personalData, addressData, preferences, professionalStory});
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>Descrição Profissional</Text>
      <Text style={styles.subtitle}>Esse texto será a descrição do seu perfil</Text>

      <TextInput
        style={styles.textArea}
        placeholder="Insira aqui a sua descrição detalhada para que atraia mais clientes"
        placeholderTextColor="#aaa"
        multiline
        value={resume}
        onChangeText={setResume}
      />

      <View style={styles.buttonContainer}>
        <TouchableOpacity style={styles.backButton} onPress={handleBack}>
          <Text style={styles.backText}>Voltar</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.finishButton} onPress={handleFinish}>
          <Text style={styles.finishText}>Finalizar</Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
};

export default DescriptionScreen;

const styles = StyleSheet.create({
  container: {
    padding: 20,
    backgroundColor: '#FFEFE5',
    flexGrow: 1,
    justifyContent: 'flex-start',
  },
  title: {
    fontSize: 16,
    fontWeight: '600',
    textAlign: 'center',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 12,
    textAlign: 'center',
    color: '#555',
    marginBottom: 24,
  },
  textArea: {
    height: 200,
    backgroundColor: '#fff',
    borderRadius: 10,
    padding: 12,
    textAlignVertical: 'top',
    borderColor: '#ddd',
    borderWidth: 1,
    fontSize: 14,
  },
  buttonContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 30,
  },
  backButton: {
    backgroundColor: '#E5E0F8',
    paddingVertical: 12,
    paddingHorizontal: 24,
    borderRadius: 8,
  },
  finishButton: {
    backgroundColor: '#FF7A00',
    paddingVertical: 12,
    paddingHorizontal: 24,
    borderRadius: 8,
  },
  backText: {
    color: '#4B0082',
    fontWeight: '600',
  },
  finishText: {
    color: '#fff',
    fontWeight: '600',
  },
});
