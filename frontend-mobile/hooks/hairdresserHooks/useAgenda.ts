// hooks/hairdresserHooks/useAgenda.ts
import { useState, useMemo, useCallback } from 'react';
import { useFocusEffect } from 'expo-router';
import dayjs from 'dayjs';
import 'dayjs/locale/pt-br';
import { useAuth } from '@/app/_layout';
import { listAgendaByHairdresser } from '@/services/agenda.service';
import type { AgendaEvent, AgendaItemResponse, CalendarMode } from '@/models/Agenda.types';

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
  const hairdresserId = userInfo?.hairdresser?.id;

  // Refetched on every focus, so a rating sent from the rate-customer screen shows up when the hairdresser comes back.
  useFocusEffect(
    useCallback(() => {
      const fetchAgendaEvents = async () => {
        if (!hairdresserId) return;

        try {
          const response = await listAgendaByHairdresser(hairdresserId);
          const convertedEvents: AgendaEvent[] = response.data.map((ev: AgendaItemResponse) => {
            return {
              id: ev.id,
              title: `${ev.service.name}`,
              start: new Date(ev.start_time),
              end: new Date(ev.end_time),
              reservationId: ev.reservation_id,
              customer: ev.customer
                ? {
                    id: ev.customer.id,
                    name: `${ev.customer.user.first_name} ${ev.customer.user.last_name}`,
                    rating: ev.customer.user.rating,
                    ratingsCount: ev.customer.ratings_count,
                  }
                : null,
              customerRating: ev.customer_rating,
            }
          });
          setEvents(convertedEvents);
        } catch (error) {
          console.log('Error while fetching agenda events', error);
        }
      };
      fetchAgendaEvents();
    }, [hairdresserId])
  );

  // Only a convenience: the device clock may differ from the server's, which answers 409 service-not-finished.
  const canRate = (event: AgendaEvent) =>
    !!event.reservationId && !event.customerRating && new Date() >= event.end;

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
    canRate,
  };
};