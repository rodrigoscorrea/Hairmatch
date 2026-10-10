import React from 'react';
import { View, Text, TouchableOpacity, ScrollView, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { ErrorModal } from '@/components/modals/ErrorModal/ErrorModal';
import { AccountRole } from '@/hooks/accountHooks/useAccountForm';
import { usePreferencesSetting } from '@/hooks/accountHooks/usePreferencesSetting';
import { styles } from '@/styles/customer/styles/AccountConfigStyles';
import { styles as preferenceStyles } from '@/styles/register/styles/PreferencesStyle';

// Where each role's settings menu lives.
const SETTINGS_ROUTE = {
  customer: '/(app)/customer/profile',
  hairdresser: '/(app)/hairdresser/profile/settings',
} as const;

// The same picker as the sign-up preferences step (register/preferences.tsx), with Save instead of Skip/Finish.
export function PreferencesSettingScreen({ role }: { role: AccountRole }) {
  const router = useRouter();
  const { catalog, selected, loading, saving, saveDisabled, modal, togglePreference, handleSave, closeModal } =
    usePreferencesSetting();

  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.push(SETTINGS_ROUTE[role])}>
          <Ionicons name="chevron-back" size={24} color="#333" />
        </TouchableOpacity>
        <Text style={styles.buttonTitle}>Perfil</Text>
      </View>

      <ScrollView style={styles.container}>
        <View style={styles.header}>
          <Text style={styles.headerTitle}>Preferências</Text>
        </View>
        <Text style={preferenceStyles.preferencesSubtitle}>
          Isso nos ajuda a encontrar os melhores matches para você!
        </Text>

        {loading ? (
          <ActivityIndicator size="large" style={preferenceStyles.loader} />
        ) : (
          <View style={preferenceStyles.preferencesContainer}>
            {catalog.map(preference => {
              const isSelected = selected.includes(preference.id);
              return (
                <TouchableOpacity
                  key={preference.id}
                  style={[preferenceStyles.preferenceButton, isSelected && preferenceStyles.preferenceButtonSelected]}
                  onPress={() => togglePreference(preference.id)}
                  disabled={saving}
                >
                  {isSelected && (
                    <View style={preferenceStyles.checkIcon}>
                      <Text style={preferenceStyles.checkIconText}>✓</Text>
                    </View>
                  )}
                  <Text
                    style={[
                      preferenceStyles.preferenceButtonText,
                      isSelected && preferenceStyles.preferenceButtonTextSelected,
                    ]}
                  >
                    {preference.name}
                  </Text>
                </TouchableOpacity>
              );
            })}
          </View>
        )}

        <TouchableOpacity
          style={[styles.saveButton, saveDisabled && { opacity: 0.6 }]}
          onPress={handleSave}
          disabled={saveDisabled}
        >
          {saving ? <ActivityIndicator color="#fff" /> : <Text style={styles.saveButtonText}>Salvar</Text>}
        </TouchableOpacity>
      </ScrollView>

      <ErrorModal visible={modal.visible} onClose={closeModal} title={modal.title} message={modal.message} />
    </SafeAreaView>
  );
}
