// app/(app)/(hairdresser)/services/edit/[id].tsx
import React from 'react';
import { View, Text, TextInput, TouchableOpacity, ScrollView, ActivityIndicator } from 'react-native';
import Slider from '@react-native-community/slider';
import { styles } from '@/styles/hairdresser/service/styles/HaidresserServiceCreation'; // Adjust path
import { useServiceForm } from '@/hooks/hairdresserHooks/useServiceForms';

export default function ServiceEditScreen() {
  const {
    loading,
    name, setName,
    description, setDescription,
    duration, setDuration,
    price, setPrice,
    handleSubmit,
    handleBack,
    handleDurationChange
  } = useServiceForm();

  if (loading) {
    return <ActivityIndicator size="large" style={{ flex: 1, justifyContent: 'center' }} />;
  }

  return (
    <View style={{ flex: 1, backgroundColor: '#FFEFE2' }}>
      <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
        <Text style={styles.title}>Editar Serviço</Text>
        
        <Text style={styles.label}>Nome do Serviço</Text>
        <TextInput style={styles.input} placeholder="Nome" value={name} onChangeText={setName} />

        <Text style={styles.label}>Descrição</Text>
        <TextInput style={[styles.input, styles.textarea]} placeholder="Descreva o serviço..." multiline value={description} onChangeText={setDescription} />

        <Text style={styles.label}>Tempo de Duração (em minutos)</Text>
        <TextInput
          style={styles.input}
          placeholder="Ex: 60"
          keyboardType="numeric"
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
            <Text style={styles.saveText}>Salvar Alterações</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </View>
  );
}