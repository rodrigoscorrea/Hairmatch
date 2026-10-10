// hooks/hairdresserHooks/useAgenda.ts
import { useState, useMemo, useCallback, useRef } from 'react';
import { useFocusEffect, useRouter } from 'expo-router';
import dayjs from 'dayjs';
import 'dayjs/locale/pt-br';
import { useAuth } from '@/app/_layout';
import { listAgendaByHairdresser } from '@/services/agenda.service';
import { deleteCustomerRating } from '@/services/customer-rating.service';
import { problemMessage } from '@/utils/api-problem';
import type { AgendaEntryResponse, AgendaEvent, CalendarMode } from '@/models/Agenda.types';

dayjs.locale('pt-br');

export const useAgenda = () => {
  const router = useRouter();
  const { userInfo } = useAuth();
  const hairdresserId = userInfo?.hairdresser?.id;

  const [events, setEvents] = useState<AgendaEvent[]>([]);
  const [selectedView, setSelectedView] = useState<CalendarMode>('agenda');
  const [selectedDate, setSelectedDate] = useState<Date>(new Date());
  
  // Modal State
  const [modalVisible, setModalVisible] = useState(false);
  const [selectedEvent, setSelectedEvent] = useState<AgendaEvent | null>(null);
  // The confirmation of "Excluir avaliação" and the failure of the edit and delete calls.
  const [deleteConfirmVisible, setDeleteConfirmVisible] = useState(false);
  const [errorModal, setErrorModal] = useState<{ visible: boolean; message: string }>({ visible: false, message: '' });
  // A second tap lands before the re-render that closes the confirmation.
  const deletingRef = useRef(false);

  // --- Data Fetching ---
  const fetchAgendaEvents = useCallback(async () => {
    if (!hairdresserId) return;

    try {
      const response = await listAgendaByHairdresser(hairdresserId);
      if (!response) return;
      const convertedEvents: AgendaEvent[] = response.data.map((ev: AgendaEntryResponse) => {
        return {
          id: ev.id,
          // An external block has no service; its title names it.
          title: ev.title || ev.service?.name || '',
          start: new Date(ev.start_time),
          end: new Date(ev.end_time),
          isExternal: ev.customer === null,
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
  }, [hairdresserId]);

  // Runs on every focus, so a block saved in agenda/create and a rating sent from the rate-customer screen show up
  // on the way back.
  useFocusEffect(
    useCallback(() => {
      fetchAgendaEvents();
    }, [fetchAgendaEvents])
  );

  // Only a convenience: the device clock may differ from the server's, which answers 409 service-not-finished.
  const canRate = (event: AgendaEvent) =>
    !!event.reservationId && !event.customerRating && new Date() >= event.end;

  // --- Handlers ---
  const handleViewChange = (view: CalendarMode) => setSelectedView(view);

  const handlePressCell = (date: Date) => {
    if (selectedView === 'month') {
      setSelectedDate(date);
      setSelectedView('day');
      return;
    }
    // Week and Day cells open the external appointment form at that slot.
    router.push({
      pathname: '/(app)/hairdresser/agenda/create',
      params: { date: dayjs(date).format('YYYY-MM-DD'), time: dayjs(date).format('HH:mm') },
    });
  };

  const handleAddPress = () => router.push('/(app)/hairdresser/agenda/create');
  
  const onEventPress = (event: AgendaEvent) => {
    setSelectedEvent(event);
    setModalVisible(true);
  };

  const closeModal = () => {
    setModalVisible(false);
    setSelectedEvent(null);
  };

  // The rate-customer screen opens in edit mode: it reads the rating by id from the customer's ratings.
  const goToEditRating = (event: AgendaEvent) => {
    if (!event.reservationId || !event.customer || !event.customerRating) return;
    // The modal is closed first: it would stay over the rate screen, and the agenda refetches on the way back.
    closeModal();
    router.push({
      pathname: '/(app)/hairdresser/rate-customer/[reservationId]',
      params: {
        reservationId: String(event.reservationId),
        customerName: event.customer.name,
        customerId: String(event.customer.id),
        ratingId: String(event.customerRating.id),
      },
    });
  };

  // The details modal gives way to the confirmation; the event stays selected for the delete.
  const requestDeleteRating = () => {
    setModalVisible(false);
    setDeleteConfirmVisible(true);
  };

  const cancelDeleteRating = () => {
    setDeleteConfirmVisible(false);
    setModalVisible(true);
  };

  const confirmDeleteRating = async () => {
    const ratingId = selectedEvent?.customerRating?.id;
    if (!ratingId || deletingRef.current) return;
    deletingRef.current = true;
    try {
      await deleteCustomerRating(ratingId);
      setDeleteConfirmVisible(false);
      setSelectedEvent(null);
      await fetchAgendaEvents();
    } catch (error) {
      setDeleteConfirmVisible(false);
      setSelectedEvent(null);
      setErrorModal({ visible: true, message: problemMessage(error, 'Não foi possível excluir a avaliação.') });
    } finally {
      deletingRef.current = false;
    }
  };

  const closeError = () => setErrorModal({ visible: false, message: '' });

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
    handleAddPress,
    onEventPress,
    closeModal,
    confirmCancelEvent,
    canRate,
    goToEditRating,
    deleteConfirmVisible,
    requestDeleteRating,
    cancelDeleteRating,
    confirmDeleteRating,
    errorModal,
    closeError,
  };
};