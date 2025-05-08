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
import { Accordion } from '../../../components/Accordion'
import { getHairdresser } from '@/app/services/hairdresser.service';
import { HairdresserResponse } from '@/app/models/Hairdresser.types';
import { listAvailabilitiesByHairdresser } from '@/app/services/availability.service';
import { AvailabilityResponse } from '@/app/models/Availability.types';
import { listServicesByHairdresser } from '@/app/services/service.service';
import { ServiceResponse } from '@/app/models/Service.types';
import { formatAvailability } from '@/app/utils/availability-formater';

const galleryImages = new Array(5).fill(
  require('../../../../assets/images/react-logo.png')
);

const techniques = ['penteado', 'crespos', 'ondas', 'cachos', 'corte', 'tratamento'];

export default function HairdresserProfileScreen() {
  const [hairdresser, setHairdresser] = useState<HairdresserResponse>();
  const [availabilities, setAvailabilities] = useState<AvailabilityResponse[]>();
  const [services, setServices] = useState<ServiceResponse[]>();

  useEffect(() => {
    const fetchHairdresserData = async () => {
      try {
        const hairdresserResponse = await getHairdresser('rodrigosc616@gmail.com');
        setHairdresser(hairdresserResponse.data);
      } catch (err) {
        console.error("Failed to fetch hairdresser:", err);
      } 
    };
    const fetchHairdresserAvailability = async () => {
      try {
        const availabilityResponse = await listAvailabilitiesByHairdresser('1')
        setAvailabilities(availabilityResponse.data);
      } catch (err) {
        console.log("Failed to fetch Hairdresser Availabilities", err)
      }
    }
    const fetchHairdresserService = async () => {
      try {
        const serviceResponse = await listServicesByHairdresser('1')
        setServices(serviceResponse.data);
      } catch (err) {
        console.log("Failed to fetch Hairdresser Services", err)
      }
    }
    

    fetchHairdresserData();
    fetchHairdresserAvailability();
    fetchHairdresserService();
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
        {availabilities ? availabilities.map((availability) => {
        const formatted = formatAvailability(availability);
          return (
            <View key={availability.id} style={styles.availabilityRow}>
              <Text style={styles.weekday}>{formatted.weekday}</Text>
              <Text style={styles.timeRange}>{formatted.timeRange}</Text>
            </View>
          );
        }) : 
        (
          <>
            <Text>Carregando horários do cabeleireiro...</Text>
          </>
        )}
      </Accordion>
      <Accordion title="Serviços">
        {services ? services.map((service) => (
          <TouchableOpacity style={styles.card} key={service.id}>
            <Text style={styles.cardText}>{service.name}</Text>
            <View style={styles.arrowButton}>
              <Ionicons name="arrow-forward" size={16} color="#fff" />
            </View>
          </TouchableOpacity>
        )) : 
        (
          <>
            <Text>Carregando Serviços...</Text>
          </>
        )}
      
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
  card: {
    borderWidth: 1,
    borderColor: '#FFA366',
    borderRadius: 16,
    padding: 12,
    paddingLeft: 16,
    marginBottom: 8,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: '#FFEFE8',
  },
  cardText: {
    fontWeight: '600',
    fontSize: 14,
  },
  arrowButton: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: '#FF7A00',
    alignItems: 'center',
    justifyContent: 'center',
  },
  availabilityRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#eee'
  },
  weekday: {
    fontWeight: 'bold'
  },
  timeRange: {
    color: '#666'
  }
});
