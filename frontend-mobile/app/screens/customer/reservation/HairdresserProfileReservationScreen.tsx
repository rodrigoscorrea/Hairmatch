import React, { useState, useEffect, useContext } from 'react';
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
import { getPreferencesByUser } from '@/app/services/preferences.service';
import { PreferencesResponse } from '@/app/models/Preferences.types';
import { RootStackParamList } from '@/app/models/RootStackParams.types';
import { StackNavigationProp } from '@react-navigation/stack';
import { useNavigation, RouteProp, useRoute } from '@react-navigation/native';
import { NonWorkingDays } from '@/app/models/Availability.types'; 
import { AuthContext } from '../../../index';

const galleryImages = new Array(5).fill(
  require('../../../../assets/images/react-logo.png')
);
type HairdresserProfileReservationScreenRouteProp = RouteProp<RootStackParamList, 'HairdresserProfileReservation'>;
type HairdresserProfileReservationScreenNavigationProp = StackNavigationProp<RootStackParamList>;

export default function HairdresserProfileReservationScreen() {
  //const [hairdresser, setHairdresser] = useState<HairdresserResponse>();
  const [availabilities, setAvailabilities] = useState<AvailabilityResponse[]>();
  const [services, setServices] = useState<ServiceResponse[]>();
  const [preferences, setPreferences] = useState<PreferencesResponse[]>();
  const [nonWorkingDays, setNonWorkingDays] = useState<NonWorkingDays>();
  const {userInfo} = useContext(AuthContext)

  const navigation = useNavigation<HairdresserProfileReservationScreenNavigationProp>();
  const route = useRoute<HairdresserProfileReservationScreenRouteProp>();
  const hairdresser = route.params.hairdresser;
  
  useEffect(() => {
    /* const fetchHairdresserData = async () => {
      try {
        const hairdresserResponse = await getHairdresser('rodrigosc616@gmail.com');
        setHairdresser(hairdresserResponse.data);
      } catch (err) {
        console.error("Failed to fetch hairdresser:", err);
      } 
    }; */
    const fetchHairdresserAvailability = async () => {
      try {
        const availabilityResponse = await listAvailabilitiesByHairdresser(hairdresser.id)
        setAvailabilities(availabilityResponse.data);
        setNonWorkingDays(availabilityResponse.non_working_days)
      } catch (err) {
        console.log("Failed to fetch Hairdresser Availabilities", err)
      }
    }
    const fetchHairdresserService = async () => {
      try {
        const serviceResponse = await listServicesByHairdresser(hairdresser.id);
        setServices(serviceResponse.data);
      } catch (err) {
        console.log("Failed to fetch Hairdresser Services", err);
      }
    }
    const fetchHairdresserPreferences = async () => {
      try {
        const preferencesResponse = await getPreferencesByUser(hairdresser.user.id);
        setPreferences(preferencesResponse);
      } catch (err) {
        console.log("Failed to retrieve user preferences",err);
      }
    }
    
    //fetchHairdresserData();
    fetchHairdresserAvailability();
    fetchHairdresserService();
    fetchHairdresserPreferences();
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

      {/* Techniques - Preferences */}
      <Accordion title='Técnicas'>
        <View style={styles.tagsContainer}>
          {preferences ? preferences.map((preference) => (
            <View style={styles.techCard} key={preference.id}>
              <Text style={styles.techText}>{preference.name}</Text>
            </View>
          )) : (
            <Text>Carregando técnicas do profissional...</Text>
          )}
        </View>
      </Accordion>
    
      {/* Available times */}
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

      {/* Available services */}
      <Accordion title="Serviços">
        {services ? services.map((service) => (
          <TouchableOpacity style={styles.card} key={service.id} onPress={()=>navigation.navigate('ServiceBooking', {service: service, customer_id: userInfo.customer.id, non_working_days: nonWorkingDays, hairdresser: hairdresser})}>
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
    color: '#FFFFFF'
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
  },
  tagsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8, // React Native doesn’t support `gap` natively; use margin instead if needed
    marginTop: 8,
  },
  techCard: {
    backgroundColor: '#FF8822',
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 999,
    margin: 4,
  },
});
