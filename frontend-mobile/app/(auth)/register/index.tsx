import React from 'react';
import { View, Text, TouchableOpacity, Image, ScrollView, TextInput } from 'react-native'; // TextInput importado de 'react-native'
import { styles } from '../../../styles/register/styles/RegisterStyle'
import { UserRole } from '@/app/../models/User.types';
import { Ionicons } from '@expo/vector-icons';
import { ErrorModal } from '@/app/../components/modals/ErrorModal/ErrorModal';
import { useRegisterForm } from '@/hooks/authHooks/useRegisterForm';
import { formatCPF, formatCNPJ, formatPhone } from '@/app/../utils/forms';
import { useRegistration } from '@/contexts/RegistrationContext';

export default function RegisterScreen() {
  const { registrationData, setRegistrationData } = useRegistration();
  const {
    handleInputChange,
    profileImage, 
    handlePickImage,
    role,
    setRole,
    errors,
    handleRegister,
    handleGoBack, 
    errorModal,
    closeErrorModal,
    passwordVisibility,
    confirmPasswordVisibility,
  } = useRegisterForm();


  return (
    <ScrollView>
      <View style={styles.container}>
      <TouchableOpacity style={styles.backButton} onPress={handleGoBack}>
        <Text style={styles.backButtonText}>←</Text>
      </TouchableOpacity>

      <View style={styles.title}>
        <Image source={require('../../../assets/images/HairmatchLogo.png')}></Image>
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

      <TouchableOpacity 
          onPress={handlePickImage} 
          style={{ alignItems: 'center', marginVertical: 20 }}
      >
          {profileImage ? (
              <Image 
                  source={{ uri: profileImage }} 
                  style={{ width: 120, height: 120, borderRadius: 60 }} 
              />
          ) : (
              <View style={{
                  width: 120, 
                  height: 120, 
                  borderRadius: 60, 
                  backgroundColor: '#e1e1e1',
                  justifyContent: 'center',
                  alignItems: 'center'
              }}>
                  <Text>Adicione uma foto de perfil</Text>
              </View>
          )}
      </TouchableOpacity>

      <View style={styles.row}>
        <TextInput
          placeholder="Nome"
          style={[styles.input, { flex: 1, marginRight: 5 }, errors.first_name && styles.inputError]}
          value={registrationData.first_name}
          onChangeText={text => handleInputChange('first_name', text)}
        />
        <TextInput
          placeholder="Sobrenome"
          style={[styles.input, { flex: 1, marginLeft: 5 }, errors.last_name && styles.inputError]}
          value={registrationData.last_name}
          onChangeText={text => handleInputChange('last_name', text)}
        />
      </View>

      {role === UserRole.CUSTOMER ? (
        <TextInput
          placeholder="CPF"
          style={[styles.input, errors.cpf && styles.inputError]}
          value={registrationData.cpf}
          maxLength={14}
          keyboardType="numeric"
          onChangeText={(text) => handleInputChange('cpf', formatCPF(text))}
        />
      ): (
        <TextInput
          placeholder="CNPJ"
          style={[styles.input, errors.cnpj && styles.inputError]}
          value={registrationData.cnpj}
          maxLength={18}
          keyboardType="numeric"
          onChangeText={text => handleInputChange('cnpj', formatCNPJ(text))}
      />
      )}      

      <TextInput
        placeholder="Email"
        style={[styles.input, errors.email && styles.inputError]}
        keyboardType="email-address"
        autoCapitalize="none"
        value={registrationData.email}
        onChangeText={text => handleInputChange('email', text)}
      />
      <TextInput
        placeholder="Telefone"
        style={[styles.input, errors.phone && styles.inputError]}
        keyboardType="phone-pad"
        value={registrationData.phone}
        onChangeText={text => handleInputChange('phone', formatPhone(text))}
      />

      <View style={[styles.passwordContainer, errors.password && styles.inputError]}>
        <TextInput
          placeholder="Senha"
          style={styles.inputInner}
          value={registrationData.password}
          onChangeText={text => handleInputChange('password', text)}
          secureTextEntry={!passwordVisibility.showPassword}
        />
        <TouchableOpacity onPress={passwordVisibility.toggle} style={styles.eyeIconAbsolute}>
            <Ionicons
              name={passwordVisibility.showPassword ? 'eye' : 'eye-off'}
              size={24}
              color="#888"
            />
        </TouchableOpacity>
      </View>

      <View style={[styles.passwordContainer, errors.confirmPassword && styles.inputError]}>
        <TextInput
          placeholder="Confirme sua senha"
          style={styles.inputInner}
          secureTextEntry={!confirmPasswordVisibility.showConfirmPassword}
          value={registrationData.confirmPassword}
          onChangeText={text => handleInputChange('confirmPassword', text)}
        />
        <TouchableOpacity onPress={confirmPasswordVisibility.toggle} style={styles.eyeIconAbsolute}>
            <Ionicons
              name={confirmPasswordVisibility.showConfirmPassword ? 'eye' : 'eye-off'}
              size={24}
              color="#888"
            />
        </TouchableOpacity>
      </View>

      <TouchableOpacity style={styles.button} onPress={handleRegister}>
        <Text style={styles.buttonText}>Próximo</Text>
      </TouchableOpacity>
      </View>
      <ErrorModal
        visible={errorModal.visible}
        message={errorModal.message}
        onClose={closeErrorModal}
      />
    </ScrollView>
  );
}

