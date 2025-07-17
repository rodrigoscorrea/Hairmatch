// app/(app)/(hairdresser)/availability/index.tsx
import React from 'react';
import { View, Text, ScrollView, TouchableOpacity, ActivityIndicator } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { styles } from '@/styles/hairdresser/availability/styles/AvailabilityManagerStyles'; // Adjust path
import { formatAvailability } from '@/utils/availability-formater';
import { useAvailabilityManager } from '@/hooks/hairdresserHooks/useAvailabilityManager';

export default function AvailabilityManagerScreen() {
  const { isLoading, availabilities, goToCreate, goToEdit, goBack } = useAvailabilityManager();

  const AddButton = () => (
    <TouchableOpacity style={styles.addButton} onPress={goToCreate}>
      <Ionicons name="add" size={28} color="#000" />
    </TouchableOpacity>
  );

  const EditButton = () => (
    <TouchableOpacity style={styles.addButton} onPress={goToEdit}>
      <Ionicons name="pencil-outline" size={24} color="#000" />
    </TouchableOpacity>
  );

  return (
    <View style={{ flex: 1 }}>
      <ScrollView style={styles.container}>
      <View style={styles.iconRow}>
        <TouchableOpacity onPress={goBack}>
            <Ionicons name="arrow-back" size={24} color="black" />
        </TouchableOpacity>
        <Text style={styles.title}>Meus Horários de Atendimento</Text>
        <View style={{width: 24}}/>
      </View>
          
        {isLoading ? (
          <ActivityIndicator size="large" color="#000" />
        ) : availabilities && availabilities.length > 0 ? (
          availabilities.map((availability: any) => {
            const formatted = formatAvailability(availability);
            return (
              <View key={availability.id} style={styles.availabilityRow}>
                <Text style={styles.weekday}>{formatted.weekday}</Text>
                <Text style={styles.timeRange}>{formatted.timeRange}</Text>
              </View>
            );
          })
        ) : (
          <Text>Você ainda não cadastrou seus horários.</Text>
        )}
      </ScrollView>

      {/* Conditionally render Add or Edit button */}
      {!isLoading && (availabilities && availabilities.length > 0 ? <EditButton /> : <AddButton />)}
    </View>
  );
};