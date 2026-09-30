import React from 'react';
import { View, Text, TouchableOpacity, ScrollView, Image } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { FormInput } from '@/components/formInputs/FormInput'; 
import { Ionicons } from '@expo/vector-icons';
import { useHairdresserProfile } from '@/hooks/hairdresserHooks/useHairdresserProfile';
import Icon from '@expo/vector-icons/FontAwesome';
import { styles } from '@/styles/customer/styles/AccountConfigStyles';

export default function AccountDetailsScreen() {
  const {hairdresser, handleGoBack} = useHairdresserProfile();
  const hairdresser_image = hairdresser.user.profile_picture;
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
        {/* Add the back icon if using react-navigation */}
        <Text style={styles.headerTitle}>Dados da Conta</Text>
      </View>

      <View style={styles.profilePicContainer}>
        <Image 
            source={
              hairdresser?.user?.profile_picture
                  ? { uri: hairdresser_image }
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
          keyboardType="numeric" // Makes it easier to type numbers
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
          secureTextEntry // Hides the password text
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
