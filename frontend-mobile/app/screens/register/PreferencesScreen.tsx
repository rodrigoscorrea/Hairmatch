import React, { useState, useContext, useEffect } from 'react';
import { View, Text, Alert, TouchableOpacity, KeyboardAvoidingView, ScrollView, ActivityIndicator, Modal, Image } from 'react-native';
import { styles } from './styles/PreferencesStyle';
import { RouteProp, useNavigation, useRoute } from '@react-navigation/native';
import { AuthContext } from '../../index';
import { StackNavigationProp } from '@react-navigation/stack';
import { RootStackParamList } from '@/app/models/RootStackParams.types';
import { listPreferences } from '@/app/services/preferences.service';
import { Preference } from '@/app/models/Preferences.types';

type PreferencesScreenRouteProp = RouteProp<RootStackParamList, 'Preferences'>;
type PreferencesScreenNavigationProp = StackNavigationProp<RootStackParamList>;

export default function PreferencesScreen() {
  const navigation = useNavigation<PreferencesScreenNavigationProp>();
  const route = useRoute<PreferencesScreenRouteProp>();
  
  // Extract params from route
  const { personalData, addressData } = route.params;
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isFetchingPreferences, setIsFetchingPreferences] = useState<boolean>(true);
  const [preferences, setPreferences] = useState<Preference[]>([]);
  const [selectedPreferences, setSelectedPreferences] = useState<number[]>([]);
  const { signUp } = useContext<any>(AuthContext);
  const [showSkipModal, setShowSkipModal] = useState<boolean>(false);

  useEffect(() =>{
    const fetchPreferences = async () => {
        try{
            setIsFetchingPreferences(true);
            const response = await listPreferences();
            if(response && Array.isArray(response)) {
                setPreferences(response);
            }
        } catch (error){
            console.error('Error fetching preferences:', error);
            Alert.alert('Erro', 'Não foi possível carregar as preferências. Tente novamente.')
        } finally {
          setIsFetchingPreferences(false);
        }
    };

    fetchPreferences();
  }, []);

  const togglePreference = (id: number) => {
    setSelectedPreferences(prevSelected => {
        if(prevSelected.includes(id)){
            return prevSelected.filter(prefId => prefId != id);
        }else{
            return [...prevSelected, id];
        }
    });
  };

  const handleFinishRegistration = async () => {
    if (!personalData || !addressData) {
      Alert.alert('Erro', 'Informações de registro ausentes');
      return;
    }
  
    const { first_name, last_name, phone, email, password, role, cpf, cnpj } = personalData;
    const { address, number, complement, neighborhood, postal_code, city, state } = addressData;
  
    if (!first_name || !email || !password) {
      Alert.alert('Erro', 'Informações pessoais incompletas');
      return;
    }
  
    if (!address || !postal_code || !city || !state) {
      Alert.alert('Erro', 'Informações de endereço incompletas');
      return;
    }
  
    setIsLoading(true);
    try {
      await signUp(
        first_name, 
        last_name,
        phone, 
        email, 
        password, 
        address, 
        number,
        neighborhood, 
        complement, 
        postal_code, 
        state, 
        city, 
        role, 
        5.0,
        cpf, 
        cnpj,
        selectedPreferences
      );
    
      Alert.alert(
        'Sucesso', 
        'Cadastro realizado com sucesso! Faça login para continuar.',
        [{ text: 'OK', onPress: () => navigation.navigate('Login') }]
      );
    } catch (error: any) {
      console.error("Erro durante o processo de registro:", error);
    }
  };

  const handleSkip = () => {
    setShowSkipModal(true);
  }

  return (
    <KeyboardAvoidingView 
      style={styles.container}
    >
        <Modal
            visible={showSkipModal}
            transparent
            animationType="fade"
            >
            <View style={styles.modalOverlay}>
                <View style={styles.modalContainer}>
                <Text style={styles.modalTitle}>Personalize sua experiência no Hairmatch</Text>
                <Text style={styles.modalText}>
                    Selecionar suas preferências nos ajuda a recomendar cabeleireiros que combinam com o seu estilo.
                    Você pode pular essa etapa, mas isso afetará suas recomendações.
                </Text>
                <View style={styles.modalButtonGroup}>
                    <TouchableOpacity
                    style={styles.modalBackButton}
                    onPress={() => setShowSkipModal(false)}
                    >
                    <Text style={styles.modalBackButtonText}>Voltar</Text>
                    </TouchableOpacity>
                    <TouchableOpacity
                    style={styles.modalAcceptButton}
                    onPress={() => {
                        setShowSkipModal(false);
                        handleFinishRegistration();
                    }}
                    >
                    <Text style={styles.modalAcceptButtonText}>Aceitar</Text>
                    </TouchableOpacity>
                </View>
                </View>
            </View>
        </Modal>

      <ScrollView style={styles.scrollView} contentContainerStyle={styles.scrollContent}>
        {/* Header */}
        <View style={styles.header}>
          <Image source={require('../../../assets/images/HairmatchLogo.png')}></Image>
        </View>

        {/* Titulo e Legenda */}
        <View style={styles.titleContainer}>
          <Text style={styles.preferencesTitle}>Quais são as suas preferências?</Text>
          <Text style={styles.preferencesSubtitle}>
            Isso nos ajuda a encontrar os melhores matches para você!
          </Text>
        </View>

        {/* Preferences */}
        {isFetchingPreferences ? (
          <ActivityIndicator size="large"  style={styles.loader} />
        ) : (
          <View style={styles.preferencesContainer}>
            {preferences.map((preference) => (
              <TouchableOpacity
                key={preference.id}
                style={[
                  styles.preferenceButton,
                  selectedPreferences.includes(preference.id) && styles.preferenceButtonSelected
                ]}
                onPress={() => togglePreference(preference.id)}
              >
                {selectedPreferences.includes(preference.id) && (
                  <View style={styles.checkIcon}>
                    <Text style={styles.checkIconText}>✓</Text>
                  </View>
                )}
                <Text
                  style={[
                    styles.preferenceButtonText,
                    selectedPreferences.includes(preference.id) && styles.preferenceButtonTextSelected
                  ]}
                >
                  {preference.name}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        )}

        {/* Butoes de Baixo */}
        <View style={styles.buttonContainer}>
          <TouchableOpacity 
            style={styles.skipButton} 
            onPress={handleSkip}
            disabled={isLoading}
          >
            <Text style={styles.skipButtonText}>Pular</Text>
          </TouchableOpacity>
          
          <TouchableOpacity 
            style={styles.finishButton} 
            onPress={handleFinishRegistration}
            disabled={isLoading}
          >
            {isLoading ? (
              <ActivityIndicator size="small" />
            ) : (
              <Text style={styles.finishButtonText}>Finalizar</Text>
            )}
          </TouchableOpacity>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

