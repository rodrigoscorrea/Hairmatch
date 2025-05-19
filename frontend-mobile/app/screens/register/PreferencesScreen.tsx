import React, { useState, useContext, useEffect } from 'react';
import { View, Text, Alert, TouchableOpacity, StyleSheet, KeyboardAvoidingView, ScrollView, ActivityIndicator, Modal, Image } from 'react-native';
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
          <ActivityIndicator size="large" color="#FF6B00" style={styles.loader} />
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
              <ActivityIndicator size="small" color="#FFF" />
            ) : (
              <Text style={styles.finishButtonText}>Finalizar</Text>
            )}
          </TouchableOpacity>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FFECE3',
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    padding: 20,
    paddingBottom: 40,
  },
  header: {
    marginTop: 60,
    alignItems: 'center',
  },
  title: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#FF6B00',
  },
  titleContainer: {
    marginTop: 30,
    marginBottom: 20,
  },
  preferencesTitle: {
    fontSize: 20,
    fontWeight: '600',
    color: '#333',
  },
  preferencesSubtitle: {
    fontSize: 14,
    color: '#666',
    marginTop: 5,
  },
  loader: {
    marginVertical: 40,
  },
  preferencesContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'flex-start',
    marginTop: 20,
  },
  preferenceButton: {
    backgroundColor: '#fff',
    borderRadius: 20,
    paddingHorizontal: 15,
    paddingVertical: 8,
    margin: 5,
    borderWidth: 1,
    borderColor: '#ddd',
    flexDirection: 'row',
    alignItems: 'center',
  },
  preferenceButtonSelected: {
    backgroundColor: '#FFF0E6',
    borderColor: '#FF6B00',
  },
  preferenceButtonText: {
    color: '#333',
    fontSize: 14,
  },
  preferenceButtonTextSelected: {
    color: '#FF6B00',
    fontWeight: '500',
  },
  checkIcon: {
    marginRight: 5,
  },
  checkIconText: {
    color: '#FF6B00',
    fontWeight: 'bold',
  },
  buttonContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 40,
    paddingHorizontal: 10,
  },
  skipButton: {
    backgroundColor: '#FFF',
    borderRadius: 10,
    paddingVertical: 15,
    paddingHorizontal: 30,
    flex: 1,
    marginRight: 10,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 3,
    elevation: 2,
  },
  skipButtonText: {
    color: '#9B59B6',
    fontWeight: '500',
    fontSize: 16,
  },
  finishButton: {
    backgroundColor: '#FF6B00',
    borderRadius: 10,
    paddingVertical: 15,
    paddingHorizontal: 30,
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 3,
    elevation: 3,
  },
  finishButtonText: {
    color: '#FFF',
    fontWeight: '700',
    fontSize: 16,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  modalContainer: {
    backgroundColor: '#FFECE3',
    borderRadius: 20,
    padding: 20,
    width: '100%',
    maxWidth: 320,
    alignItems: 'center',
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: '600',
    textAlign: 'center',
    marginBottom: 10,
    color: '#333',
  },
  modalText: {
    fontSize: 14,
    textAlign: 'center',
    color: '#555',
    marginBottom: 20,
  },
  modalButtonGroup: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    width: '100%',
  },
  modalBackButton: {
    backgroundColor: '#fff',
    borderRadius: 10,
    paddingVertical: 10,
    paddingHorizontal: 20,
    borderColor: '#9B59B6',
    borderWidth: 1,
    marginRight: 10,
    flex: 1,
    alignItems: 'center',
  },
  modalBackButtonText: {
    color: '#9B59B6',
    fontWeight: '500',
  },
  modalAcceptButton: {
    backgroundColor: '#FF6B00',
    borderRadius: 10,
    paddingVertical: 10,
    paddingHorizontal: 20,
    flex: 1,
    alignItems: 'center',
  },
  modalAcceptButtonText: {
    color: '#fff',
    fontWeight: '600',
  },

});