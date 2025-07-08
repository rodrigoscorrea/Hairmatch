// app/(app)/(hairdresser)/availability/create.tsx
import React from 'react';
import { View, Text, ScrollView } from 'react-native';
import { useAvailabilityForm } from '@/hooks/hairdresserHooks/useAvailabilityForms';
import { AvailabilityForm } from '@/components/AvailabilityForms'; // A new reusable component
import { ErrorModal } from '@/components/modals/ErrorModal/ErrorModal';

export default function AvailabilityCreateScreen() {
  const form = useAvailabilityForm('create'); // Use the hook in 'create' mode
  
  return (
    <ScrollView style={{ flex: 1, backgroundColor: '#FFEFE2' }}>
      <Text style={{ fontSize: 24, fontWeight: 'bold', textAlign: 'center', margin: 20 }}>
        Cadastrar Horários
      </Text>
      <AvailabilityForm {...form} />
      <ErrorModal
        visible={form.errorModal.visible}
        message={form.errorModal.message}
        onClose={form.closeErrorModal}
      />
    </ScrollView>
  );
}