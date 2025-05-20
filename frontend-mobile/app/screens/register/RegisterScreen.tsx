import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, Image, Alert, ScrollView } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { UserRole } from '@/app/models/User.types';
import { ErrorModal } from '@/app/components/ErrorModal'; 


export default function RegisterScreen() {
  const navigation = useNavigation<any>();

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
  const [errors, setErrors] = useState<{ [key: string]: boolean }>({});
  const [errorModalVisible, setErrorModalVisible] = useState(false);
  const [errorModalMessage, setErrorModalMessage] = useState('');


  const formatCPF = (value: string) => {
    const digits = value.replace(/\D/g, '').slice(0, 11); 
  
    if (digits.length <= 3) return digits;
    if (digits.length <= 6) return `${digits.slice(0, 3)}.${digits.slice(3)}`;
    if (digits.length <= 9) return `${digits.slice(0, 3)}.${digits.slice(3, 6)}.${digits.slice(6)}`;
    return `${digits.slice(0, 3)}.${digits.slice(3, 6)}.${digits.slice(6, 9)}-${digits.slice(9)}`;
  };
  
  
  const formatCNPJ = (value: string) => {
    return value
      .replace(/\D/g, '')
      .replace(/^(\d{2})(\d)/, '$1.$2')
      .replace(/^(\d{2})\.(\d{3})(\d)/, '$1.$2.$3')
      .replace(/\.(\d{3})(\d)/, '.$1/$2')
      .replace(/(\d{4})(\d)/, '$1-$2')
      .slice(0, 14);
  };
  
  const formatPhone = (value: string) => {
    return value
      .replace(/\D/g, '')
      .replace(/^(\d{2})(\d)/, '($1)$2')
      .replace(/(\d{5})(\d)/, '$1-$2')
      .slice(0, 14); 
  };

  const isValidEmail = (email: string): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email.trim());
  };
  
  const stripNonDigits = (value: string) => value.replace(/\D/g, '');

  const validateFields = () => {
    const newErrors: { [key: string]: boolean } = {};

    if (!first_name) newErrors.first_name = true;
    if (!last_name) newErrors.last_name = true;
    if ((!isValidEmail(email)) || (!email) ) {
      newErrors.email = true;
    }
    if (!phone) newErrors.phone = true;
    if (!password) newErrors.password = true;
    if (!confirmPassword) newErrors.confirmPassword = true;
    if (password !== confirmPassword) {
      newErrors.password = true;
      newErrors.confirmPassword = true;
    }
    if (role === UserRole.CUSTOMER && !cpf) newErrors.cpf = true;
    if (role === UserRole.HAIRDRESSER && !cnpj) newErrors.cnpj = true;

    const sanitizedCpf = stripNonDigits(cpf);
    const sanitizedCnpj = stripNonDigits(cnpj);
    const sanitizedPhone = stripNonDigits(phone);

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleRegister = async () => {
    if (!validateFields()) {
      setErrorModalMessage('Por favor, corrija os campos destacados.');
      setErrorModalVisible(true);
      return;
    }

    navigation?.navigate('Address', {
      personalData: {
        first_name,
        last_name,
        phone,
        email,
        cnpj: cnpj ?? '',
        cpf: cpf ?? '',
        password,
        role,
      },
    });
  };

  return (
    <ScrollView>
      <View style={styles.container}>
        <TouchableOpacity style={styles.backButton} onPress={() => navigation.goBack()}>
          <Text style={styles.backButtonText}>←</Text>
        </TouchableOpacity>

        <View style={styles.title}>
          <Image source={require('../../../assets/images/HairmatchLogo.png')} />
        </View>
        <Text style={styles.subtitle}>Cadastre-se</Text>

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
              role === UserRole.HAIRDRESSER && styles.toggleButtonSelected,
            ]}
            onPress={() => setRole(UserRole.HAIRDRESSER)}
          >
            <Text style={role === UserRole.HAIRDRESSER ? styles.toggleButtonTextSelected : styles.toggleButtonText}>
              Profissional
            </Text>
          </TouchableOpacity>
        </View>

        <TouchableOpacity style={styles.profilePicture}>
          <Image
            source={require('../../../imgs/Camera.png')}
            style={styles.profileIcon}
          />
        </TouchableOpacity>

        <View style={styles.row}>
          <TextInput
            placeholder="Nome"
            style={[styles.input, { flex: 1, marginRight: 5 }, errors.first_name && styles.inputError]}
            value={first_name}
            onChangeText={text => {
              setFirst_Name(text);
              setErrors(prev => ({ ...prev, first_name: false }));
            }}
          />
          <TextInput
            placeholder="Sobrenome"
            style={[styles.input, { flex: 1, marginLeft: 5 }, errors.last_name && styles.inputError]}
            value={last_name}
            onChangeText={text => {
              setLast_Name(text);
              setErrors(prev => ({ ...prev, last_name: false }));
            }}
          />
        </View>

        {role === UserRole.CUSTOMER ? (
          <TextInput
            placeholder="CPF"
            style={[styles.input, errors.cpf && styles.inputError]}
            value={cpf}
            keyboardType="numeric"
            onChangeText={(text) => setCpf(formatCPF(text))}
          />
        ) : (
          <TextInput
            placeholder="CNPJ"
            style={[styles.input, errors.cnpj && styles.inputError]}
            value={cnpj}
            keyboardType="numeric"
            onChangeText={(text) => setCnpj(formatCNPJ(text))}
          />
        )}

        <TextInput
          placeholder="Email"
          style={[styles.input, errors.email && styles.inputError]}
          keyboardType="email-address"
          autoCapitalize="none"
          value={email}
          onChangeText={text => {
            setEmail(text);
            setErrors(prev => ({ ...prev, email: false }));
          }}
        />

        <TextInput
          placeholder="Telefone"
          style={[styles.input, errors.phone && styles.inputError]}
          keyboardType="phone-pad"
          value={phone}
          onChangeText={(text) => setPhone(formatPhone(text))}
        />

        <TextInput
          placeholder="Senha"
          style={[styles.input, errors.password && styles.inputError]}
          secureTextEntry
          value={password}
          onChangeText={text => {
            setPassword(text);
            setErrors(prev => ({ ...prev, password: false }));
          }}
        />

        <TextInput
          placeholder="Confirme sua senha"
          style={[styles.input, errors.confirmPassword && styles.inputError]}
          secureTextEntry
          value={confirmPassword}
          onChangeText={text => {
            setConfirmPassword(text);
            setErrors(prev => ({ ...prev, confirmPassword: false }));
          }}
        />

        <TouchableOpacity style={styles.button} onPress={handleRegister}>
          <Text style={styles.buttonText}>Próximo</Text>
        </TouchableOpacity>
      </View>
      <ErrorModal
        visible={errorModalVisible}
        onClose={() => setErrorModalVisible(false)}
        message={errorModalMessage}
      />
    </ScrollView>
    
  );
}

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
    backgroundColor: '#8e44ad',
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
    tintColor: '#000',
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
  inputError: {
    borderWidth: 1.5,
    borderColor: 'purple',
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
