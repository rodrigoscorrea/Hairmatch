// app/(app)/(hairdresser)/agenda.tsx
import React from 'react';
import { View, Text, TouchableOpacity, SafeAreaView, FlatList, Modal, StatusBar } from 'react-native';
import { Calendar } from 'react-native-big-calendar';
import dayjs from 'dayjs';
import 'dayjs/locale/pt-br';
import { formatDate } from '../../../utils/date-formater';
import { formatTime } from '../../../utils/time-formater';
import { styles, calendarTheme } from '@/screens/hairdresser/agenda/AgendaManagerStyles'; // Adjust path
import { useAgenda } from '@/hooks/hairdresserHooks/useAgenda'; // Our new hook
import type { AgendaEvent, AgendaViewProps } from '@/models/Agenda.types';

// The Agenda list view can be a separate component for cleanliness
const AgendaListView: React.FC<AgendaViewProps> = ({ events, onEventPress }) => (
  <FlatList
    data={events}
    keyExtractor={(item) => item.id.toString()}
    contentContainerStyle={{ paddingVertical: 10 }}
    ListEmptyComponent={<Text style={styles.emptyText}>Nenhum evento agendado.</Text>}
    renderItem={({ item }) => (
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
    )}
  />
);

export default function AgendaManagerScreen() {
  const {
    events,
    selectedView,
    selectedDate,
    modalVisible,
    selectedEvent,
    headerText,
    sortedEventsForAgendaView,
    handleViewChange,
    goToPreviousPeriod,
    goToNextPeriod,
    handlePressCell,
    onEventPress,
    closeModal,
    confirmCancelEvent,
  } = useAgenda();

  const Header = () => (
    <View style={styles.header}>
      <StatusBar barStyle="dark-content" backgroundColor="#F5E6D3" />
      <View style={styles.tabContainer}>
        {(['agenda','month', 'week', 'day', ] as const).map((view) => (
          <TouchableOpacity
            key={view}
            style={[styles.tab, selectedView === view && styles.activeTab]}
            onPress={() => handleViewChange(view)}
          >
            <Text style={[styles.tabText, selectedView === view && styles.activeTabText]}>
              {view.charAt(0).toUpperCase() + view.slice(1)}
            </Text>
          </TouchableOpacity>
        ))}
      </View>
    </View>
  );

  return (
    <SafeAreaView style={styles.container}>
      <Header />
      
      {/* Calendar Header is part of the main component now */}
      <View style={[styles.calendarHeader, { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }]}>
        <TouchableOpacity onPress={goToPreviousPeriod} style={{ padding: 10 }}>
          <Text style={{ fontSize: 18, color: '#9B7EBD', fontWeight: 'bold' }}>‹</Text>
        </TouchableOpacity>
        <Text style={styles.calendarHeaderText}>{headerText}</Text>
        <TouchableOpacity onPress={goToNextPeriod} style={{ padding: 10 }}>
          <Text style={{ fontSize: 18, color: '#9B7EBD', fontWeight: 'bold' }}>›</Text>
        </TouchableOpacity>
      </View>
      
      {selectedView === 'agenda' ? (
        <AgendaListView events={sortedEventsForAgendaView} onEventPress={onEventPress} />
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
            swipeEnabled={false}
            theme={calendarTheme}
          />
        </View>
      )}

      {/* --- Cancellation Modal --- */}
      <Modal visible={modalVisible} transparent={true} animationType="slide" onRequestClose={closeModal}>
        <View style={styles.modalOverlay}>
            <View style={styles.modalContainer}>
            <Text style={styles.modalTitle}>Detalhes do Agendamento</Text>
            <View style={styles.modalReserveInformations}>
                <Text>Serviço agendado: {selectedEvent?.title}</Text> 
                <Text>Data: {selectedEvent ? formatDate(selectedEvent.start.toISOString()) : ""}</Text>
                <Text>Horário: {selectedEvent ? formatTime(selectedEvent.start.toISOString()) : ""}</Text>
            </View>
            <View style={styles.modalButtonGroup}>
                <TouchableOpacity style={styles.modalBackButton} onPress={closeModal}>
                    <Text style={styles.modalBackButtonText}>Voltar</Text>
                </TouchableOpacity>
                <TouchableOpacity style={styles.modalAcceptButton} onPress={confirmCancelEvent}>
                    <Text style={styles.modalAcceptButtonText}>Cancelar Agendamento</Text>
                </TouchableOpacity>
            </View>
            </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}