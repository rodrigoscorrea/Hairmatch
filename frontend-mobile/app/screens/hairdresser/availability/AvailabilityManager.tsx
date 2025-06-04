import React, { useState } from 'react';
import {
  View, Text, TouchableOpacity, TextInput, Switch, ScrollView, StyleSheet
} from 'react-native';
import { RootStackParamList } from '@/app/models/RootStackParams.types';
import { StackNavigationProp } from '@react-navigation/stack';
import { useNavigation } from '@react-navigation/native';

const DAYS = [
  'Segunda-Feira',
  'Terça-Feira',
  'Quarta-Feira',
  'Quinta-Feira',
  'Sexta-Feira',
  'Sábado',
  'Domingo',
];

type AvailabilityManagerScreenNavigationProp = StackNavigationProp<RootStackParamList>;

export default function AvailabilityManagerScreen() {
  const navigation = useNavigation<AvailabilityManagerScreenNavigationProp>();
  const [mode, setMode] = useState<'all' | 'custom'>('all');
  const [allStart, setAllStart] = useState('08:00');
  const [allEnd, setAllEnd] = useState('17:00');

  const [days, setDays] = useState(
    DAYS.map((day, index) => ({
      name: day,
      active: index !== 6, // Sunday off by default
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
            <View key={day.name} style={styles.dayRow}>
              <Switch
                value={day.active}
                onValueChange={() => toggleDay(index)}
              />
              <Text style={styles.dayLabel}>{day.name}</Text>
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
        <TouchableOpacity style={styles.cancelButton} onPress={()=>navigation.navigate('HairdresserProfile')}>
          <Text>Voltar</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.saveButton}>
          <Text style={{ color: '#fff' }}>Salvar</Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#FFF3ED', padding: 20 },
  title: { fontSize: 20, fontWeight: 'bold', textAlign: 'center', marginBottom: 20 },
  tabContainer: { flexDirection: 'row', justifyContent: 'center' },
  tab: {
    borderWidth: 1, borderColor: '#ccc', padding: 10, width: 140,
    borderRadius: 12, marginHorizontal: 5, backgroundColor: '#FFF'
  },
  activeTab: {
    backgroundColor: '#fce6d6', borderColor: '#fa944b'
  },
  tabText: { textAlign: 'center', color: '#666' },
  activeTabText: { color: '#fa944b', fontWeight: 'bold', textAlign: 'center' },
  timeContainer: { marginTop: 20 },
  label: { fontWeight: 'bold', marginBottom: 5 },
  input: {
    backgroundColor: '#fde4d2', padding: 10, borderRadius: 10,
    width: 100, textAlign: 'center', fontSize: 18
  },
  dayRow: {
    flexDirection: 'row', alignItems: 'center', marginBottom: 15
  },
  dayLabel: { marginLeft: 10, width: 100 },
  timeInputs: { flexDirection: 'row', alignItems: 'center' },
  smallInput: {
    backgroundColor: '#fde4d2', padding: 5, borderRadius: 10,
    width: 60, textAlign: 'center'
  },
  buttonRow: {
    flexDirection: 'row', justifyContent: 'space-between',
    marginTop: 30, paddingHorizontal: 10
  },
  cancelButton: {
    backgroundColor: '#e5e4f4', padding: 12, borderRadius: 10, width: '40%', alignItems: 'center'
  },
  saveButton: {
    backgroundColor: '#fa944b', padding: 12, borderRadius: 10, width: '40%', alignItems: 'center'
  },
});
