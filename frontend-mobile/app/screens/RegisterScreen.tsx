import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, Image } from 'react-native';
import { useNavigation } from '@react-navigation/native';

export default function RegisterScreen() {
  const navigation = useNavigation<any>();

  // Estados para armazenar os campos
  const [nome, setNome] = useState('');
  const [sobrenome, setSobrenome] = useState('');
  const [cpfCnpj, setCpfCnpj] = useState('');
  const [email, setEmail] = useState('');
  const [telefone, setTelefone] = useState('');
  const [senha, setSenha] = useState('');
  const [confirmarSenha, setConfirmarSenha] = useState('');
  const [tipoUsuario, setTipoUsuario] = useState<'Cliente' | 'Profissional'>('Cliente');

  const handleProximo = () => {
    console.log('Dados preenchidos:');
    console.log({ nome, sobrenome, cpfCnpj, email, telefone, senha, confirmarSenha, tipoUsuario });
  };

  return (
    <View style={styles.container}>
      {/* Botão de Voltar */}
      <TouchableOpacity style={styles.backButton} onPress={() => navigation.goBack()}>
        <Text style={styles.backButtonText}>←</Text>
      </TouchableOpacity>

      <Text style={styles.title}>HairMatch</Text>
      <Text style={styles.subtitle}>Cadastre-se</Text>

      {/* Botões Cliente / Profissional */}
      <View style={styles.toggleContainer}>
        <TouchableOpacity
          style={[
            styles.toggleButton,
            tipoUsuario === 'Cliente' && styles.toggleButtonSelected,
          ]}
          onPress={() => setTipoUsuario('Cliente')}
        >
          <Text style={tipoUsuario === 'Cliente' ? styles.toggleButtonTextSelected : styles.toggleButtonText}>
            Cliente
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[
            styles.toggleButton,
            tipoUsuario === 'Profissional' && styles.toggleButtonSelected, // Ambos ficam roxos
          ]}
          onPress={() => setTipoUsuario('Profissional')}
        >
          <Text style={tipoUsuario === 'Profissional' ? styles.toggleButtonTextSelected : styles.toggleButtonText}>
            Profissional
          </Text>
        </TouchableOpacity>
      </View>

      {/* Ícone de foto */}
      <TouchableOpacity style={styles.profilePicture}>
        <Image
          source={require('../../imgs/Camera.png')} // Substitua pelo caminho correto da imagem
          style={styles.profileIcon}
        />
      </TouchableOpacity>

      {/* Formulário */}
      <View style={styles.row}>
        <TextInput
          placeholder="Nome"
          style={[styles.input, { flex: 1, marginRight: 5 }]}
          value={nome}
          onChangeText={setNome}
        />
        <TextInput
          placeholder="Sobrenome"
          style={[styles.input, { flex: 1, marginLeft: 5 }]}
          value={sobrenome}
          onChangeText={setSobrenome}
        />
      </View>

      <TextInput
        placeholder="CPF/CNPJ"
        style={styles.input}
        value={cpfCnpj}
        onChangeText={setCpfCnpj}
      />

      <TextInput
        placeholder="Email"
        style={styles.input}
        keyboardType="email-address"
        autoCapitalize="none"
        value={email}
        onChangeText={setEmail}
      />

      <TextInput
        placeholder="Telefone"
        style={styles.input}
        keyboardType="phone-pad"
        value={telefone}
        onChangeText={setTelefone}
      />

      <TextInput
        placeholder="Senha"
        style={styles.input}
        secureTextEntry
        value={senha}
        onChangeText={setSenha}
      />

      <TextInput
        placeholder="Confirme sua senha"
        style={styles.input}
        secureTextEntry
        value={confirmarSenha}
        onChangeText={setConfirmarSenha}
      />

      {/* Botão Próximo */}
      <TouchableOpacity style={styles.button} onPress={() => navigation?.navigate('Address')}>
        <Text style={styles.buttonText}>Próximo</Text>
      </TouchableOpacity>
    </View>
  );
}

// Estilos
const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FFECE3',
    alignItems: 'center',
    padding: 20,
  },
  backButton: {
    position: 'absolute',
    top: 20,
    left: 20,
    zIndex: 1,
  },
  backButtonText: {
    fontSize: 32,
    color: '#000',
  },
  title: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#FF6B00',
    marginTop: 40,
  },
  subtitle: {
    fontSize: 20,
    marginVertical: 10,
  },
  toggleContainer: {
    flexDirection: 'row',
    backgroundColor: '#F8DFF2',
    borderRadius: 20,
    marginVertical: 15,
  },
  toggleButton: {
    paddingVertical: 8,
    paddingHorizontal: 20,
    borderRadius: 20,
  },
  toggleButtonSelected: {
    backgroundColor: '#8e44ad',  // Roxo para ambos os botões
  },
  toggleButtonText: {
    color: '#555',
    fontWeight: '600',
  },
  toggleButtonTextSelected: {
    color: 'white',
    fontWeight: '700',
  },
  profilePicture: {
    width: 100,
    height: 100,
    borderRadius: 50,
    borderWidth: 1,
    borderColor: '#000000',
    justifyContent: 'center',
    alignItems: 'center',
    marginVertical: 15,
  },
  profileIcon: {
    width: 40,
    height: 40,
    tintColor: '#000', // Agora a câmera é preta
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
  button: {
    backgroundColor: '#FF6B00',
    borderRadius: 10,
    marginTop: 20,
    width: '100%',
    padding: 15,
    alignItems: 'center',
  },
  buttonText: {
    color: 'white',
    fontWeight: '700',
    fontSize: 16,
  },
});
