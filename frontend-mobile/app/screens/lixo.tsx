import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, ScrollView } from 'react-native';
import { useNavigation } from '@react-navigation/native';

const AddressScreen = () => {
  const navigation = useNavigation();

  const [endereco, setEndereco] = useState('');
  const [numero, setNumero] = useState('');
  const [complemento, setComplemento] = useState('');
  const [bairro, setBairro] = useState('');
  const [cep, setCep] = useState('');
  const [cidade, setCidade] = useState('');
  const [uf, setUf] = useState('');

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <TouchableOpacity style={styles.backArrow} onPress={() => navigation.goBack()}>
        <Text style={styles.arrow}>←</Text>
      </TouchableOpacity>

      <Text style={styles.title}>
        <Text style={styles.hair}>Hair</Text>
        <Text style={styles.match}>M✄tch</Text>
      </Text>

      <Text style={styles.subtitle}>Informações de Endereço</Text>

      <View style={styles.inputRow}>
        <TextInput
          style={[styles.input, { flex: 2 }]}
          placeholder="Endereço"
          value={endereco}
          onChangeText={setEndereco}
        />
        <TextInput
          style={[styles.input, { flex: 1, marginLeft: 8 }]}
          placeholder="Número"
          value={numero}
          onChangeText={setNumero}
        />
      </View>

      <TextInput
        style={styles.input}
        placeholder="Complemento"
        value={complemento}
        onChangeText={setComplemento}
      />

      <View style={styles.inputRow}>
        <TextInput
          style={[styles.input, { flex: 1, marginRight: 8 }]}
          placeholder="Bairro"
          value={bairro}
          onChangeText={setBairro}
        />
        <TextInput
          style={[styles.input, { flex: 1 }]}
          placeholder="CEP"
          value={cep}
          onChangeText={setCep}
        />
      </View>

      <View style={styles.inputRow}>
        <TextInput
          style={[styles.input, { flex: 1, marginRight: 8 }]}
          placeholder="Cidade"
          value={cidade}
          onChangeText={setCidade}
        />
        <TextInput
          style={[styles.input, { flex: 1 }]}
          placeholder="UF"
          value={uf}
          onChangeText={setUf}
        />
      </View>

      <View style={styles.buttonContainer}>
        <TouchableOpacity style={styles.backButton} onPress={() => navigation.goBack()}>
          <Text style={styles.backButtonText}>Voltar</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.nextButton} onPress={() => {/* Próxima ação aqui */}}>
          <Text style={styles.nextButtonText}>Próximo</Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
};

export default AddressScreen;

const styles = StyleSheet.create({
  container: {
    flexGrow: 1,
    backgroundColor: '#FFEFE6',
    padding: 20,
    alignItems: 'center',
  },
  backArrow: {
    position: 'absolute',
    top: 40,
    left: 20,
  },
  arrow: {
    fontSize: 30,
    color: '#000',
  },
  title: {
    fontSize: 32,
    fontWeight: 'bold',
    marginTop: 60,
    flexDirection: 'row',
    textAlign: 'center',
  },
  hair: {
    color: '#FF6600',
  },
  match: {
    color: '#9B59B6',
  },
  subtitle: {
    fontSize: 18,
    marginVertical: 20,
    textAlign: 'center',
    fontWeight: 'bold',
    color: '#333',
  },
  input: {
    borderWidth: 1,
    borderColor: '#ccc',
    backgroundColor: '#fff',
    padding: 12,
    marginVertical: 8,
    borderRadius: 8,
    width: '100%',
  },
  inputRow: {
    flexDirection: 'row',
    width: '100%',
    justifyContent: 'space-between',
  },
  buttonContainer: {
    flexDirection: 'row',
    marginTop: 20,
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
  nextButton: {
    backgroundColor: '#FF6600',
    padding: 14,
    borderRadius: 8,
    flex: 1,
    marginLeft: 8,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 3.84,
    elevation: 5,
  },
  nextButtonText: {
    color: '#fff',
    fontWeight: 'bold',
  },
});
