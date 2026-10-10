import React from 'react';
import { View, Text, TextInput, TouchableOpacity, ScrollView, ActivityIndicator, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { ErrorModal } from '@/components/modals/ErrorModal/ErrorModal';
import { RESUME_MAX_LENGTH, useResumeForm } from '@/hooks/accountHooks/useResumeForm';
import { styles } from '@/styles/customer/styles/AccountConfigStyles';

// The text area of the sign-up description step (register/description.tsx), with a counter and Save.
export default function ResumeSettingScreen() {
  const router = useRouter();
  const { resume, count, saving, modal, handleChange, handleSave, closeModal } = useResumeForm();

  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.push('/(app)/hairdresser/profile/settings')}>
          <Ionicons name="chevron-back" size={24} color="#333" />
        </TouchableOpacity>
        <Text style={styles.buttonTitle}>Perfil</Text>
      </View>

      <ScrollView style={styles.container} keyboardShouldPersistTaps="handled">
        <View style={styles.header}>
          <Text style={styles.headerTitle}>Resumo</Text>
        </View>

        <View style={styles.form}>
          <Text style={resumeStyles.subtitle}>Esse texto será a descrição do seu perfil</Text>
          <TextInput
            style={resumeStyles.textArea}
            placeholder="Insira aqui a sua descrição detalhada para que atraia mais clientes"
            placeholderTextColor="#aaa"
            multiline
            value={resume}
            onChangeText={handleChange}
            maxLength={RESUME_MAX_LENGTH}
          />
          <Text style={resumeStyles.counter}>
            {count}/{RESUME_MAX_LENGTH}
          </Text>
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

const resumeStyles = StyleSheet.create({
  subtitle: {
    fontSize: 12,
    textAlign: 'center',
    color: '#555',
    marginBottom: 16,
  },
  textArea: {
    height: 200,
    backgroundColor: '#fff',
    borderRadius: 10,
    padding: 12,
    textAlignVertical: 'top',
    borderColor: '#ddd',
    borderWidth: 1,
    fontSize: 14,
  },
  counter: {
    alignSelf: 'flex-end',
    marginTop: 6,
    fontSize: 12,
    color: '#555',
  },
});
