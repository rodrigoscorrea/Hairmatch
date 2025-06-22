import React from 'react';
import { View, Text, TouchableOpacity, ScrollView, Alert, Modal, ActivityIndicator } from 'react-native';
import { styles } from '@/styles/customer/reservation/styles/ServiceReservationStyle'; // Adjust path
import { Calendar, LocaleConfig } from 'react-native-calendars';
import { ptBR } from '@/utils/locale-calendar'; // Adjust path
import FontAwesome6 from '@expo/vector-icons/FontAwesome6';
import { serviceTimeFormater } from '@/utils/serviceTime-formater'; // Adjust path
import { useServiceBooking } from '@/hooks/customerHooks/useServiceBooking'; // <-- Our powerful new hook
import BottomTabBar from '@/components/BottomBar'; // Adjust path
import { formatDate } from '@/utils/date-formater';

LocaleConfig.locales["pt-br"] = ptBR;
LocaleConfig.defaultLocale = "pt-br";

export default function ServiceBookingScreen() {
  const {
    loading,
    slotsLoading,
    service,
    hairdresser,
    showCalendar,
    setShowCalendar,
    initialDate,
    markedDates,
    handleDayPress,
    selectedDate,
    availableSlots,
    selectedTime,
    setSelectedTime,
    showConfirmationModal,
    setShowConfirmationModal,
    handleBooking,
    formattedSelectedDate,
  } = useServiceBooking();

  const getMaxDate = () => {
    const maxDate = new Date();
    maxDate.setFullYear(maxDate.getFullYear() + 1);
    return maxDate.toISOString().split('T')[0];
  }

  const renderCalendar = () => {
    return (
        <View >
          <Calendar 
            hideExtraDays
            minDate={initialDate}
            maxDate={getMaxDate()}
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
            onDayPress={handleDayPress}>

          </Calendar>
        </View>
      );
    };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <View style={styles.titleContainer}>  
        <Text style={styles.title}>{service?.name}</Text>
        <View style={styles.clockIconContainer}>
          <FontAwesome6 style={styles.clockIcon} name="clock" size={18} color="black" />
          <Text style={[styles.title, {marginLeft: 5, fontSize:18}]}>{serviceTimeFormater(service?.duration)}</Text>
        </View>
        
      </View>
      
      <Text style={styles.description}>
        {service?.description}
      </Text>

      <Text style={styles.hairdresserName}>
        Profissional: {hairdresser?.user.first_name} {hairdresser?.user.last_name}
      </Text>

      <Text style={styles.sectionTitle}>Valor</Text>
      {service && (
        <>
          <TouchableOpacity
            key={service.name}
            style={styles.option}
          >
            <Text style={styles.optionText}>R$ {service.price}</Text>
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
          
          {loading ? (
            <Text>Carregando horários disponíveis...</Text>
          ) : (
            <View style={styles.grid}>
              {availableSlots && availableSlots.length > 0 ? (
                availableSlots.map((slot: any) => (
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
          onPress={()=>setShowConfirmationModal(true)}
        >
          <Text style={styles.buttonText}>Agendar</Text>
        </TouchableOpacity>
      )}

    <Modal
        visible={showConfirmationModal}
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
              <Text >Serviço selecionado: {service?.name}</Text> 
              <Text >Data de realização do serviço: {formatDate(selectedDate)}</Text>
              <Text >Horário de realização do serviço: {selectedTime}</Text>
              <Text >Valor do serviço: R$ {service?.price}</Text>
            </View>
            <View style={styles.modalButtonGroup}>
                <TouchableOpacity
                style={styles.modalBackButton}
                onPress={() => setShowConfirmationModal(false)}
                >
                <Text style={styles.modalBackButtonText}>Voltar</Text>
                </TouchableOpacity>
                <TouchableOpacity
                style={styles.modalAcceptButton}
                onPress={() => {
                    setShowConfirmationModal(false);
                    handleBooking();
                }}
                >
                <Text style={styles.modalAcceptButtonText}>Aceitar</Text>
                </TouchableOpacity>
            </View>
            </View>
        </View>
      </Modal>
    </ScrollView>
  );
}

