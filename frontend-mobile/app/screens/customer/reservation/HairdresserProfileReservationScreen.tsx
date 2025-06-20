import React, { useState, useEffect, useContext } from 'react';
import {
  View,
  Text,
  Image,
  ScrollView,
  TouchableOpacity,
  FlatList
} from 'react-native';
import { styles } from './styles/HairdresserProfileReservationStyle';
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

const galleryImages = [
  require('../../../../assets/hairdressers/gallery/galery1.jpg'),
  require('../../../../assets/hairdressers/gallery/galery2.jpg'),
  require('../../../../assets/hairdressers/gallery/galery3.jpg'),
  require('../../../../assets/hairdressers/gallery/galery4.jpg'),
  require('../../../../assets/hairdressers/gallery/galery5.jpg')
];
type HairdresserProfileReservationScreenRouteProp = RouteProp<RootStackParamList, 'HairdresserProfileReservation'>;
type HairdresserProfileReservationScreenNavigationProp = StackNavigationProp<RootStackParamList>;

export default function HairdresserProfileReservationScreen() {
  const [availabilities, setAvailabilities] = useState<AvailabilityResponse[]>();
  const [services, setServices] = useState<ServiceResponse[]>();
  const [preferences, setPreferences] = useState<PreferencesResponse[]>();
  const {userInfo} = useContext(AuthContext)

  const navigation = useNavigation<HairdresserProfileReservationScreenNavigationProp>();
  const route = useRoute<HairdresserProfileReservationScreenRouteProp>();
  const hairdresser = route.params.hairdresser;
  const avatar = route.params.avatar;
  
  useEffect(() => {
    const fetchHairdresserAvailability = async () => {
      try {
        const availabilityResponse = await listAvailabilitiesByHairdresser(hairdresser.id)
        setAvailabilities(availabilityResponse.data);
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
          source={avatar} // Replace with actual image
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
          <TouchableOpacity style={styles.card} key={service.id} onPress={()=>navigation.navigate('ServiceBooking', {service: service, customer_id: userInfo.customer.id, hairdresser: hairdresser})}>
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
