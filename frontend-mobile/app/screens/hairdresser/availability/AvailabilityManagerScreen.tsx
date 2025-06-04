import React, {useState, useEffect} from 'react';
import { View, Text, ScrollView, TouchableOpacity, ActivityIndicator } from 'react-native';
import { Accordion } from '../../../components/Accordion'
import { Ionicons, MaterialIcons } from '@expo/vector-icons';
import { useBottomTab } from '@/app/contexts/BottomTabContext';
import { RootStackParamList } from '@/app/models/RootStackParams.types';
import { StackNavigationProp } from '@react-navigation/stack';
import { RouteProp, useNavigation, useRoute } from '@react-navigation/native';
import BottomTabBar from '@/app/components/BottomBar';
import { styles } from './styles/AvailabilityManagerStyles';
import { formatAvailability } from '@/app/utils/availability-formater';
import { NonWorkingDays } from '@/app/models/Availability.types';
import { AvailabilityResponse } from '@/app/models/Availability.types';
import { listAvailabilitiesByHairdresser } from '@/app/services/availability.service';

type AvailabilityManagerScreenRouteProp = RouteProp<RootStackParamList, 'AvailabilityManager'>;
type AvailabilityManagerScreenNavigationProp = StackNavigationProp<RootStackParamList>;

const AvailabilityManageScreen = () => {
  const navigation = useNavigation<AvailabilityManagerScreenNavigationProp>();
  const route = useRoute<AvailabilityManagerScreenRouteProp>();
  const { hairdresser, setActiveTab } = useBottomTab();
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [availabilities, setAvailabilities] = useState<AvailabilityResponse[]>();
  const [nonWorkingDays, setNonWorkingDays] = useState<NonWorkingDays>();

  useEffect(()=>{
    const fetchHairdresserAvailability = async () => {
        try {
            const availabilityResponse = await listAvailabilitiesByHairdresser(hairdresser?.id)
            setAvailabilities(availabilityResponse.data);
            setNonWorkingDays(availabilityResponse.non_working_days)
        } catch (err) {
            console.log("Failed to fetch Hairdresser Availabilities", err)
        }
    }
    fetchHairdresserAvailability();
    setActiveTab('HairdresserServiceManager');
  }, []);
 
  return (
    <View style={{ flex: 1 }}>
        <ScrollView style={styles.container}>
        <Text style={styles.title}>Meus Horários de Atendimento</Text>
        
        {availabilities ?  (
            isLoading ? (
                <View>
                    <ActivityIndicator size="large" color="#000" />
                    <Text>Carregando informações...</Text>
                </View>
            ) : (
            <>
                {availabilities.map((availability: any) => {
                    const formatted = formatAvailability(availability);
                    return (
                    <View key={availability.id} style={styles.availabilityRow}>
                        <Text style={styles.weekday}>{formatted.weekday}</Text>
                        <Text style={styles.timeRange}>{formatted.timeRange}</Text>
                    </View>
                    );
                })}
            </>
            )
        ) : (
            <View>
                <Text>Não há horários de atendimento cadastrados para este usuário</Text>
            </View>
        )}
        </ScrollView>
        
        {availabilities && availabilities.length > 0 && (
            <TouchableOpacity style={styles.addButton} 
            onPress={()=>navigation.navigate('AvailabilityEdit', 
                {
                    availabilities: availabilities, 
                    nonWorkingDays: nonWorkingDays
                }
            )}
            >
                <Ionicons name="filter" size={28} color="#000" />
            </TouchableOpacity>
        )}

        {availabilities && availabilities.length == 0 && (
            <TouchableOpacity style={styles.addButton} onPress={()=>navigation.navigate('AvailabilityCreate')}>
                <Ionicons name="add" size={28} color="#000" />
            </TouchableOpacity>
        )}

        <BottomTabBar/>
    </View>
    );
};

export default AvailabilityManageScreen;
