import React, { useEffect, useState } from 'react'
import {
  View,
  Text,
  StyleSheet,
  Image,
  ScrollView,
  TouchableOpacity,
  FlatList,
  SafeAreaView
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useBottomTab } from '@/app/contexts/BottomTabContext';
import { Accordion } from '@/app/components/Accordion';
import { getPreferencesByUser } from '@/app/services/preferences.service';
import { PreferencesResponse } from '@/app/models/Preferences.types';
import { ServiceResponse } from '@/app/models/Service.types';
import { AvailabilityResponse } from '@/app/models/Availability.types';
import { NonWorkingDays } from '@/app/models/Availability.types';
import BottomTabBar from '@/app/components/BottomBar';
import { RootStackParamList } from '@/app/models/RootStackParams.types';
import { RouteProp, useNavigation, useRoute } from '@react-navigation/native';
import { StackNavigationProp } from '@react-navigation/stack';
import {styles} from './styles/HairdresserProfileStyles';

type HairdresserProfileScreenNavigationProp = StackNavigationProp<RootStackParamList>;

const galleryImages = new Array(5).fill(
  require('../../../../assets/images/react-logo.png')
);

export default function HairdresserProfileScreen() {
  const navigation = useNavigation<HairdresserProfileScreenNavigationProp>();
  const { hairdresser, setActiveTab } = useBottomTab();
  const [availabilities, setAvailabilities] = useState<AvailabilityResponse[]>();
  const [services, setServices] = useState<ServiceResponse[]>();
  const [preferences, setPreferences] = useState<PreferencesResponse[]>();
  const [nonWorkingDays, setNonWorkingDays] = useState<NonWorkingDays>();
  
  useEffect(()=>{
    const fetchHairdresserPreferences = async () => {
        try {
        const preferencesResponse = await getPreferencesByUser(hairdresser?.user.id);
        setPreferences(preferencesResponse);
        } catch (err) {
        console.log("Failed to retrieve user preferences",err);
        }
    }
    fetchHairdresserPreferences();
    setActiveTab('HairdresserProfile');
  },[])  
  return (
    <SafeAreaView style={styles.container}>
      <ScrollView style={styles.scrollContainer}>
        {/* Header */}
        <View style={styles.header}>
          <TouchableOpacity>
            <Ionicons name="arrow-back" size={24} color="black" />
          </TouchableOpacity>
          <TouchableOpacity onPress={()=> navigation.navigate('HairdresserSettings')}>
            <Ionicons name="settings-outline" size={24} color="black" />
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
        <Accordion title='Minhas Técnicas'>
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
        <TouchableOpacity style={styles.card} 
          onPress={()=>{navigation.navigate('AvailabilityManager', {
            availabilities: availabilities, 
            nonWorkingDays: nonWorkingDays
          })}}>
          <Text style={styles.cardText}>Meus horários de atendimento</Text>
          <View style={styles.arrowButton}>
            <Ionicons name="arrow-forward" size={16} color="#fff" />
          </View>
        </TouchableOpacity>

        {/* Available services */}
        <TouchableOpacity style={styles.card} onPress={()=>{navigation.navigate('HairdresserServiceManager')}}>
          <Text style={styles.cardText}>Meus serviços</Text>
          <View style={styles.arrowButton}>
            <Ionicons name="arrow-forward" size={16} color="#fff" />
          </View>
        </TouchableOpacity>
        
      </ScrollView>
      <BottomTabBar/>
    </SafeAreaView>
  )
}
