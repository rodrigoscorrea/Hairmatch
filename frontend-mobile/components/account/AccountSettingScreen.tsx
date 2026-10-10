import React from 'react';
import { View, Text, TouchableOpacity, ScrollView, Image, ActivityIndicator, Modal } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { FormInput } from '@/components/formInputs/FormInput';
import { ErrorModal } from '@/components/modals/ErrorModal/ErrorModal';
import { AccountRole, useAccountForm } from '@/hooks/accountHooks/useAccountForm';
import { useProfilePicture } from '@/hooks/accountHooks/useProfilePicture';
import { styles } from '@/styles/customer/styles/AccountConfigStyles';
import { styles as optionStyles } from '@/components/modals/confirmationModal/ConfirmationModalStyles';

// Where each role's settings menu lives.
const SETTINGS_ROUTE = {
  customer: '/(app)/customer/profile',
  hairdresser: '/(app)/hairdresser/profile/settings',
} as const;

export function AccountSettingScreen({ role }: { role: AccountRole }) {
  const router = useRouter();
  const { values, errors, email, profilePicture, saving, modal, handleChange, handleSave, closeModal } =
    useAccountForm(role);
  const picture = useProfilePicture();

  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.push(SETTINGS_ROUTE[role])}>
          <Ionicons name="chevron-back" size={24} color="#333" />
        </TouchableOpacity>
        <Text style={styles.buttonTitle}>Perfil</Text>
      </View>
      <ScrollView style={styles.container} keyboardShouldPersistTaps="handled">
        <View style={styles.header}>
          <Text style={styles.headerTitle}>Dados da Conta</Text>
        </View>

        <TouchableOpacity
          style={styles.profilePicContainer}
          onPress={picture.openOptions}
          disabled={picture.updating}
        >
          <Image
            source={
              profilePicture
                ? { uri: profilePicture }
                : require('../../assets/images/profile_picture_placeholder.png')
            }
            style={[styles.profilePic, picture.updating && { opacity: 0.5 }]}
            resizeMode="cover"
          />
          {picture.updating && <ActivityIndicator style={{ position: 'absolute', top: 50 }} />}
        </TouchableOpacity>

        <View style={styles.form}>
          <FormInput
            value={values.first_name}
            onChangeText={text => handleChange('first_name', text)}
            placeholder="Nome"
            isError={errors.first_name}
            containerStyle={styles.inputContainer}
          />
          <FormInput
            value={values.last_name}
            onChangeText={text => handleChange('last_name', text)}
            placeholder="Sobrenome"
            isError={errors.last_name}
            containerStyle={styles.inputContainer}
          />
          <FormInput
            value={values.document}
            onChangeText={text => handleChange('document', text)}
            placeholder={role === 'customer' ? 'CPF' : 'CNPJ'}
            keyboardType="numeric"
            isError={errors.document}
            containerStyle={styles.inputContainer}
          />
          {/* The e-mail is the login and cannot change here. */}
          <FormInput
            value={email}
            placeholder="Email"
            editable={false}
            style={{ color: '#999' }}
            containerStyle={styles.inputContainer}
          />
          <FormInput
            value={values.phone}
            onChangeText={text => handleChange('phone', text)}
            placeholder="(DDD) Telefone"
            keyboardType="phone-pad"
            isError={errors.phone}
            containerStyle={styles.inputContainer}
          />
        </View>

        <TouchableOpacity
          style={[styles.saveButton, saving && { opacity: 0.6 }]}
          onPress={handleSave}
          disabled={saving}
        >
          {saving ? <ActivityIndicator color="#fff" /> : <Text style={styles.saveButtonText}>Salvar</Text>}
        </TouchableOpacity>
      </ScrollView>

      {/* "Remover foto" only shows when there is a picture to remove. */}
      <Modal visible={picture.optionsVisible} transparent animationType="fade" onRequestClose={picture.closeOptions}>
        <View style={optionStyles.overlay}>
          <View style={optionStyles.modalContainer}>
            <Text style={optionStyles.title}>Foto de perfil</Text>
            <TouchableOpacity style={[optionStyles.confirmButton, pictureOption]} onPress={picture.handlePickNew}>
              <Text style={optionStyles.confirmText}>Escolher nova foto</Text>
            </TouchableOpacity>
            {picture.hasPicture && (
              <TouchableOpacity style={[optionStyles.cancelButton, pictureOption]} onPress={picture.handleRemove}>
                <Text style={optionStyles.cancelText}>Remover foto</Text>
              </TouchableOpacity>
            )}
            <TouchableOpacity style={[pictureOption, { paddingVertical: 10 }]} onPress={picture.closeOptions}>
              <Text style={optionStyles.cancelText}>Cancelar</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>

      <ErrorModal visible={modal.visible} onClose={closeModal} title={modal.title} message={modal.message} />
      <ErrorModal visible={picture.modal.visible} onClose={picture.closeModal} message={picture.modal.message} />
    </SafeAreaView>
  );
}

const pictureOption = { alignItems: 'center', marginTop: 10 } as const;
