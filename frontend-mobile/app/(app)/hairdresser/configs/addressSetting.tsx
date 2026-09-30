import React from 'react';
import { View, Text, TextInput, TouchableOpacity, SafeAreaView, ScrollView } from 'react-native';
import { FormInput } from '@/components/formInputs/FormInput'; 
import { Ionicons } from '@expo/vector-icons';
import { useHairdresserProfile } from '@/hooks/hairdresserHooks/useHairdresserProfile';
import Icon from '@expo/vector-icons/FontAwesome';
import { styles } from '@/styles/customer/styles/AddressConfigStyles';
import { useAddress } from '@/hooks/authHooks/useAddress';

export default function AccountDetailsScreen() {
  const {hairdresser, handleGoBack} = useHairdresserProfile();
  //const {errors, errorModal} = useAddress();

  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity  onPress={handleGoBack}>
          <Ionicons name="chevron-back" size={24} color="#333" />
        </TouchableOpacity>
        <Text style={styles.buttonTitle}>Perfil</Text>
      </View>

      {/* 2. SCROLL AREA: Wraps only the content that needs to scroll */}
      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollViewContent}
        keyboardShouldPersistTaps="handled"
      >
        <View style={styles.header}>
        {/* Add the back icon if using react-navigation */}
        <Text style={styles.headerTitle}>Endereço</Text>
      </View>
        {/* The <View style={styles.form}> is now inside the ScrollView and WITHOUT flex:1 */}
        <View style={styles.form}>
          <View style={styles.row}>
            <TextInput
              placeholder="Endereço"
              style={[styles.input, { flex: 2, marginRight: 5 }]}
              value={hairdresser?.user?.address}
            />
            <TextInput
              placeholder="Número"
              style={[styles.input, { flex: 1 }]}
              value={hairdresser?.user?.number}
              keyboardType="numeric"
            />
          </View>
          <TextInput
            placeholder="Complemento"
            style={styles.input}
            value={hairdresser?.user?.complement}
          />
          <View style={styles.row}>
            <TextInput
              placeholder="Bairro"
              style={[styles.input, { flex: 1, marginRight: 5 }]}
              value={hairdresser?.user?.neighborhood}
            />
            <TextInput
              placeholder="CEP"
              style={[styles.input, { flex: 1 }]}
              value={hairdresser?.user?.postal_code}
              keyboardType="numeric"
              maxLength={9}
            />
          </View>
          <View style={styles.row}>
            <TextInput
              placeholder="Cidade"
              style={[styles.input, { flex: 2, marginRight: 5 }]}
              value={hairdresser?.user?.city}
            />
            <TextInput
              placeholder="UF"
              style={[styles.input, { flex: 1 }]}
              value={hairdresser?.user?.state}
              maxLength={2}
              autoCapitalize="characters"
            />
          </View>
        </View>

        {/* 3. SAVE BUTTON: Also inside the scroll, but flexGrow on the container will push it down */}
        <TouchableOpacity style={styles.saveButton}>
          <Text style={styles.saveButtonText}>Salvar</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}
