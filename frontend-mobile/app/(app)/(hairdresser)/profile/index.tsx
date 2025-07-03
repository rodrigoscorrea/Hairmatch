// app/(app)/(hairdresser)/profile/index.tsx
import React from 'react';
import { View, Text, Image, ScrollView, TouchableOpacity, FlatList, SafeAreaView, ActivityIndicator } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { styles } from '@/styles/hairdresser/profile/styles/HairdresserProfileStyles'; // Adjust path
import { useHairdresserProfile } from '@/hooks/hairdresserHooks/useHairdresserProfile';
import { Accordion } from '@/components/Accordion';
import { API_BACKEND_URL } from '@/app/_layout';

export default function HairdresserProfileScreen() {
  const { hairdresser, preferences, loading, goToSettings, goToServices, goToAvailability } = useHairdresserProfile();
  const fallbackImage = 'https://images.unsplash.com/photo-1494790108755-2616c28c5ad2?w=64&h=64&fit=crop&crop=face';
  const profilePictureUrl = hairdresser?.user?.profile_picture
      ? `${API_BACKEND_URL}${hairdresser.user.profile_picture}`
      : fallbackImage;
  console.log(profilePictureUrl)
  return (
    <SafeAreaView style={styles.container}>
      <ScrollView style={styles.scrollContainer}>
        {/* Header */}
        <View style={styles.header}>
            <View style={{width: 24}} />
            <TouchableOpacity onPress={goToSettings}>
                <Ionicons name="settings-outline" size={24} color="black" />
            </TouchableOpacity>
        </View>

        {/* Profile */}
        <View style={styles.profile}>
            <Image 
                source={{ uri: profilePictureUrl }}
                style={styles.profileImage}
                resizeMode="cover"
            />
            <View style={styles.profileText}>
                <Text style={styles.name}>{hairdresser?.user.first_name} {hairdresser?.user.last_name}</Text>
                <Text style={styles.location}><Ionicons name="location-outline" size={14} /> {hairdresser?.user.city} - {hairdresser?.user.state}</Text>
                <Text style={styles.rating}>⭐ {hairdresser?.user.rating}</Text>
            </View>
        </View>

        {/* Bio */}
        <Text style={styles.bio}>{hairdresser?.resume}</Text>

        {/* Gallery, Techniques, etc. */}
        {loading ? <ActivityIndicator/> : (
            <Accordion title='Minhas Técnicas'>
                <View style={styles.tagsContainer}>
                    {preferences.map((p) => <View style={styles.techCard} key={p.id}><Text style={styles.techText}>{p.name}</Text></View>)}
                </View>
            </Accordion>
        )}
        
        {/* Navigation Cards */}
        <TouchableOpacity style={styles.card} onPress={goToAvailability}>
            <Text style={styles.cardText}>Meus horários de atendimento</Text>
            <View style={styles.arrowButton}><Ionicons name="arrow-forward" size={16} color="#fff" /></View>
        </TouchableOpacity>
        <TouchableOpacity style={styles.card} onPress={goToServices}>
            <Text style={styles.cardText}>Meus serviços</Text>
            <View style={styles.arrowButton}><Ionicons name="arrow-forward" size={16} color="#fff" /></View>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}