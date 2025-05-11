import React, { useState, useEffect } from 'react';
import { View, Text, TouchableOpacity, ScrollView, StyleSheet, Alert, Button } from 'react-native';
import { RootStackParamList } from '@/app/models/RootStackParams.types';
import { RouteProp, useNavigation, useRoute } from '@react-navigation/native';
import { StackNavigationProp } from '@react-navigation/stack';
import { Calendar, LocaleConfig } from 'react-native-calendars';
import { ptBR } from '@/app/utils/locale-calendar';
import { getAvailableResearchSlots } from '@/app/services/reserve.service';
import { createReserve } from '@/app/services/reserve.service';

type ServiceReserveScreenRouteProp = RouteProp<RootStackParamList, 'ServiceBooking'>;
type ServiceReserveScreenNavigationProp = StackNavigationProp<RootStackParamList>;

LocaleConfig.locales["pt-br"] = ptBR;
LocaleConfig.defaultLocale = "pt-br";

const hairLengths = [
  { label: 'Curto', price: 120 },
  { label: 'Médio', price: 125 },
  { label: 'Longo', price: 130 },
];

export default function ServiceBookingScreen() {
  const navigation = useNavigation<ServiceReserveScreenNavigationProp>();
  const route = useRoute<ServiceReserveScreenRouteProp>();
  
  const service = route.params?.service;
  const customer_id = route.params?.customer_id;
  const non_working_days = route.params?.non_working_days

  const [selectedLength, setSelectedLength] = useState<string>('Curto');
  const [selectedTime, setSelectedTime] = useState<string | null>(null);
  const [showCalendar, setShowCalendar] = useState<boolean>(false);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [markedDates, setMarkedDates] = useState<any>({});
  const [availableReserveSlots, setAvailableReserveSlots] = useState<string[]>();
  const [isLoading, setIsLoading] = useState<boolean>(false);
  
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
    markSundaysAsDisabled();
  }, []);

  useEffect(() => {
    const fetchAvailableResearchSlots = async () => {
      if(!selectedDate) return; 
      const availableReserveSlotsResponse = await getAvailableResearchSlots(1, service.id, selectedDate!);
      setAvailableReserveSlots(availableReserveSlotsResponse.available_slots)
    }

    fetchAvailableResearchSlots();
  }, [selectedDate]);

  const markSundaysAsDisabled = () => {
    const startDate = new Date(initialDate);
    const endDate = new Date(initialDate);
    endDate.setFullYear(endDate.getFullYear() + 1); // Mark Sundays for a year ahead
    
    const marked: any = {};

    for(let non_working_day of non_working_days){
        let currentDate = new Date(startDate);
        while (currentDate <= endDate) {            
            if (currentDate.getDay() === non_working_day) { // Check if the day is Sunday (0 = Sunday, 1 = Monday, etc.)
                const dateString: string = currentDate.toISOString().split('T')[0];
                marked[dateString] = { 
                disabled: true, 
                disableTouchEvent: true,
                textColor: 'gray',
                color: '#e0e0e0'
                };
            }
            currentDate.setDate(currentDate.getDate() + 1);
        }
    }
    setMarkedDates(marked);
  };

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
      hairdresser: 1,
      start_time: formatedTime,
    }
    console.log(reserveData)
    try{
       createReserveRequest(reserveData);
       navigation.navigate('Home');
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
            markedDates={markedDates}
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
      <Text style={styles.title}>{service.name}</Text>
      <Text style={styles.description}>
        {service.description}
      </Text>

      <Text style={styles.sectionTitle}>Valores</Text>
      {hairLengths.map(({ label, price }) => (
        <TouchableOpacity
          key={label}
          style={styles.option}
          onPress={() => setSelectedLength(label)}
        >
          <Text style={styles.optionText}>{label} R${price}</Text>
          {selectedLength === label && <Text style={styles.check}>✔️</Text>}
        </TouchableOpacity>
      ))}

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
          onPress={handleBooking}
        >
          <Text style={styles.buttonText}>Agendar</Text>
        </TouchableOpacity>
      )}
      
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: 16,
    backgroundColor: '#FFF8F2',
  },
  title: {
    fontSize: 22,
    fontWeight: 'bold',
  },
  description: {
    fontSize: 14,
    marginTop: 6,
    marginBottom: 12,
    color: '#333',
  },
  sectionTitle: {
    fontWeight: 'bold',
    fontSize: 16,
    marginTop: 20,
  },
  option: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderColor: '#eee',
  },
  optionText: {
    fontSize: 16,
  },
  check: {
    fontSize: 16,
    color: '#f08000',
  },
  date: {
    fontSize: 16,
    color: '#555',
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderColor: '#eee',
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginTop: 12,
    gap: 10,
  },
  selectedTimeSlot: {
    width: '22%',
    padding: 10,
    borderWidth: 1,
    borderColor: '#4E2F5D',
    backgroundColor: '#FC7C25',
    borderRadius: 8,
    alignItems: 'center',
  },
  timeSlot: {
    width: '22%',
    padding: 10,
    borderWidth: 1,
    borderColor: '#4E2F5D',
    backgroundColor: '#F5F5F5',
    borderRadius: 8,
    alignItems: 'center',
  },
  selectedTimeText: {
    fontSize: 14,
    color: 'white'
  },
  timeText: {
    fontSize: 14,
    color: 'black'
  },
  button: {
    backgroundColor: '#FF914D',
    paddingVertical: 14,
    borderRadius: 10,
    marginTop: 30,
    alignItems: 'center',
  },
  buttonText: {
    color: 'white',
    fontWeight: 'bold',
    fontSize: 16,
  },
  monthHeader: {
    width: '100%',
    paddingVertical: 10,
    paddingHorizontal: 15,
    backgroundColor: '#f0f0f0',
    borderBottomWidth: 1,
    borderBottomColor: '#ddd',
  },
  monthText: {
    fontSize: 18,
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: 5,
  },
  monthNavigation: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: 10,
  },
});
