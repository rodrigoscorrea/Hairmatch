import React, { useState, useEffect, useMemo } from 'react';
import { View, Text, TouchableOpacity, ScrollView, Alert, Modal } from 'react-native';
import { styles } from './styles/ServiceReservationStyle';
import { RootStackParamList } from '@/app/models/RootStackParams.types';
import { RouteProp, useNavigation, useRoute } from '@react-navigation/native';
import { StackNavigationProp } from '@react-navigation/stack';
import { Calendar, LocaleConfig } from 'react-native-calendars';
import { ptBR } from '@/app/utils/locale-calendar';
import { getAvailableResearchSlots } from '@/app/services/reserve.service';
import { createReserve } from '@/app/services/reserve.service';
import FontAwesome6 from '@expo/vector-icons/FontAwesome6';
import { serviceTimeFormater } from '@/app/utils/serviceTime-formater';
import { formatDate } from '@/app/utils/date-formater';
import { listAvailabilitiesByHairdresser } from '@/app/services/availability.service';
import { useBottomTab } from '@/app/contexts/BottomTabContext';
import BottomTabBar from '@/app/components/BottomBar';

type ServiceReserveScreenRouteProp = RouteProp<RootStackParamList, 'ServiceBooking'>;
type ServiceReserveScreenNavigationProp = StackNavigationProp<RootStackParamList>;

LocaleConfig.locales["pt-br"] = ptBR;
LocaleConfig.defaultLocale = "pt-br";

export default function ServiceBookingScreen() {
  const navigation = useNavigation<ServiceReserveScreenNavigationProp>();
  const route = useRoute<ServiceReserveScreenRouteProp>();
  const { setActiveTab } = useBottomTab();
  const service = route.params?.service;
  const customer_id = route.params?.customer_id;
  const hairdresser = route.params?.hairdresser
  
  const [selectedServiceOption, setSelectedServiceOption] = useState<any>();
  const [selectedTime, setSelectedTime] = useState<string | null>(null);
  const [showCalendar, setShowCalendar] = useState<boolean>(false);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [availableReserveSlots, setAvailableReserveSlots] = useState<string[]>();
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [nonWorkingDays, setNonWorkingDays] = useState<number[]>([]);
  const [showReserveConfirmationModal, setShowReserveConfirmationModal] = useState<boolean>(false);
  
  const getCurrentDate = () => {
    const today = new Date();
    return today.toISOString().split('T')[0];
  };

  const getMaxDate = () => {
    const maxDate = new Date();
    maxDate.setFullYear(maxDate.getFullYear() + 1);
    return maxDate.toISOString().split('T')[0];
  }
  
  const initialDate: string = getCurrentDate();
  const maxDate: string = getMaxDate();

  useEffect(() => {
    const fetchHairdresserAvailability = async () => {
      try {
        const availabilityResponse = await listAvailabilitiesByHairdresser(hairdresser.id)
        setNonWorkingDays(availabilityResponse.non_working_days)
      } catch (err) {
        console.log("Failed to fetch Hairdresser Availabilities", err)
      }
    }
    fetchHairdresserAvailability();
    setActiveTab('Search')
  }, []);

  useEffect(() => {
    const fetchAvailableResearchSlots = async () => {
      if(!selectedDate) return; 
      const availableReserveSlotsResponse = await getAvailableResearchSlots(hairdresser.id, service.id, selectedDate!);
      setAvailableReserveSlots(availableReserveSlotsResponse.available_slots)
    }

    fetchAvailableResearchSlots();
  }, [selectedDate]);

  const memorizedMarkedDates = useMemo(() => {
        const startDate = new Date(initialDate);
        const endDate = new Date(maxDate);
        const marked: any = {};

        if (nonWorkingDays.length > 0) {
            let currentDate = new Date(startDate);
            while (currentDate <= endDate) {
                if (nonWorkingDays.includes(currentDate.getDay())) {
                    const dateString = currentDate.toISOString().split('T')[0];
                    marked[dateString] = {
                        disabled: true,
                        disableTouchEvent: true,
                        textColor: 'gray',
                    };
                }
                currentDate.setDate(currentDate.getDate() + 1);
            }
        }
        if (selectedDate) {
            marked[selectedDate] = {
                ...marked[selectedDate],
                selected: true,
                selectedColor: '#F06543'
            };
        }

        return marked;
    }, [nonWorkingDays, selectedDate, initialDate, maxDate]);

  const formatStartTime = (selectedDate: string, selectedTime: string): string => {
    let formatedTime: string = `${selectedDate}T${selectedTime}:00`;
    return formatedTime;
  }

  const createReserveRequest = async (data: any) => {
    await createReserve(data);
  }

  const handleBooking = () => {
    if (!selectedTime) return;

    let formatedTime = formatStartTime(selectedDate!, selectedTime);
    let reserveData = {
      customer: customer_id,
      service: service.id,
      hairdresser: hairdresser.id,
      start_time: formatedTime,
    }
    try{
       createReserveRequest(reserveData);
       navigation.navigate('CustomerHome');
       Alert.alert("Reserva concluida com sucesso :D");
    } catch (err) {
      Alert.alert("Aconteceu um problema, verifique os logs")
    }
   
  };

  const renderCalendar = () => {
    return (
        <View >
          <Calendar 
            hideExtraDays
            minDate={initialDate}
            maxDate={maxDate}
            markedDates={memorizedMarkedDates}
            theme={{
                arrowColor: '#F06543',
                disabledArrowColor: '#d9e1e8',
                monthTextColor: '#000000',
                dayTextColor: '#000000',
                selectedDayBackgroundColor: '#F06543',
                selectedDayTextColor: '#E8E8E8',
                todayTextColor: '#F06543'
            }}
            onDayPress={(event: any)=> {setSelectedDate(event.dateString)}}>

          </Calendar>
        </View>
      );
    };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <View style={styles.titleContainer}>  
        <Text style={styles.title}>{service.name}</Text>
        <View style={styles.clockIconContainer}>
          <FontAwesome6 style={styles.clockIcon} name="clock" size={18} color="black" />
          <Text style={[styles.title, {marginLeft: 5, fontSize:18}]}>{serviceTimeFormater(service.duration)}</Text>
        </View>
        
      </View>
      
      <Text style={styles.description}>
        {service.description}
      </Text>

      <Text style={styles.hairdresserName}>
        Profissional: {hairdresser.user.first_name} {hairdresser.user.last_name}
      </Text>

      <Text style={styles.sectionTitle}>Valor</Text>
      {service && (
        <>
          <TouchableOpacity
            key={service.name}
            style={styles.option}
            onPress={()=>{setSelectedServiceOption(service.name)}}
          >
            <Text style={styles.optionText}>R$ {service.price}</Text>
            {/* {selectedServiceOption === service.name && <Text style={styles.check}>✔️</Text>} */}
          </TouchableOpacity>
        </>
      )}

      <TouchableOpacity onPress={()=>{setShowCalendar(true)}} style={styles.button}>
        <Text style={styles.buttonText}>Selecione uma data</Text>
      </TouchableOpacity>

      {showCalendar && renderCalendar()}

       {selectedDate && (
        <>
          <Text style={styles.sectionTitle}>Horários disponíveis</Text>
          
          {isLoading ? (
            <Text>Carregando horários disponíveis...</Text>
          ) : (
            <View style={styles.grid}>
              {availableReserveSlots && availableReserveSlots.length > 0 ? (
                availableReserveSlots.map((slot) => (
                  <TouchableOpacity
                    key={slot}
                    style={[ 
                      styles.timeSlot,
                      selectedTime === slot && styles.selectedTimeSlot
                    ]}
                    onPress={() => setSelectedTime(slot)}
                  >
                    <Text style={[
                      styles.timeText,
                      selectedTime === slot && styles.selectedTimeText]}>
                      {slot}
                    </Text>
                  </TouchableOpacity>
                ))
              ) : (
                <Text>Não há horários disponíveis nesta data</Text>
              )}
            </View>
          )}
        </>
      )}

      {selectedDate && (
        <TouchableOpacity
          style={[
            styles.button,
            !selectedTime && { opacity: 0.5 },
          ]}
          disabled={!selectedTime}
          onPress={()=>setShowReserveConfirmationModal(true)}
        >
          <Text style={styles.buttonText}>Agendar</Text>
        </TouchableOpacity>
      )}

    <Modal
        visible={showReserveConfirmationModal}
        transparent
        animationType="fade"
        >
        <View style={styles.modalOverlay}>
            <View style={styles.modalContainer}>
            <Text style={styles.modalTitle}>Confirmar agendamento</Text>
            <Text style={styles.modalText}>
                Cheque todos os dados sobre seu agendamento abaixo e clique em Confirmar Agendamento para prosseguir.
            </Text>
            <View style={styles.modalReserveInformations}>
              <Text >Serviço selecionado: {service.name}</Text> 
              <Text >Data de realização do serviço: {formatDate(selectedDate)}</Text>
              <Text >Horário de realização do serviço: {selectedTime}</Text>
              <Text >Valor do serviço: R$ {service.price}</Text>
            </View>
            <View style={styles.modalButtonGroup}>
                <TouchableOpacity
                style={styles.modalBackButton}
                onPress={() => setShowReserveConfirmationModal(false)}
                >
                <Text style={styles.modalBackButtonText}>Voltar</Text>
                </TouchableOpacity>
                <TouchableOpacity
                style={styles.modalAcceptButton}
                onPress={() => {
                    setShowReserveConfirmationModal(false);
                    handleBooking();
                }}
                >
                <Text style={styles.modalAcceptButtonText}>Aceitar</Text>
                </TouchableOpacity>
            </View>
            </View>
        </View>
      </Modal>
      <BottomTabBar/>
    </ScrollView>
  );
}

