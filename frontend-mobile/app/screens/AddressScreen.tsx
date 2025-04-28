import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, KeyboardAvoidingView, Platform } from 'react-native';
import { useNavigation } from '@react-navigation/native';

export default function Address() {
  const navigation = useNavigation();

  const [endereco, setEndereco] = useState('');
  const [numero, setNumero] = useState('');
  const [complemento, setComplemento] = useState('');
  const [bairro, setBairro] = useState('');
  const [cep, setCep] = useState('');
  const [cidade, setCidade] = useState('');
  const [uf, setUf] = useState('');

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
            value={endereco}
            onChangeText={setEndereco}
          />
          <TextInput
            placeholder="Número"
            style={[styles.input, { flex: 1 }]}
            value={numero}
            onChangeText={setNumero}
          />
        </View>

        <TextInput
          placeholder="Complemento"
          style={styles.input}
          value={complemento}
          onChangeText={setComplemento}
        />

        <View style={styles.row}>
          <TextInput
            placeholder="Bairro"
            style={[styles.input, { flex: 1, marginRight: 5 }]}
            value={bairro}
            onChangeText={setBairro}
          />
          <TextInput
            placeholder="CEP"
            style={[styles.input, { flex: 1 }]}
            value={cep}
            onChangeText={setCep}
            keyboardType="numeric"
          />
        </View>

        <View style={styles.row}>
          <TextInput
            placeholder="Cidade"
            style={[styles.input, { flex: 2, marginRight: 5 }]}
            value={cidade}
            onChangeText={setCidade}
          />
          <TextInput
            placeholder="UF"
            style={[styles.input, { flex: 1 }]}
            value={uf}
            onChangeText={setUf}
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
          <TouchableOpacity style={styles.button} onPress={() => {/* ação ao confirmar */}}>
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
