import React from 'react';
import { View, Text, TextInput, TouchableOpacity, SafeAreaView, ScrollView } from 'react-native';
import { FormInput } from '@/components/formInputs/FormInput'; 
import { Ionicons } from '@expo/vector-icons';
import { useHairdresserProfile } from '@/hooks/hairdresserHooks/useHairdresserProfile';
import Icon from 'react-native-vector-icons/FontAwesome'; // ou outra biblioteca de ícones
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

      {/* 2. ÁREA DE ROLAGEM: Envolve apenas o conteúdo que precisa rolar */}
      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollViewContent}
        keyboardShouldPersistTaps="handled"
      >
        <View style={styles.header}>
        {/* Adicione o ícone de voltar se estiver usando react-navigation */}
        <Text style={styles.headerTitle}>Endereço</Text>
      </View>
        {/* O <View style={styles.form}> agora está dentro do ScrollView e SEM flex:1 */}
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

        {/* 3. BOTÃO SALVAR: Também dentro do scroll, mas o flexGrow no container o empurrará para baixo */}
        <TouchableOpacity style={styles.saveButton}>
          <Text style={styles.saveButtonText}>Salvar</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}
