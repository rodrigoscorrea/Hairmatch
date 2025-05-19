import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, Image, Alert, ScrollView } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { UserRole } from '@/app/models/User.types';

export default function RegisterScreen() {
  const navigation = useNavigation<any>();

  // Estados para armazenar os campos
  const [first_name, setFirst_Name] = useState<string>('');
  const [last_name, setLast_Name] = useState<string>('');
  const [cpf, setCpf] = useState<string>('');
  const [cnpj, setCnpj] = useState<string>('');
  const [email, setEmail] = useState<string>('');
  const [phone, setPhone] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [confirmPassword, setConfirmPassword] = useState<string>('');
  const [role, setRole] = useState<UserRole>(UserRole.CUSTOMER);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  return (
    <ScrollView>
      <View style={styles.container}>
      {/* Botão de Voltar */}
      <TouchableOpacity style={styles.backButton} onPress={() => navigation.goBack()}>
        <Text style={styles.backButtonText}>←</Text>
      </TouchableOpacity>

      <View style={styles.title}>
        <Image source={require('../../../assets/images/HairmatchLogo.png')}></Image>
      </View>
      <Text style={styles.subtitle}>Cadastre-se</Text>

      {/* Botões Cliente / Profissional */}
      <View style={styles.toggleContainer}>
        <TouchableOpacity
          style={[
            styles.toggleButton,
            role === UserRole.CUSTOMER && styles.toggleButtonSelected,
          ]}
          onPress={() => setRole(UserRole.CUSTOMER)}
        >
          <Text style={role === UserRole.CUSTOMER ? styles.toggleButtonTextSelected : styles.toggleButtonText}>
            Cliente
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[
            styles.toggleButton,
            role === UserRole.HAIRDRESSER && styles.toggleButtonSelected, // Ambos ficam roxos
          ]}
          onPress={() => setRole(UserRole.HAIRDRESSER)}
        >
          <Text style={role === UserRole.HAIRDRESSER ? styles.toggleButtonTextSelected : styles.toggleButtonText}>
            Profissional
          </Text>
        </TouchableOpacity>
      </View>

      {/* Ícone de foto */}
      <TouchableOpacity style={styles.profilePicture}>
        <Image
          source={require('../../../imgs/Camera.png')} // Substitua pelo caminho correto da imagem
          style={styles.profileIcon}
        />
      </TouchableOpacity>

      {/* Formulário */}
      <View style={styles.row}>
        <TextInput
          placeholder="Nome"
          style={[styles.input, { flex: 1, marginRight: 5 }]}
          value={first_name}
          onChangeText={setFirst_Name}
        />
        <TextInput
          placeholder="Sobrenome"
          style={[styles.input, { flex: 1, marginLeft: 5 }]}
          value={last_name}
          onChangeText={setLast_Name}
        />
      </View>

      {role === 'customer' ? (
        <TextInput
        placeholder="CPF"
        style={styles.input}
        value={cpf}
        onChangeText={setCpf}
        />
      ): (
        <TextInput
        placeholder="CNPJ"
        style={styles.input}
        value={cnpj}
        onChangeText={setCnpj}
      />
      )}      

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
        value={phone}
        onChangeText={setPhone}
      />

      <TextInput
        placeholder="Senha"
        style={styles.input}
        secureTextEntry
        value={password}
        onChangeText={setPassword}
      />

      <TextInput
        placeholder="Confirme sua senha"
        style={styles.input}
        secureTextEntry
        value={confirmPassword}
        onChangeText={setConfirmPassword}
      />

      {/* Botão Próximo */}
      <TouchableOpacity style={styles.button} onPress={() => navigation?.navigate('Address', {personalData: {
        first_name: first_name,
        last_name: last_name,
        phone: phone,
        email: email,
        cnpj: cnpj ?? '',
        cpf: cpf ?? '',
        password: password,
        role: role,
      }})}>
        <Text style={styles.buttonText}>Próximo</Text>
      </TouchableOpacity>
      </View>
    </ScrollView>
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