import React from 'react';
import { View, Text, TouchableOpacity, SafeAreaView, ScrollView, Image } from 'react-native';
import { FormInput } from '@/components/formInputs/FormInput'; 
import { Ionicons } from '@expo/vector-icons';
import { useCustomerProfile } from "@/hooks/customerHooks/useCustomerProfile";
import Icon from 'react-native-vector-icons/FontAwesome';
import { styles } from '@/styles/customer/styles/AccountConfigStyles';
import { API_BACKEND_URL } from '@/app/_layout';

export default function AccountDetailsScreen() {
  const {customer, handleGoBack} = useCustomerProfile();
  const customer_image = `${API_BACKEND_URL}${customer.user.profile_picture}`;
  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity  onPress={handleGoBack}>
          <Ionicons name="chevron-back" size={24} color="#333" />
        </TouchableOpacity>
        <Text style={styles.buttonTitle}>Perfil</Text>
      </View>
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        {/* Adicione o ícone de voltar se estiver usando react-navigation */}
        <Text style={styles.headerTitle}>Dados da Conta</Text>
      </View>

      <View style={styles.profilePicContainer}>
        <View>
          <Image 
            source={
              customer?.user?.profile_picture
                  ? { uri: customer_image }
                  : require('../../../../assets/images/profile_picture_placeholder.png')
            }
            style={styles.profilePic}
            resizeMode="cover"
          />
        </View>
      </View>

      <View style={styles.form}>
        <FormInput
          value={customer?.user?.first_name}
          //onChangeText={setFirstName}
          placeholder="Nome"
          containerStyle={styles.inputContainer}
        />
        <FormInput
          value={customer?.user?.last_name}
          //onChangeText={setLastName}
          placeholder="Sobrenome"
          containerStyle={styles.inputContainer}
        />
        <FormInput
          value={customer?.cpf}
          //onChangeText={setCpf}
          placeholder="CPF/CNPJ"
          keyboardType="numeric" // Facilita a digitação de números
          containerStyle={styles.inputContainer}
        />
        <FormInput
          value={customer?.user?.email}
          //onChangeText={setEmail}
          placeholder="Email"
          keyboardType="email-address"
          autoCapitalize="none"
          containerStyle={styles.inputContainer}
        />
        <FormInput
          value={customer?.user?.phone}
          //onChangeText={setPhone}
          placeholder="+55 (DDD)"
          keyboardType="phone-pad"
          containerStyle={styles.inputContainer}
        />
        <FormInput
          value={customer?.user?.password}
          //onChangeText={setPassword}
          placeholder="Senha"
          secureTextEntry // Oculta o texto da senha
          containerStyle={styles.inputContainer}
        />
        <FormInput
          value={customer?.user?.confirmPassword}
          //onChangeText={setConfirmPassword}
          placeholder="Confirme sua senha"
          secureTextEntry
          containerStyle={styles.inputContainer}
        />
      </View>

      <TouchableOpacity style={styles.saveButton} /*onPress={handleSaveChanges}*/>
        <Text style={styles.saveButtonText}>Salvar</Text>
      </TouchableOpacity>
    </ScrollView>
    </SafeAreaView>
  );
}
