import React, { useState } from 'react';
import {
  View, Text, TouchableOpacity, TextInput, Switch, ScrollView, StyleSheet
} from 'react-native';
import { RootStackParamList } from '@/app/models/RootStackParams.types';
import { StackNavigationProp } from '@react-navigation/stack';
import { useNavigation } from '@react-navigation/native';
import { useBottomTab } from '@/app/contexts/BottomTabContext';
import { AvailabilityRequest } from '@/app/models/Availability.types';
import { createAvailability } from '@/app/services/availability.service';
import { styles } from './styles/AvailabilityCreateStyle';

const DAYS = [
  {name: 'Segunda-Feira', weekday: 'monday'},
  {name:'Terça-Feira', weekday:'tuesday'},
  {name:'Quarta-Feira', weekday:'wednesday'},
  {name:'Quinta-Feira', weekday:'thursday'},
  {name:'Sexta-Feira', weekday:'friday'},
  {name:'Sábado', weekday:'saturday'},
  {name:'Domingo', weekday:'sunday'},
];

type AvailabilityCreateScreenNavigationProp = StackNavigationProp<RootStackParamList>;

export default function AvailabilityCreateScreen() {
  const navigation = useNavigation<AvailabilityCreateScreenNavigationProp>();
  const {hairdresser, setActiveTab} = useBottomTab();
  const [mode, setMode] = useState<'all' | 'custom'>('all');
  const [allStart, setAllStart] = useState('08:00');
  const [allEnd, setAllEnd] = useState('17:00');

  const [days, setDays] = useState(
    DAYS.map((day, index) => ({
      info: day,
      active: true,
      start: '08:00',
      end: '17:00',
    }))
  );

  const toggleDay = (index: number) => {
    const newDays = [...days];
    newDays[index].active = !newDays[index].active;
    setDays(newDays);
  };

  const handleChangeTime = (index: number, key: 'start' | 'end', value: string) => {
    const newDays = [...days];
    newDays[index][key] = value;
    setDays(newDays);
  };

  const handleAvailabilitySubmit = async () => {
    const availabilitiesRaw = days.filter((day) => day.active == true);
    const availabilities = availabilitiesRaw.map((availability) => {
      return {
        weekday: availability.info.weekday,
        start_time: `${availability.start}:00`,
        end_time: `${availability.end}:00`
      }
    })
    await createAvailability(availabilities, hairdresser?.id);
    navigation.navigate("HairdresserProfile");
  }

  return (
    <ScrollView style={styles.container}>
      <Text style={styles.title}>Horário de Atendimento</Text>

      {/* Toggle Tabs */}
      <View style={styles.tabContainer}>
        <TouchableOpacity
          style={[styles.tab, mode === 'all' && styles.activeTab]}
          onPress={() => setMode('all')}
        >
          <Text style={mode === 'all' ? styles.activeTabText : styles.tabText}>Todos os dias</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.tab, mode === 'custom' && styles.activeTab]}
          onPress={() => setMode('custom')}
        >
          <Text style={mode === 'custom' ? styles.activeTabText : styles.tabText}>Customizar</Text>
        </TouchableOpacity>
      </View>

      {/* All Days Same */}
      {mode === 'all' ? (
        <View style={styles.timeContainer}>
          <Text style={styles.label}>Horário de início</Text>
          <TextInput
            style={styles.input}
            value={allStart}
            onChangeText={setAllStart}
            keyboardType="numeric"
          />

          <Text style={[styles.label, { marginTop: 20 }]}>Horário de fim</Text>
          <TextInput
            style={styles.input}
            value={allEnd}
            onChangeText={setAllEnd}
            keyboardType="numeric"
          />
        </View>
      ) : (
        // Custom Per Day
        <View style={{ marginTop: 20 }}>
          {days.map((day, index) => (
            <View key={day.info.name} style={styles.dayRow}>
              <Switch
                value={day.active}
                onValueChange={() => toggleDay(index)}
              />
              <Text style={styles.dayLabel}>{day.info.name}</Text>
              {day.active ? (
                <View style={styles.timeInputs}>
                  <TextInput
                    style={styles.smallInput}
                    value={day.start}
                    onChangeText={(value) => handleChangeTime(index, 'start', value)}
                    keyboardType="numeric"
                  />
                  <Text style={{ marginHorizontal: 5 }}>às</Text>
                  <TextInput
                    style={styles.smallInput}
                    value={day.end}
                    onChangeText={(value) => handleChangeTime(index, 'end', value)}
                    keyboardType="numeric"
                  />
                </View>
              ) : (
                <Text style={{ marginLeft: 10, color: 'gray' }}>Fechado</Text>
              )}
            </View>
          ))}
        </View>
      )}

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
