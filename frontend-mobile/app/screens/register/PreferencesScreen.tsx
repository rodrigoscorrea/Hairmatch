import React, { useState, useContext, useEffect } from 'react';
import { View, Text, Alert, TouchableOpacity, StyleSheet, KeyboardAvoidingView, ScrollView, ActivityIndicator, Modal } from 'react-native';
import { RouteProp, useNavigation, useRoute } from '@react-navigation/native';
import { AuthContext, API_URL } from '../../index';
import { StackNavigationProp } from '@react-navigation/stack';
import { RootStackParamList } from '@/app/models/RootStackParams.types';
import axios from 'axios';

interface Preference {
    id: number;
    name: string;
}

// Define the route and navigation prop types
type PreferencesScreenRouteProp = RouteProp<RootStackParamList, 'Preferences'>;
type PreferencesScreenNavigationProp = StackNavigationProp<RootStackParamList>;


export default function PreferencesScreen() {
  // Use the hooks to get navigation and route
  const navigation = useNavigation<PreferencesScreenNavigationProp>();
  const route = useRoute<PreferencesScreenRouteProp>();
  
  // Extract params from route
  const { personalData, addressData } = route.params;
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isFetchingPreferences, setIsFetchingPreferences] = useState<boolean>(true);
  const [preferences, setPreferences] = useState<Preference[]>([]);
  const [selectedPreferences, setSelectedPreferences] = useState<number[]>([]);
  const { signUp, signIn } = useContext<any>(AuthContext);
  const [showSkipModal, setShowSkipModal] = useState<boolean>(false);

  useEffect(() =>{
    const fetchPreferences = async () => {
        try{
            setIsFetchingPreferences(true);
            const response = await axios.get(`${API_URL}/api/preferences/list`);
            if(response.data && Array.isArray(response.data)) {
                setPreferences(response.data);
            }
        } catch (error){
            console.error('Error fetching preferences:', error);
            Alert.alert('Erro', 'Não foi possível carregar as preferências. Tente novamente.')
        }finally {
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

  const assignPreferencesToUser = async (userId: number) => {
    try {
      // Para cada preferência selecionada, chamar a API de assign
      for (const preferenceId of selectedPreferences) {
        await axios.post(`${API_URL}/api/preferences/assign/${preferenceId}`,{
            user_id: userId,
        });
      }
      return true;
    } catch (error) {
      console.error('Error assigning preferences:', error);
      return false;
    }
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
        cnpj
      );
  
      await signIn(email, password); // logando
  
      // Se tem preference vamos atribuí-las 
      if (selectedPreferences.length > 0) {
        try {
          const userResponse = await axios.get(`${API_URL}/api/user/authenticated`, {
            headers: {
              'Accept': 'application/json'
            }
          });
          
          // Extraindo Id do usuario baseado no role
          let userId = null;
          if (role === 'customer' && userResponse.data.customer) {
            userId = userResponse.data.customer.user.id;
          } else if (role === 'hairdresser' && userResponse.data.hairdresser) {
            userId = userResponse.data.hairdresser.user.id;
          }
          
          if (userId) {
            await assignPreferencesToUser(userId);
          } else {
            console.error("Não foi possível obter o ID do usuário");
          }
        } catch (userError) {
          console.error("Erro ao buscar informações do usuário:", userError);
        }
      }
  
      Alert.alert(
        'Sucesso', 
        'Cadastro realizado com sucesso! Faça login para continuar.',
        [{ text: 'OK', onPress: () => navigation.navigate('Login') }]
      );
    } catch (error: any) {
      console.error("Erro durante o processo de registro:", error);
      
      // Tratamento de erros
      let errorMessage = 'Falha no registro';
      
      if (error.response) {
        // O servidor respondeu com um status de erro
        console.error('Resposta de erro do servidor:', error.response.data);
        errorMessage = error.response.data?.error || 'Erro no servidor';
        
        // Se for um erro HTML, mostrar mensagem genérica
        if (typeof error.response.data === 'string' && 
            error.response.data.includes('<!DOCTYPE html>')) {
          errorMessage = 'Erro de comunicação com o servidor';
        }
      } else if (error.request) {
        console.error('Sem resposta do servidor');
        errorMessage = 'Sem resposta do servidor. Verifique sua conexão.';
      } else {
        console.error('Erro de configuração:', error.message);
        errorMessage = `Erro: ${error.message}`;
      }
      Alert.alert('Erro', errorMessage);
    } finally {
      setIsLoading(false);
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
          <Text style={styles.title}>HairMatch</Text>
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