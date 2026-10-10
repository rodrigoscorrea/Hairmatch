import React from 'react';
import { View, Text, TextInput, TouchableOpacity, ScrollView, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { ErrorModal } from '@/components/modals/ErrorModal/ErrorModal';
import { useAddressForm } from '@/hooks/accountHooks/useAddressForm';
import { styles } from '@/styles/customer/styles/AddressConfigStyles';
import { styles as registerStyles } from '@/styles/register/styles/AdressStyle';

// Where each role's settings menu lives.
const SETTINGS_ROUTE = {
  customer: '/(app)/customer/profile',
  hairdresser: '/(app)/hairdresser/profile/settings',
} as const;

// The same fields and CEP behavior as the sign-up address step (register/address.tsx).
export function AddressSettingScreen({ role }: { role: 'customer' | 'hairdresser' }) {
  const router = useRouter();
  const {
    values,
    errors,
    handleInputChange,
    handlePostalCodeChange,
    cepLoading,
    cepMessage,
    numberInputRef,
    addressUnlocked,
    saving,
    modal,
    handleSave,
    closeModal,
  } = useAddressForm();
  const locked = !addressUnlocked && registerStyles.inputDisabled;

  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.push(SETTINGS_ROUTE[role])}>
          <Ionicons name="chevron-back" size={24} color="#333" />
        </TouchableOpacity>
        <Text style={styles.buttonTitle}>Perfil</Text>
      </View>

      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollViewContent}
        keyboardShouldPersistTaps="handled"
      >
        <View style={styles.header}>
          <Text style={styles.headerTitle}>Endereço</Text>
        </View>
        <View style={styles.form}>
          <View style={styles.row}>
            <TextInput
              placeholder="CEP"
              style={[styles.input, { flex: 1 }, errors.postal_code && registerStyles.inputError]}
              value={values.postal_code}
              onChangeText={handlePostalCodeChange}
              keyboardType="numeric"
              maxLength={9}
            />
            {cepLoading && <ActivityIndicator style={registerStyles.cepSpinner} />}
          </View>
          {!!cepMessage && <Text style={registerStyles.cepHint}>{cepMessage}</Text>}
          <View style={styles.row}>
            <TextInput
              editable={addressUnlocked}
              placeholder="Endereço"
              style={[styles.input, { flex: 2, marginRight: 5 }, errors.address && registerStyles.inputError, locked]}
              value={values.address}
              onChangeText={text => handleInputChange('address', text)}
            />
            <TextInput
              ref={numberInputRef}
              editable={addressUnlocked}
              placeholder="Número"
              style={[styles.input, { flex: 1 }, errors.number && registerStyles.inputError, locked]}
              value={values.number}
              onChangeText={text => handleInputChange('number', text)}
              keyboardType="numeric"
            />
          </View>
          <TextInput
            editable={addressUnlocked}
            placeholder="Complemento"
            style={[styles.input, errors.complement && registerStyles.inputError, locked]}
            value={values.complement}
            onChangeText={text => handleInputChange('complement', text)}
          />
          <TextInput
            editable={addressUnlocked}
            placeholder="Bairro"
            style={[styles.input, errors.neighborhood && registerStyles.inputError, locked]}
            value={values.neighborhood}
            onChangeText={text => handleInputChange('neighborhood', text)}
          />
          <View style={styles.row}>
            <TextInput
              editable={addressUnlocked}
              placeholder="Cidade"
              style={[styles.input, { flex: 2, marginRight: 5 }, errors.city && registerStyles.inputError, locked]}
              value={values.city}
              onChangeText={text => handleInputChange('city', text)}
            />
            <TextInput
              editable={addressUnlocked}
              placeholder="UF"
              style={[styles.input, { flex: 1 }, errors.state && registerStyles.inputError, locked]}
              value={values.state}
              onChangeText={text => handleInputChange('state', text)}
              maxLength={2}
              autoCapitalize="characters"
            />
          </View>
        </View>

        <TouchableOpacity
          style={[styles.saveButton, saving && { opacity: 0.6 }]}
          onPress={handleSave}
          disabled={saving}
        >
          {saving ? <ActivityIndicator color="#fff" /> : <Text style={styles.saveButtonText}>Salvar</Text>}
        </TouchableOpacity>
      </ScrollView>

      <ErrorModal visible={modal.visible} onClose={closeModal} title={modal.title} message={modal.message} />
    </SafeAreaView>
  );
}
