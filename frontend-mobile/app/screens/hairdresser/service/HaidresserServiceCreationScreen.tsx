import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Switch
} from 'react-native';
import Slider from '@react-native-community/slider';
import { useBottomTab } from '@/app/contexts/BottomTabContext';
import BottomTabBar from '@/app/components/BottomBar';
import { styles } from './styles/HaidresserServiceCreation';
import { createService } from '@/app/services/service.service';
import { RootStackParamList } from '@/app/models/RootStackParams.types';
import { StackNavigationProp } from '@react-navigation/stack';
import { useNavigation } from '@react-navigation/native';

type HairdresserServiceCreationScreenNavigationProp = StackNavigationProp<RootStackParamList>;

export default function HairdresserServiceCreationScreen() {
  const navigation = useNavigation<HairdresserServiceCreationScreenNavigationProp>();
  const { hairdresser, setActiveTab } = useBottomTab();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [duration, setDuration] = useState<number>(30);
  const [price, setPrice] = useState<string>('');

  useEffect(()=>{
    setActiveTab('HairdresserServiceManager');
  }, [])

  const handleCreateService = async () => {
    try {
      const data = {
        hairdresser: hairdresser?.id, 
        name:name, 
        description:description, 
        price: price, 
        duration: duration
      }
      await createService(data);
      navigation.navigate('HairdresserServiceManager');
    } catch(error) {
      console.log('Error while creating a service', error)
    }
  };

  return (
    <View style={{ flex: 1, backgroundColor: '#FFEFE2' }}>
      <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
        <Text style={styles.title}>Novo Serviço</Text>

        <Text style={styles.label}>Nome do Serviço</Text>
        <TextInput
          style={styles.input}
          placeholder="Nome"
          value={name}
          onChangeText={setName}
        />

        <Text style={styles.label}>Descrição do Serviço</Text>
        <TextInput
          style={[styles.input, styles.textarea]}
          placeholder="Descreva em detalhes como funciona o serviço, quais produtos você utiliza e etc"
          multiline
          value={description}
          onChangeText={setDescription}
        />

        <Text style={styles.label}>Tempo</Text>
        <View style={styles.sliderContainer}>
          <Slider
            style={{ flex: 1 }}
            minimumValue={10}
            maximumValue={240}
            step={5}
            value={duration}
            onValueChange={setDuration}
            minimumTrackTintColor="#FF8A00"
            maximumTrackTintColor="#000000"
          />
          <Text style={styles.durationLabel}>{duration}min</Text>
        </View>
        <Text style={styles.helperText}>Tempo médio de duração desse procedimento</Text>

        <Text style={styles.label}>Valor</Text>
        <TextInput
          style={styles.valueInput}
          placeholder="R$"
          keyboardType="numeric"
          value={price}
          onChangeText={(price) => setPrice(price)}
        />
        <View style={styles.footerButtons}>
          <TouchableOpacity style={styles.cancelButton} onPress={()=>navigation.navigate('HairdresserServiceManager')}>
            <Text style={styles.cancelText}>Voltar</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.saveButton} onPress={handleCreateService}>
            <Text style={styles.saveText}>Salvar</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
      <BottomTabBar/>
    </View>
  );
}
