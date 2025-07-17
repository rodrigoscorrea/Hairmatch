// hooks/hairdresserHooks/useAgenda.ts
import { useState, useMemo, useEffect } from 'react';
import dayjs from 'dayjs';
import 'dayjs/locale/pt-br';
import { formatDateTimeForAgenda } from '@/utils/time-formater';
import { useAuth } from '@/app/_layout';
import { listAgendaByHairdresser } from '@/services/agenda.service';
import type { AgendaEvent, CalendarMode } from '@/models/Agenda.types';

dayjs.locale('pt-br');

export const useAgenda = () => {
  const { userInfo } = useAuth();

  const [events, setEvents] = useState<AgendaEvent[]>([]);
  const [selectedView, setSelectedView] = useState<CalendarMode>('agenda');
  const [selectedDate, setSelectedDate] = useState<Date>(new Date());
  
  // Modal State
  const [modalVisible, setModalVisible] = useState(false);
  const [selectedEvent, setSelectedEvent] = useState<AgendaEvent | null>(null);

  // --- Data Fetching ---
  useEffect(() => {
    const fetchAgendaEvents = async () => {
      const hairdresserId = userInfo?.hairdresser?.id;
      if (!hairdresserId) return;

      try {
        const response = await listAgendaByHairdresser(hairdresserId);
        const convertedEvents: AgendaEvent[] = response.data.map((ev: any) => {
          return {
            id: ev.id,
            title: `${ev.service.name}`,
            start: new Date(formatDateTimeForAgenda(ev.start_time)),
            end: new Date(formatDateTimeForAgenda(ev.end_time)),
          }
        });
        setEvents(convertedEvents);
      } catch (error) {
        console.log('Error while fetching agenda events', error);
      }
    };
    fetchAgendaEvents();
  }, [userInfo]); // Re-fetch if the user info changes

  // --- Handlers ---
  const handleViewChange = (view: CalendarMode) => setSelectedView(view);

  const handlePressCell = (date: Date) => {
    setSelectedDate(date);
    if (selectedView === 'month') {
      setSelectedView('day');
    }
  };
  
  const onEventPress = (event: AgendaEvent) => {
    setSelectedEvent(event);
    setModalVisible(true);
  };

  const closeModal = () => {
    setModalVisible(false);
    setSelectedEvent(null);
  };

  const confirmCancelEvent = async () => {
    if (!selectedEvent?.id) return;
    // Call your backend service to cancel the event here
    // await cancelAgendaEvent(selectedEvent.id);
    setEvents(prev => prev.filter(e => e.id !== selectedEvent.id)); // Optimistic update
    closeModal();
  };

  const goToPreviousPeriod = () => {
    // GUARD CLAUSE: Do nothing if we are in the 'agenda' list view
    if (selectedView === 'agenda') return;
    
    // This is now safe because 'agenda' is filtered out.
    const newDate = dayjs(selectedDate).subtract(1, selectedView).toDate();
    setSelectedDate(newDate);
  };

  const goToNextPeriod = () => {
    // GUARD CLAUSE: Do nothing if we are in the 'agenda' list view
    if (selectedView === 'agenda') return;

    const newDate = dayjs(selectedDate).add(1, selectedView).toDate();
    setSelectedDate(newDate);
  };
  
  // --- Memoized Values ---
  const headerText = useMemo(() => {
    if (selectedView === 'agenda') return 'Todos os Eventos';
    return dayjs(selectedDate).format('MMMM [de] YYYY');
  }, [selectedDate, selectedView]);

  const sortedEventsForAgendaView = useMemo(() =>
    [...events].sort((a, b) => a.start.getTime() - b.start.getTime()),
    [events]
  );

  return {
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
  };
};