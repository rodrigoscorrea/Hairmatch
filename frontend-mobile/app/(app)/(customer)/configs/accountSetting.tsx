import React from 'react';
import { View, Text, TouchableOpacity, SafeAreaView, ScrollView } from 'react-native';
import { FormInput } from '@/components/formInputs/FormInput'; 
import { Ionicons } from '@expo/vector-icons';
import { useCustomerProfile } from "@/hooks/customerHooks/useCustomerProfile"; // <-- Our new hook
import Icon from 'react-native-vector-icons/FontAwesome'; // ou outra biblioteca de ícones
import { styles } from '@/styles/customer/styles/AccountConfigStyles';

export default function AccountDetailsScreen() {
  const {customer, handleGoBack} = useCustomerProfile();

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
        <View style={styles.profilePic}>
          <Icon name="camera" size={40} color="#888" />
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
