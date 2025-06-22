// app/(auth)/register/preferences.tsx (or wherever this screen is located)

import React from 'react';
import { View, Text, TouchableOpacity, KeyboardAvoidingView, ScrollView, ActivityIndicator, Modal, Image } from 'react-native';
import { styles } from '../../../styles/register/styles/PreferencesStyle'; // Adjust path if needed
import { usePreferencesForm } from '../../../hooks/authHooks/usePreferences'; // Adjust path
import { UserRole } from '@/models/User.types';

export default function PreferencesScreen() {
  const {
    isLoading,
    isFetchingPreferences,
    preferences,
    selectedPreferences,
    showSkipModal,
    setShowSkipModal,
    role,
    togglePreference,
    handleNext,
    handleSkip,
  } = usePreferencesForm();

  return (
    <KeyboardAvoidingView style={styles.container}>
      {/* --- MODAL (No changes needed) --- */}
      <Modal
          visible={showSkipModal}
          transparent
          animationType="fade"
      >
        <View style={styles.modalOverlay}>
            <View style={styles.modalContainer}>
            <Text style={styles.modalTitle}>Personalize sua experiência no Hairmatch</Text>
            <Text style={styles.modalText}>
                Selecionar suas preferências nos ajuda a recomendar cabeleireiros que combinam com o seu estilo.
                Você pode pular essa etapa, mas isso afetará suas recomendações.
            </Text>
            <View style={styles.modalButtonGroup}>
                <TouchableOpacity
                    style={styles.modalBackButton}
                    onPress={() => setShowSkipModal(false)}
                >
                    <Text style={styles.modalBackButtonText}>Voltar</Text>
                </TouchableOpacity>
                <TouchableOpacity
                    style={styles.modalAcceptButton}
                    onPress={handleSkip} // Use the handler from the hook
                >
                    <Text style={styles.modalAcceptButtonText}>Aceitar e Pular</Text>
                </TouchableOpacity>
            </View>
            </View>
        </View>
      </Modal>

      <ScrollView style={styles.scrollView} contentContainerStyle={styles.scrollContent}>
        {/* --- HEADER (No changes needed) --- */}
        <View style={styles.header}>
          <Image source={require('../../../assets/images/HairmatchLogo.png')}></Image>
        </View>
        
        {/* --- TITLE (No changes needed) --- */}
        <View style={styles.titleContainer}>
          <Text style={styles.preferencesTitle}>Quais são as suas preferências?</Text>
          <Text style={styles.preferencesSubtitle}>
            Isso nos ajuda a encontrar os melhores matches para você!
          </Text>
        </View>

        {/* --- PREFERENCES LIST (No changes needed) --- */}
        {isFetchingPreferences ? (
          <ActivityIndicator size="large" style={styles.loader} />
        ) : (
          <View style={styles.preferencesContainer}>
            {preferences.map((preference) => (
              <TouchableOpacity
                key={preference.id}
                style={[
                  styles.preferenceButton,
                  selectedPreferences.includes(preference.id) && styles.preferenceButtonSelected
                ]}
                onPress={() => togglePreference(preference.id)}
              >
                {selectedPreferences.includes(preference.id) && (
                  <View style={styles.checkIcon}><Text style={styles.checkIconText}>✓</Text></View>
                )}
                <Text
                  style={[
                    styles.preferenceButtonText,
                    selectedPreferences.includes(preference.id) && styles.preferenceButtonTextSelected
                  ]}
                >
                  {preference.name}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        )}

        {/* --- BOTTOM BUTTONS (Simplified) --- */}
        <View style={styles.buttonContainer}>
          <TouchableOpacity 
            style={styles.skipButton} 
            onPress={() => setShowSkipModal(true)} // Just open the modal
            disabled={isLoading}
          >
            <Text style={styles.skipButtonText}>Pular</Text>
          </TouchableOpacity>
          
          <TouchableOpacity 
            style={styles.finishButton} 
            onPress={handleNext} // The hook now handles the logic
            disabled={isLoading}
          >
            {isLoading ? (
              <ActivityIndicator size="small" color="#fff" />
            ) : (
              <Text style={styles.modalAcceptButtonText}>
                {role === UserRole.CUSTOMER ? 'Finalizar' : 'Próximo'}
              </Text>
            )}
          </TouchableOpacity>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}