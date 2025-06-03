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
import { createService, editService } from '@/app/services/service.service';
import { RootStackParamList } from '@/app/models/RootStackParams.types';
import { StackNavigationProp } from '@react-navigation/stack';
import { useNavigation, RouteProp, useRoute } from '@react-navigation/native';
import { serviceTimeFormater } from '@/app/utils/serviceTime-formater';

type HairdresserServiceEditScreenNavigationProp = StackNavigationProp<RootStackParamList>;
type HairdresserServiceEditScreenRouteProp = RouteProp<RootStackParamList, 'HairdresserServiceEdit'>;

export default function HairdresserServiceEditScreen() {
  const navigation = useNavigation<HairdresserServiceEditScreenNavigationProp>();
  const route = useRoute<HairdresserServiceEditScreenRouteProp>();
  const { hairdresser, setActiveTab } = useBottomTab();
  const [name, setName] = useState<string>(route.params?.service.name);
  const [description, setDescription] = useState<string>(route.params?.service.description);
  const [duration, setDuration] = useState<number>(route.params?.service.duration);
  const [price, setPrice] = useState<string>(route.params?.service.price);
  const serviceId = route.params?.service.id;

  useEffect(()=>{
    setActiveTab('HairdresserServiceManager');
  }, [])

  const handleEditionService = async () => {
    try {
      const data = {
        id: serviceId,
        hairdresser: hairdresser?.id, 
        name:name, 
        description:description, 
        price: price, 
        duration: duration
      }
      await editService(data);
      navigation.navigate('HairdresserServiceManager');
    } catch(error) {
      console.log('Error while editing a service', error)
    }
  };

  return (
    <View style={{ flex: 1, backgroundColor: '#FFEFE2' }}>
      <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
        <Text style={styles.title}>Editar Serviço</Text>

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
          <TouchableOpacity style={styles.saveButton} onPress={handleEditionService}>
            <Text style={styles.saveText}>Salvar</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
      <BottomTabBar/>
    </View>
  );
}
