// app/(app)/(customer)/hairdresser-profile/[id].tsx
import React from 'react';
import {
  View,
  Text,
  Image,
  ScrollView,
  TouchableOpacity,
  FlatList,
  ActivityIndicator
} from 'react-native';
import { styles } from '@/styles/customer/reservation/styles/HairdresserProfileReservationStyle'; // Adjust path
import { Ionicons } from '@expo/vector-icons';
import { Accordion } from '@/components/Accordion'; // Adjust path
import { formatAvailability } from '@/utils/availability-formater'; // Adjust path
import { useHairdresserProfile } from '@/hooks/customerHooks/useHairdresserReservation'; // <-- Our new hook!

const galleryImages = [
  require('../../../../assets/hairdressers/gallery/galery1.jpg'),
  require('../../../../assets/hairdressers/gallery/galery2.jpg'),
  // ... other images
];

// This is the demonstration avatar, we should probably handle this better,
// but for now, we'll keep it. A real implementation would fetch the avatar URL.
const defaultAvatar = require('../../../../assets/hairdressers/male/default.jpg'); 

export default function HairdresserProfileReservationScreen() {
  const {
    loading,
    hairdresser,
    availabilities,
    services,
    preferences,
    handleBookService,
    handleBack,
  } = useHairdresserProfile();

  if (loading) {
    return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
        <ActivityIndicator size="large" />
      </View>
    );
  }

  if (!hairdresser) {
    return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
        <Text>Não foi possível encontrar o perfil do profissional.</Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={handleBack}>
          <Ionicons name="arrow-back" size={24} color="black" />
        </TouchableOpacity>
      </View>

      {/* Profile */}
      <View style={styles.profile}>
        <Image
          source={defaultAvatar} // Using a default for now
          style={styles.profileImage}
        />
        <View style={styles.profileText}>
          <Text style={styles.name}>{hairdresser.user.first_name} {hairdresser.user.last_name}</Text>
          <Text style={styles.location}>
            <Ionicons name="location-outline" size={14} /> 
            {hairdresser.user.address}, {hairdresser.user.number}, {hairdresser.user.neighborhood}, {hairdresser.user.city} - {hairdresser.user.state}
          </Text>
          <Text style={styles.rating}>⭐ {hairdresser.user.rating}</Text>
        </View>
      </View>

      {/* Bio */}
      <Text style={styles.bio}>{hairdresser.resume}</Text>

      {/* Gallery */}
      <Text style={styles.sectionTitle}>Galeria</Text>
      <FlatList
        data={galleryImages}
        keyExtractor={(_, index) => index.toString()}
        horizontal
        renderItem={({ item }) => <Image source={item} style={styles.galleryImage} />}
        contentContainerStyle={styles.gallery}
        showsHorizontalScrollIndicator={false}
      />

      {/* Techniques - Preferences */}
      <Accordion title='Técnicas'>
        <View style={styles.tagsContainer}>
          {preferences.map((preference) => (
            <View style={styles.techCard} key={preference.id}>
              <Text style={styles.techText}>{preference.name}</Text>
            </View>
          ))}
        </View>
      </Accordion>
      
      {/* Available times */}
      <Accordion title="Horários de funcionamento">
        {availabilities.map((availability) => {
          const formatted = formatAvailability(availability);
          return (
            <View key={availability.id} style={styles.availabilityRow}>
              <Text style={styles.weekday}>{formatted.weekday}</Text>
              <Text style={styles.timeRange}>{formatted.timeRange}</Text>
            </View>
          );
        })}
      </Accordion>

      {/* Available services */}
      <Accordion title="Serviços">
        {services.map((service) => (
          <TouchableOpacity 
            style={styles.card} 
            key={service.id} 
            onPress={() => handleBookService(service)}
          >
            <Text style={styles.cardText}>{service.name}</Text>
            <View style={styles.arrowButton}>
              <Ionicons name="arrow-forward" size={16} color="#fff" />
            </View>
          </TouchableOpacity>
        ))}
      </Accordion>
    </ScrollView>
  );
}