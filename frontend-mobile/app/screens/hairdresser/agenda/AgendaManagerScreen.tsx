import React, { useState, useMemo, useEffect } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StatusBar,
  SafeAreaView,
  FlatList,
} from 'react-native';
import BottomTabBar from '@/app/components/BottomBar';
import { Calendar } from 'react-native-big-calendar';
import 'dayjs/locale/pt-br';
import dayjs from 'dayjs';
import { styles, calendarTheme } from './AgendaManagerStyles';
import { createAgendaApointment, listAgendaByHairdresser } from '@/app/services/agenda.service';
import { useBottomTab } from '@/app/contexts/BottomTabContext'



interface Event {
  title: string;
  start: Date;
  end: Date;
  color: string;
}

type CalendarMode = 'month' | 'week' | 'day' | 'agenda';

const CalendarScreen: React.FC = () => {
  const [selectedView, setSelectedView] = useState<CalendarMode>('month');
  const [selectedDate, setSelectedDate] = useState<Date>(new Date());
  const {hairdresser, setActiveTab} = useBottomTab();
  const [events, setEvents] = useState<any[]>([]);

  useEffect(() => {
    const fetchAgendaEvents = async () => {
      try {
        const response = await listAgendaByHairdresser(hairdresser?.id);
        const converted = response.data.map((ev:any) => ({
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

  interface AgendaViewProps {
    events: Event[];
  }
  
  const AgendaView: React.FC<AgendaViewProps> = ({ events }) => {
    // Usa useMemo para ordenar os eventos apenas quando a lista mudar, otimizando a performance.
    const sortedEvents = useMemo(() => {
      return [...events].sort((a, b) => a.start.getTime() - b.start.getTime());
    }, [events]);
  
    const renderItem = ({ item }: { item: Event }) => (
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
    );
  
    return (
      <FlatList
        data={sortedEvents}
        renderItem={renderItem}
        keyExtractor={(item, index) => `${item.title}-${index}`}
        contentContainerStyle={{ paddingVertical: 10 }}
        ListEmptyComponent={<Text style={styles.emptyText}>Nenhum evento agendado.</Text>}
      />
    );
  };

  return (

    <SafeAreaView style={styles.container}>
      {renderHeader()}
      {renderCalendarHeader()}
      
      {selectedView === 'agenda' ? (
          <AgendaView events={events} />
        ) : (
      <View style={styles.calendarContainer}>
        <Calendar
          events={events}
          height={600}
          mode={selectedView}
          date={selectedDate}
          locale="pt-br"
          onPressEvent={(event: Event) => console.log('Event pressed:', event)}
          onPressCell={handlePressCell}
          weekStartsOn={1}
          showTime={selectedView !== 'month'}
          swipeEnabled={true}
          theme={calendarTheme}
        />
      </View>)}

      <View>
        <BottomTabBar/>
      </View>
    </SafeAreaView>
  );
};

export default CalendarScreen;