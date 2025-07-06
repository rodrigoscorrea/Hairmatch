import React from 'react';
import { View, Text, TouchableOpacity, SafeAreaView, ScrollView, Image } from 'react-native';
import { FormInput } from '@/components/formInputs/FormInput'; 
import { Ionicons } from '@expo/vector-icons';
import { useHairdresserProfile } from '@/hooks/hairdresserHooks/useHairdresserProfile';
import Icon from 'react-native-vector-icons/FontAwesome'; // ou outra biblioteca de ícones
import { styles } from '@/styles/customer/styles/AccountConfigStyles';
import { API_BACKEND_URL } from '@/app/_layout';

export default function AccountDetailsScreen() {
  const {hairdresser, handleGoBack} = useHairdresserProfile();

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
        <Image 
            source={
              hairdresser?.user?.profile_picture
                  ? { uri: `${API_BACKEND_URL}${hairdresser.user.profile_picture}` }
                  : require('../../../../assets/images/profile_picture_placeholder.png')
            }
            style={styles.profilePic}
            resizeMode="cover"
        />
      </View>

      <View style={styles.form}>
        <FormInput
          value={hairdresser?.user?.first_name}
          //onChangeText={setFirstName}
          placeholder="Nome"
          containerStyle={styles.inputContainer}
        />
        <FormInput
          value={hairdresser?.user?.last_name}
          //onChangeText={setLastName}
          placeholder="Sobrenome"
          containerStyle={styles.inputContainer}
        />
        <FormInput
          value={hairdresser?.cnpj}
          //onChangeText={setCpf}
          placeholder="CNPJ"
          keyboardType="numeric" // Facilita a digitação de números
          containerStyle={styles.inputContainer}
        />
        <FormInput
          value={hairdresser?.user?.email}
          //onChangeText={setEmail}
          placeholder="Email"
          keyboardType="email-address"
          autoCapitalize="none"
          containerStyle={styles.inputContainer}
        />
        <FormInput
          value={hairdresser?.user?.phone}
          //onChangeText={setPhone}
          placeholder="+55 (DDD)"
          keyboardType="phone-pad"
          containerStyle={styles.inputContainer}
        />
        <FormInput
          value={hairdresser?.user?.password}
          //onChangeText={setPassword}
          placeholder="Senha"
          secureTextEntry // Oculta o texto da senha
          containerStyle={styles.inputContainer}
        />
        <FormInput
          value={hairdresser?.user?.confirmPassword}
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
