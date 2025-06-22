import React, { useState } from 'react';
import { View, Text, TextInput, StyleSheet, TouchableOpacity, ScrollView } from 'react-native';
import { RootStackParamList } from '@/app/models/RootStackParams.types';
import { RouteProp, useNavigation, useRoute } from '@react-navigation/native';
import { StackNavigationProp } from '@react-navigation/stack';

type ProfessionalStoryScreenRouteProp = RouteProp<RootStackParamList, 'ProfessionalStory'>;
type ProfessionalStoryScreenNavigationProp = StackNavigationProp<RootStackParamList>;

const ProfessionalStoryScreen = () => {
  const [experience_time, setExperienceTime] = useState('');
  const [experiences, setExperiences] = useState('');
  const [products, setProducts] = useState('');
  const navigation = useNavigation<ProfessionalStoryScreenNavigationProp>();
  const route = useRoute<ProfessionalStoryScreenRouteProp>();
  const { personalData, addressData, preferences } = route.params;
  const handleCancel = () => {
    console.log('Canceled');
  };

  const handleNext = () => {
    navigation.navigate('Description', {
      personalData: personalData, 
      addressData: addressData,
      preferences: preferences,
      professionalStory: {experience_time, experiences, products}
    })
  };

  const clearForms = () => {
    setExperienceTime('');
    setExperiences('');
    setProducts('');
  }

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
        value={experience_time}
        onChangeText={setExperienceTime}
        multiline
      />

      <Text style={styles.label}>Conte um pouco sobre suas experiências anteriores.</Text>
      <TextInput
        style={styles.input}
        placeholder="Quanto mais detalhes você compartilhar, melhor será o seu resumo!"
        value={experiences}
        onChangeText={setExperiences}
        multiline
      />

      <Text style={styles.label}>Quais marcas de produto você costuma usar?</Text>
      <TextInput
        style={styles.input}
        placeholder="Ex: Wella, Arvensis, Keraste"
        value={products}
        onChangeText={setProducts}
        multiline
      />

      <View style={styles.buttonContainer}>
        <TouchableOpacity style={styles.cancelButton} onPress={handleCancel}>
          <Text style={styles.cancelText}>Cancelar</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.finishButton} onPress={() => {clearForms() ; handleNext()}}>
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
