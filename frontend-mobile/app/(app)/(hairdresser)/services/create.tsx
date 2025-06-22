// app/(app)/(hairdresser)/services/create.tsx
import React from 'react';
import { View, Text, TextInput, TouchableOpacity, ScrollView } from 'react-native';
import Slider from '@react-native-community/slider';
import { styles } from '@/screens/hairdresser/service/styles/HaidresserServiceCreation'; // Adjust path
import { useServiceForm } from '@/hooks/hairdresserHooks/useServiceForms';

export default function ServiceCreationScreen() {
  const {
    name, setName,
    description, setDescription,
    duration, setDuration,
    price, setPrice,
    handleSubmit,
    handleBack,
    handleDurationChange
  } = useServiceForm();

  return (
    <View style={{ flex: 1, backgroundColor: '#FFEFE2' }}>
      <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
        <Text style={styles.title}>Novo Serviço</Text>
        
        <Text style={styles.label}>Nome do Serviço</Text>
        <TextInput style={styles.input} placeholder="Nome" value={name} onChangeText={setName} />

        <Text style={styles.label}>Descrição</Text>
        <TextInput style={[styles.input, styles.textarea]} placeholder="Descreva o serviço..." multiline value={description} onChangeText={setDescription} />

        <Text style={styles.label}>Tempo de Duração (em minutos)</Text>
        <TextInput
          style={styles.input} // You can reuse the standard input style
          placeholder="Ex: 60"
          keyboardType="numeric"
          // The value must be a string, so we convert the number state
          value={duration > 0 ? duration.toString() : ''}
          onChangeText={handleDurationChange}
        />
        
        <Text style={styles.label}>Valor</Text>
        <TextInput style={styles.valueInput} placeholder="R$" keyboardType="numeric" value={price} onChangeText={setPrice} />
        
        <View style={styles.footerButtons}>
          <TouchableOpacity style={styles.cancelButton} onPress={handleBack}>
            <Text style={styles.cancelText}>Voltar</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.saveButton} onPress={handleSubmit}>
            <Text style={styles.saveText}>Salvar</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </View>
  );
}