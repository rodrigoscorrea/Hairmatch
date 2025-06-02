import React, {useState, useEffect} from 'react';
import { View, Text, ScrollView, TouchableOpacity, ActivityIndicator } from 'react-native';
import { Accordion } from '../../../components/Accordion'
import { Ionicons, MaterialIcons } from '@expo/vector-icons';
import { styles } from './styles/HairdresserServiceManager';
import { ServiceResponse } from '@/app/models/Service.types';
import { useBottomTab } from '@/app/contexts/BottomTabContext';
import { listServicesByHairdresser } from '@/app/services/service.service';
import { serviceTimeFormater } from '@/app/utils/serviceTime-formater';

const HairdresserServiceManageScreen = () => {
  
  const [services, setServices] = useState<ServiceResponse[]>(); 
  const { hairdresser, setActiveTab } = useBottomTab();
  const [isLoading, setIsLoading] = useState<boolean>(false);

  useEffect(()=>{
    const fetchHairdresserService = async () => {
        try {
            setIsLoading(true);
            const serviceResponse = await listServicesByHairdresser(hairdresser?.id);
            setServices(serviceResponse.data);
        } catch (err) {
            console.log("Failed to fetch Hairdresser Services", err);
        } finally {
            setIsLoading(false);
        }
    }
    setActiveTab('HairdresserServiceManager');
    fetchHairdresserService();
  }, []);

  return (
    <View style={{ flex: 1 }}>
        <ScrollView style={styles.container}>
        <Text style={styles.title}>Seus Serviços</Text>
        
        {services ? (
            isLoading ? (
            <View>
                <ActivityIndicator size="large" color="#000" />
                <Text>Carregando informações...</Text>
            </View>
            ) : (
            <>
                {services.map((service) => (
                <Accordion key={service.id} title={service.name}>
                    <View style={styles.card}>
                    <View style={styles.cardHeader}>
                        <Text style={styles.serviceTitle}>{service.name}</Text>
                        <View style={styles.iconRow}>
                        <TouchableOpacity>
                            <Ionicons name="trash-outline" size={18} color="#000" />
                        </TouchableOpacity>
                        <TouchableOpacity style={{ marginLeft: 10 }}>
                            <Ionicons name="pencil-outline" size={18} color="#000" />
                        </TouchableOpacity>
                        </View>
                    </View>

                    <Text style={styles.label}>
                        Tempo Médio de Duração: <Text style={styles.bold}>{serviceTimeFormater(service.duration)}</Text>
                    </Text>

                    <View style={{ marginTop: 5 }}>
                        <Text>Valor: <Text style={styles.bold}>R$ {service.price}</Text></Text>
                    </View>

                    <Text style={styles.label}>
                        Descrição: <Text style={styles.description}>{service.description}</Text>
                    </Text>
                    </View>
                </Accordion>
                ))}
            </>
            )
        ) : (
            <View>
            <Text>Não há serviços cadastrados para este usuário</Text>
            </View>
        )}
        </ScrollView>

        <TouchableOpacity style={styles.addButton}>
        <Ionicons name="add" size={28} color="#000" />
        </TouchableOpacity>
    </View>
    );
};

export default HairdresserServiceManageScreen;
