import React, { useState, useMemo, useEffect } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StatusBar,
  SafeAreaView,
  FlatList,
  Modal,
  Pressable
} from 'react-native';
import BottomTabBar from '@/app/components/BottomBar';
import { Calendar } from 'react-native-big-calendar';
import 'dayjs/locale/pt-br';
import dayjs from 'dayjs';
import { styles, calendarTheme } from './AgendaManagerStyles';
import { createAgendaApointment, listAgendaByHairdresser } from '@/app/services/agenda.service';
import { useBottomTab } from '@/app/contexts/BottomTabContext'
import type { AgendaEvent, CalendarMode, AgendaViewProps } from '@/app/models/Agenda.types';

const AgendaManagerScreen: React.FC = () => {
  const [selectedView, setSelectedView] = useState<CalendarMode>('month');
  const [selectedDate, setSelectedDate] = useState<Date>(new Date());
  const {hairdresser, setActiveTab} = useBottomTab();
  const [events, setEvents] = useState<AgendaEvent[]>([]);
  const [modalVisible, setModalVisible] = useState<boolean>(false);
  const [eventTitle, setEventTitle] = useState<string>("");
  const [startTime, setStartTime] = useState<any>(null);
  const [selectedEvent, setSelectedEvent] = useState<any>(null)

  const onEventPress = (event: AgendaEvent) => {
    setSelectedEvent(event);
    setEventTitle(event.title);
    setStartTime(new Date(event.start));
    setModalVisible(true);
  };

  useEffect(() => {
    const fetchAgendaEvents = async () => {
      try {
        const response = await listAgendaByHairdresser(hairdresser?.id);
        const converted:AgendaEvent[] =response.data.map((ev:any) => ({
          id: ev.id,
          title: ev.service.name,
          start: new Date(ev.start_time),
          end: new Date(ev.end_time),
        }));
        setEvents(converted);  
      } catch (error) {
        console.log('Error while fetching agenda events', error);
      }
    }
    fetchAgendaEvents();
  }, []);

  useEffect(()=>{
    setActiveTab('AgendaManager')
  }, [])
  
  // Função alternativa para navegação manual
  const handleSwipeLeft = () => {
    let newDate: Date;
    
    switch (selectedView) {
      case 'month':
        newDate = dayjs(selectedDate).add(1, 'month').toDate();
        break;
      case 'week':
        newDate = dayjs(selectedDate).add(1, 'week').toDate();
        break;
      case 'day':
        newDate = dayjs(selectedDate).add(1, 'day').toDate();
        break;
      default:
        return;
    }
    
    setSelectedDate(newDate);
  };

  const handleSwipeRight = () => {
    let newDate: Date;
    
    switch (selectedView) {
      case 'month':
        newDate = dayjs(selectedDate).subtract(1, 'month').toDate();
        break;
      case 'week':
        newDate = dayjs(selectedDate).subtract(1, 'week').toDate();
        break;
      case 'day':
        newDate = dayjs(selectedDate).subtract(1, 'day').toDate();
        break;
      default:
        return;
    }
    
    setSelectedDate(newDate);
  };

  // Função para lidar com pressionar uma célula
  const handlePressCell = (date: Date) => {
    setSelectedDate(date);
    if (selectedView === 'month') {
      setSelectedView('day');
    }
  };

  // Função para lidar com mudança de visualização
  const handleViewChange = (view: CalendarMode) => {
    setSelectedView(view);
  };

  const renderHeader = (): JSX.Element => (
    <View style={styles.header}>
      <StatusBar barStyle="dark-content" backgroundColor="#F5E6D3" />
      <View style={styles.tabContainer}>
        <TouchableOpacity
          style={[styles.tab, selectedView === 'month' && styles.activeTab]}
          onPress={() => handleViewChange('month')}
        >
          <Text style={[styles.tabText, selectedView === 'month' && styles.activeTabText]}>
            Mês
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.tab, selectedView === 'week' && styles.activeTab]}
          onPress={() => handleViewChange('week')}
        >
          <Text style={[styles.tabText, selectedView === 'week' && styles.activeTabText]}>
            Semana
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.tab, selectedView === 'day' && styles.activeTab]}
          onPress={() => handleViewChange('day')}
        >
          <Text style={[styles.tabText, selectedView === 'day' && styles.activeTabText]}>
            Dia
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.tab, selectedView === 'agenda' && styles.activeTab]}
          onPress={() => handleViewChange('agenda')}
        >
          <Text style={[styles.tabText, selectedView === 'agenda' && styles.activeTabText]}>
            Agenda
          </Text>
        </TouchableOpacity>
      </View>
    </View>
  );

  // Usa useMemo para otimizar o texto do header
  const headerText = useMemo(() => {
    const monthNames: string[] = [
      'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
      'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
    ];

    if (selectedView === 'agenda') {
      return 'Todos os Eventos';
    }
    
    return `${monthNames[selectedDate.getMonth()]}`;
  }, [selectedDate, selectedView]);

  const renderCalendarHeader = (): JSX.Element => {
    if (selectedView === 'agenda') {
      return (
        <View style={styles.calendarHeader}>
          <Text style={styles.calendarHeaderText}>{headerText}</Text>
        </View>
      );
    }

    return (
      <View style={[styles.calendarHeader, { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }]}>
        <TouchableOpacity onPress={handleSwipeRight} style={{ padding: 10 }}>
          <Text style={{ fontSize: 18, color: '#9B7EBD', fontWeight: 'bold' }}>‹</Text>
        </TouchableOpacity>
        
        <Text style={styles.calendarHeaderText}>{headerText}</Text>
        
        <TouchableOpacity onPress={handleSwipeLeft} style={{ padding: 10 }}>
          <Text style={{ fontSize: 18, color: '#9B7EBD', fontWeight: 'bold' }}>›</Text>
        </TouchableOpacity>
      </View>
    );
  };
  
  const AgendaView: React.FC<AgendaViewProps> = ({ events, onEventPress }) => { // Usando AgendaViewProps
    const sortedEvents = useMemo(() =>
      [...events].sort((a, b) => a.start.getTime() - b.start.getTime()),
      [events]
    );

    const renderItem = ({ item }: { item: AgendaEvent }) => ( // Tipado com AgendaEvent
      <TouchableOpacity onPress={() => onEventPress(item)}>
        <View style={styles.agendaItem}>
          <View style={styles.dateContainer}>
            <Text style={styles.dayText}>{dayjs(item.start).format('DD')}</Text>
            <Text style={styles.monthText}>{dayjs(item.start).format('MMM').toUpperCase()}</Text>
          </View>
          <View style={styles.detailsContainer}>
            <Text style={styles.titleText}>{item.title}</Text>
            <Text style={styles.timeText}>
              {dayjs(item.start).format('HH:mm')} - {dayjs(item.end).format('HH:mm')}
            </Text>
          </View>
        </View>
      </TouchableOpacity>
    );

    return (
      <FlatList
        data={sortedEvents}
        renderItem={renderItem}
        keyExtractor={(item) => item.id.toString()}
        contentContainerStyle={{ paddingVertical: 10 }}
        ListEmptyComponent={<Text style={styles.emptyText}>Nenhum evento agendado.</Text>}
      />
    );
  };

  const closeModal = () => {
    setModalVisible(false);
    setEventTitle("");
    setStartTime(null);
  };

  const handleCancelEvent = async () => {
    if (!selectedEvent?.id) return;

    try {
      // Deleta do backend primeiro
      //await deleteAgendaAppointment(selectedEvent.id);
      
      // Se tiver sucesso, atualiza o estado local para refletir a mudança
      setEvents((prevEvents) => prevEvents.filter((ev) => ev.id !== selectedEvent.id));
      
      //Alert.alert("Sucesso", "Agendamento cancelado.");
      closeModal();
    } catch (error) {
      console.error("Erro ao cancelar agendamento:", error);
      //Alert.alert("Erro", "Não foi possível cancelar o agendamento. Tente novamente.");
    }
  };


  return (

    <SafeAreaView style={styles.container}>
      {renderHeader()}
      {renderCalendarHeader()}
      
      {selectedView === 'agenda' ? (
          <AgendaView events={events} onEventPress={onEventPress} />
        ) : (
      <View style={styles.calendarContainer}>
        <Calendar
          events={events}
          height={600}
          mode={selectedView}
          date={selectedDate}
          locale="pt-br"
          onPressEvent={onEventPress}
          onPressCell={handlePressCell}
          weekStartsOn={1}
          showTime={selectedView !== 'month'}
          swipeEnabled={true}
          theme={calendarTheme}
        />
      </View>)}

      <View>
      <Modal
        visible={modalVisible}
        transparent={true}
        animationType="slide"
        onRequestClose={closeModal}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContainer}>
          <Text style={styles.modalTitle}>Confirmar Cancelamento</Text>
            <Text style={styles.modalText}>
                Cheque todos os dados sobre o agendamento abaixo e clique em Cancelar para prosseguir.
            </Text>
            <View style={styles.modalReserveInformations}>
              <Text >Serviço agendado: {eventTitle}</Text> 
              <Text >Data Reservada: {startTime ? dayjs(startTime).format('DD/MM/YYYY') : "--:--"}</Text>
              <Text >Horário Reservado: {startTime ? dayjs(startTime).format("HH:mm"): "--:--"}</Text>
            </View>
            <View style={styles.modalButtonGroup}>
                <TouchableOpacity
                style={styles.modalBackButton}
                onPress={closeModal}
                >
                <Text style={styles.modalBackButtonText}>Voltar</Text>
                </TouchableOpacity>
                <TouchableOpacity
                style={styles.modalAcceptButton}
                onPress={handleCancelEvent}
                >
                <Text style={styles.modalAcceptButtonText}>Cancelar</Text>
                </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
        <BottomTabBar/>
      </View>
    </SafeAreaView>
  );
};

export default AgendaManagerScreen;