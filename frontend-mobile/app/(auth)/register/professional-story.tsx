import React from 'react';
import { View, Text, TextInput, StyleSheet, TouchableOpacity, ScrollView } from 'react-native';
import { useProfessionalStoryForm } from '../../../hooks/authHooks/useProfessionalStory'; // Adjust path


const ProfessionalStoryScreen = () => {
  const { formData, handleInputChange, handleNext, handleBack } = useProfessionalStoryForm();
  const handleCancel = () => {
    console.log('Canceled');
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>Conte sobre sua trajetória profissional</Text>
      <Text style={styles.subtitle}>
        As informações que você preencher aqui serão usadas para criar automaticamente um resumo profissional personalizado que será exibido no seu perfil.
      </Text>

      <Text style={styles.label}>Há quanto tempo você trabalha na sua área?</Text>
      <TextInput
        style={styles.input}
        placeholder="Ex: 5 anos como cabeleireira"
        value={formData.experience_time}
        onChangeText={(text) => handleInputChange('experience_time', text)}
        multiline
      />

      <Text style={styles.label}>Conte um pouco sobre suas experiências anteriores.</Text>
      <TextInput
        style={styles.input}
        placeholder="Quanto mais detalhes você compartilhar, melhor será o seu resumo!"
        value={formData.experiences}
        onChangeText={(text) => handleInputChange('experiences', text)}
        multiline
      />

      <Text style={styles.label}>Quais marcas de produto você costuma usar?</Text>
      <TextInput
        style={styles.input}
        placeholder="Ex: Wella, Arvensis, Keraste"
        value={formData.products}
        onChangeText={(text) => handleInputChange('products', text)}
        multiline
      />

      <View style={styles.buttonContainer}>
        <TouchableOpacity style={styles.cancelButton} onPress={handleBack}>
          <Text style={styles.cancelText}>Cancelar</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.finishButton} onPress={handleNext}>
          <Text style={styles.finishText}>Próximo</Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
};

export default ProfessionalStoryScreen;

const styles = StyleSheet.create({
  container: {
    padding: 20,
    backgroundColor: '#FFEFE5',
    flexGrow: 1,
  },
  title: {
    fontSize: 16,
    fontWeight: '600',
    textAlign: 'center',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 12,
    textAlign: 'center',
    color: '#555',
    marginBottom: 24,
  },
  label: {
    fontSize: 14,
    fontWeight: '500',
    marginBottom: 8,
    color: '#000',
  },
  input: {
    backgroundColor: '#fff',
    borderRadius: 8,
    padding: 12,
    marginBottom: 20,
    textAlignVertical: 'top',
    borderColor: '#ddd',
    borderWidth: 1,
  },
  buttonContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 12,
  },
  cancelButton: {
    backgroundColor: '#E5E0F8',
    paddingVertical: 12,
    paddingHorizontal: 24,
    borderRadius: 8,
  },
  finishButton: {
    backgroundColor: '#FF7A00',
    paddingVertical: 12,
    paddingHorizontal: 24,
    borderRadius: 8,
  },
  cancelText: {
    color: '#4B0082',
    fontWeight: '600',
  },
  finishText: {
    color: '#fff',
    fontWeight: '600',
  },
});
