import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Image,
  ScrollView,
  TouchableOpacity,
  FlatList
} from 'react-native';
import { Ionicons, MaterialIcons } from '@expo/vector-icons';
import { Accordion } from '../../../components/Accordion' // You’ll create this below
import { getHairdresser } from '@/app/services/hairdresser.service';
import { HairdresserResponse } from '@/app/models/Hairdresser.types';

const galleryImages = new Array(5).fill(
  require('../../../../assets/images/react-logo.png') // Replace with your local image
);

const techniques = ['penteado', 'crespos', 'ondas', 'cachos', 'corte', 'tratamento'];

export default function HairdresserProfileScreen() {
  const [hairdresser, setHairdresser] = useState<HairdresserResponse>();

  useEffect(() => {
    const fetchHairdresserData = async () => {
      try {
        const response = await getHairdresser('rodrigosc615@gmail.com');
        setHairdresser(response.data);
      } catch (err) {
        console.error("Failed to fetch hairdresser:", err);
      } 
    };
    fetchHairdresserData();
  }, []);
  return (
    <ScrollView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity>
          <Ionicons name="arrow-back" size={24} color="black" />
        </TouchableOpacity>
        <TouchableOpacity>
          <Ionicons name="heart-outline" size={24} color="black" />
        </TouchableOpacity>
      </View>

      {/* Profile */}
      <View style={styles.profile}>
        <Image
          source={require('../../../../assets/images/react-logo.png')} // Replace with actual image
          style={styles.profileImage}
        />
        <View style={styles.profileText}>
          <Text style={styles.name}>{hairdresser?.user.first_name} {hairdresser?.user.last_name}</Text>
          <Text style={styles.location}>
            <Ionicons name="location-outline" size={14} /> 
              {hairdresser?.user.address}, 
              {hairdresser?.user.number},  
              {hairdresser?.user.neighborhood}, 
              {hairdresser?.user.city} - {hairdresser?.user.state}, 
              {hairdresser?.user.postal_code}
          </Text>
          <Text style={styles.rating}>⭐ {hairdresser?.user.rating}</Text>
        </View>
      </View>

      {/* Bio */}
      <Text style={styles.bio}>
        {hairdresser?.resume}
      </Text>

      {/* Gallery */}
      <Text style={styles.sectionTitle}>Galeria</Text>
      <FlatList
        data={galleryImages}
        keyExtractor={(_, index) => index.toString()}
        horizontal
        renderItem={({ item }) => (
          <Image source={item} style={styles.galleryImage} />
        )}
        contentContainerStyle={styles.gallery}
        showsHorizontalScrollIndicator={false}
      />

      {/* Techniques */}
      <View style={styles.techniques}>
        {techniques.map((tech) => (
          <View key={tech} style={styles.techTag}>
            <Text style={styles.techText}>{tech}</Text>
          </View>
        ))}
      </View>

      {/* Accordions */}
      <Accordion title="Horários de funcionamento">
        <Text>Seg a Sex: 09h às 18h{'\n'}Sáb: 09h às 13h</Text>
      </Accordion>
      <Accordion title="Serviços">
        <Text>- Corte{'\n'}- Tratamento{'\n'}- Penteado</Text>
      </Accordion>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#FFEFE8',
    padding: 16,
    flex: 1,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  profile: {
    flexDirection: 'row',
    marginVertical: 16,
    alignItems: 'center',
  },
  profileImage: {
    width: 70,
    height: 70,
    borderRadius: 35,
    marginRight: 12,
  },
  profileText: {
    flex: 1,
  },
  name: {
    fontSize: 20,
    fontWeight: '600',
  },
  location: {
    fontSize: 12,
    color: '#555',
  },
  rating: {
    marginTop: 4,
    fontSize: 14,
    color: '#000',
  },
  bio: {
    fontSize: 13,
    color: '#333',
    marginBottom: 10,
  },
  more: {
    color: '#A85E49',
    fontWeight: 'bold',
  },
  sectionTitle: {
    fontWeight: 'bold',
    marginVertical: 10,
    fontSize: 16,
  },
  gallery: {
    flexDirection: 'row',
    gap: 8,
  },
  galleryImage: {
    width: 100,
    height: 100,
    borderRadius: 12,
    marginRight: 8,
  },
  techniques: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginVertical: 12,
  },
  techTag: {
    backgroundColor: '#FFD6C7',
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  techText: {
    fontSize: 12,
    fontWeight: '500',
  },
});
