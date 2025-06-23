// components/hairdresser/AvailabilityForm.tsx
import React from 'react';
import { View, Text, TouchableOpacity, TextInput, Switch } from 'react-native';
import { styles } from '@/styles/hairdresser/availability/styles/AvailabilityCreateStyle'; // Use styles from create screen

// The form now accepts props from the hook
export const AvailabilityForm = ({
  days,
  formMode,
  handleModeChange,
  allStart, setAllStart,
  allEnd, setAllEnd,
  toggleDay,
  handleTimeChange,
  handleSubmit,
  goBack,
  isSaveDisabled
}: any) => {
  return (
    <View style={styles.container}>
      {/* Toggle Tabs */}
      <View style={styles.tabContainer}>
        <TouchableOpacity 
          style={[styles.tab, formMode === 'all' && styles.activeTab]} 
          onPress={() => handleModeChange('all')} // <-- Use the new handler
        >
          <Text style={formMode === 'all' ? styles.activeTabText : styles.tabText}>Todos os dias</Text>
        </TouchableOpacity>
        <TouchableOpacity 
          style={[styles.tab, formMode === 'custom' && styles.activeTab]} 
          onPress={() => handleModeChange('custom')} // <-- Use the new handler
        >
          <Text style={formMode === 'custom' ? styles.activeTabText : styles.tabText}>Customizar</Text>
        </TouchableOpacity>
      </View>

      {/* Form Content */}
      {formMode === 'all' ? (
        <View style={styles.timeContainer}>
          <Text style={styles.label}>Horário de início</Text>
          <TextInput style={styles.input} value={allStart} onChangeText={setAllStart} />
          <Text style={[styles.label, { marginTop: 20 }]}>Horário de fim</Text>
          <TextInput style={styles.input} value={allEnd} onChangeText={setAllEnd} />
        </View>
      ) : (
        <View style={{ marginTop: 20 }}>
          {days.map((day: any, index: any) => (
            <View key={day.info.name} style={styles.dayRow}>
              <Switch value={day.active} onValueChange={() => toggleDay(index)} />
              <Text style={styles.dayLabel}>{day.info.name}</Text>
              {day.active ? (
                <View style={styles.timeInputs}>
                  <TextInput style={styles.smallInput} value={day.start} onChangeText={(v) => handleTimeChange(index, 'start', v)} />
                  <Text>às</Text>
                  <TextInput style={styles.smallInput} value={day.end} onChangeText={(v) => handleTimeChange(index, 'end', v)} />
                </View>
              ) : (
                <Text style={{ marginLeft: 10, color: 'gray' }}>Fechado</Text>
              )}
            </View>
          ))}
        </View>
      )}

      {/* Action Buttons */}
      <View style={styles.buttonRow}>
        <TouchableOpacity style={styles.cancelButton} onPress={goBack}>
          <Text>Voltar</Text>
        </TouchableOpacity>
        <TouchableOpacity style={isSaveDisabled ? styles.disabledSaveButton : styles.saveButton} onPress={handleSubmit} disabled={isSaveDisabled}>
          <Text style={{ color: '#fff' }}>Salvar</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
};