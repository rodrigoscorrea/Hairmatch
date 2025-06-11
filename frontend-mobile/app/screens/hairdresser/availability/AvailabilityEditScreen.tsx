import React, { useEffect, useState } from 'react';
import {
  View, Text, TouchableOpacity, TextInput, Switch, ScrollView, StyleSheet
} from 'react-native';
import { RootStackParamList } from '@/app/models/RootStackParams.types';
import { StackNavigationProp } from '@react-navigation/stack';
import { RouteProp, useNavigation, useRoute } from '@react-navigation/native';
import { useBottomTab } from '@/app/contexts/BottomTabContext';
import { updateAvailability } from '@/app/services/availability.service';
import { styles } from './styles/AvailabilityEditStyles';

const DAYS = [
  {name: 'Segunda-Feira', weekday: 'monday'},
  {name:'Terça-Feira', weekday:'tuesday'},
  {name:'Quarta-Feira', weekday:'wednesday'},
  {name:'Quinta-Feira', weekday:'thursday'},
  {name:'Sexta-Feira', weekday:'friday'},
  {name:'Sábado', weekday:'saturday'},
  {name:'Domingo', weekday:'sunday'},
];

type Availability = {
  id: number;
  weekday: string;
  start_time: string;
  end_time: string;
  break_start?: string;
  break_end?: string;
};

type DayState = {
  info: typeof DAYS[0];
  active: boolean;
  start: string;
  end: string;
  breakStart?: string;
  breakEnd?: string;
  availabilityId?: number;
};

type AvailabilityCreateScreenNavigationProp = StackNavigationProp<RootStackParamList>;
type AvailabilityCreateScreenRouteProp = RouteProp<RootStackParamList, 'AvailabilityEdit'>;

export default function AvailabilityEditScreen() {
  const navigation = useNavigation<AvailabilityCreateScreenNavigationProp>();
  const route = useRoute<AvailabilityCreateScreenRouteProp>();

  const [availabilities, setAvailabilities] = useState(route.params.availabilities);
  const [nonWorkingDays, setNonWorkingDays] = useState(route.params.nonWorkingDays);
  const {hairdresser, setActiveTab} = useBottomTab();

  const [days, setDays] = useState<DayState[]>([]);

  // Helper function to convert time format from "HH:MM:SS" to "HH:MM"
  const formatTimeDisplay = (time: string): string => {
    return time.substring(0, 5);
  };

  // Helper function to convert time format from "HH:MM" to "HH:MM:SS"
  const formatTimeForBackend = (time: string): string => {
    return `${time}:00`;
  };

  // Initialize days state based on availabilities and nonWorkingDays
  useEffect(() => {
    const initialDays = DAYS.map((day, index) => {
      // Check if this day is a non-working day
      const isNonWorkingDay = nonWorkingDays.includes(index + 1); // assuming 1-based indexing
      
      // Find availability for this day
      const availability = availabilities?.find(avail => avail.weekday === day.weekday);
      
      if (isNonWorkingDay || !availability) {
        // Non-working day or no availability found
        return {
          info: day,
          active: false,
          start: '08:00',
          end: '17:00',
        };
      } else {
        // Working day with availability
        return {
          info: day,
          active: true,
          start: formatTimeDisplay(availability.start_time),
          end: formatTimeDisplay(availability.end_time),
          breakStart: availability.break_start ? formatTimeDisplay(availability.break_start) : undefined,
          breakEnd: availability.break_end ? formatTimeDisplay(availability.break_end) : undefined,
          availabilityId: availability.id,
        };
      }
    });
    
    setDays(initialDays);
  }, [availabilities, nonWorkingDays]);

  const toggleDay = (index: number) => {
    const newDays = [...days];
    newDays[index].active = !newDays[index].active;
    setDays(newDays);
  };

  const handleChangeTime = (index: number, key: 'start' | 'end' | 'breakStart' | 'breakEnd', value: string) => {
    const newDays = [...days];
    newDays[index][key] = value;
    setDays(newDays);
  };

  const handleAvailabilitySubmit = async () => {
    // Get active days (working days)
    const workingDays = days.filter((day) => day.active === true);
    
    // Format availabilities for backend
    const availabilitiesForBackend = workingDays.map((day) => {
      const availability: any = {
        weekday: day.info.weekday,
        start_time: formatTimeForBackend(day.start),
        end_time: formatTimeForBackend(day.end),
      };
      
      if (day.availabilityId) {
        availability.id = day.availabilityId;
      }
      
      if (day.breakStart && day.breakEnd) {
        availability.break_start = formatTimeForBackend(day.breakStart);
        availability.break_end = formatTimeForBackend(day.breakEnd);
      }
      
      return availability;
    });
    
    const nonWorkingDaysForBackend = days
      .map((day, index) => day.active ? null : index + 1)
      .filter(dayIndex => dayIndex !== null);
    
    try {
      await updateAvailability(availabilitiesForBackend, hairdresser?.id);
      
      navigation.navigate("HairdresserProfile");
    } catch (error) {
      console.error('Error updating availability:', error);
    }
  };

  return (
    <ScrollView style={styles.container}>
      <Text style={styles.title}>Editar Horário de Atendimento</Text>

      {/* Toggle Tabs */}
      <View style={styles.tabContainer}>
        <View style={{ marginTop: 20 }}>
          {days.map((day, index) => (
            <View key={day.info.name} style={styles.dayRow}>
              <Switch
                value={day.active}
                onValueChange={() => toggleDay(index)}
              />
              <Text style={styles.dayLabel}>{day.info.name}</Text>
              {day.active ? (
                <View style={styles.timeContainer}>
                  <View style={styles.timeInputs}>
                    <TextInput
                      style={styles.smallInput}
                      value={day.start}
                      onChangeText={(value) => handleChangeTime(index, 'start', value)}
                      keyboardType="numeric"
                      placeholder="08:00"
                    />
                    <Text style={{ marginHorizontal: 5 }}>às</Text>
                    <TextInput
                      style={styles.smallInput}
                      value={day.end}
                      onChangeText={(value) => handleChangeTime(index, 'end', value)}
                      keyboardType="numeric"
                      placeholder="17:00"
                    />
                  </View>
                  
                  {/* Optional: Break time inputs */}
                  {/* <View style={styles.breakTimeContainer}>
                    <Text style={styles.breakLabel}>Intervalo (opcional):</Text>
                    <View style={styles.timeInputs}>
                      <TextInput
                        style={styles.smallInput}
                        value={day.breakStart || ''}
                        onChangeText={(value) => handleChangeTime(index, 'breakStart', value)}
                        keyboardType="numeric"
                        placeholder="12:00"
                      />
                      <Text style={{ marginHorizontal: 5 }}>às</Text>
                      <TextInput
                        style={styles.smallInput}
                        value={day.breakEnd || ''}
                        onChangeText={(value) => handleChangeTime(index, 'breakEnd', value)}
                        keyboardType="numeric"
                        placeholder="13:00"
                      />
                    </View>
                  </View> */}
                </View>
              ) : (
                <Text style={{ marginLeft: 10, color: 'gray' }}>Fechado</Text>
              )}
            </View>
          ))}
        </View>
      </View>

      <View style={styles.buttonRow}>
        <TouchableOpacity style={styles.cancelButton} onPress={()=>navigation.navigate('AvailabilityManager')}>
          <Text>Voltar</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.saveButton} onPress={handleAvailabilitySubmit}>
          <Text style={{ color: '#fff' }}>Salvar</Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
}