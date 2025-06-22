// app/(app)/(hairdresser)/availability/edit.tsx
import React from 'react';
import { View, Text, ScrollView, ActivityIndicator } from 'react-native';
import { useAvailabilityForm } from '@/hooks/hairdresserHooks/useAvailabilityForms';
import { AvailabilityForm } from '@/components/AvailabilityForms';

export default function AvailabilityEditScreen() {
  const form = useAvailabilityForm('edit'); // Use the hook in 'edit' mode

  if (form.loading) {
    return <ActivityIndicator size="large" style={{flex: 1}} />;
  }
  
  return (
    <ScrollView style={{ flex: 1, backgroundColor: '#FFEFE2' }}>
      <Text style={{ fontSize: 24, fontWeight: 'bold', textAlign: 'center', margin: 20 }}>
        Editar Horários
      </Text>
      <AvailabilityForm {...form} />
    </ScrollView>
  );
}