// hooks/useServiceBooking.ts
import { useState, useEffect, useMemo } from 'react';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { Alert } from 'react-native';

// Import Services
import { getServiceById } from '@/services/service.service'; // Assuming you have a getService by ID function
import { getHairdresser } from '@/services/hairdresser.service';
import { listAvailabilitiesByHairdresser } from '@/services/availability.service';
import { getAvailableResearchSlots, createReserve } from '@/services/reserve.service';

// Import Types and Helpers
import { ServiceResponse } from '@/models/Service.types';
import { HairdresserResponse } from '@/models/Hairdresser.types';
import { formatDate } from '@/utils/date-formater';

export const useServiceBooking = () => {
  const router = useRouter();
  
  // Get the IDs from the URL search parameters
  const { serviceId, hairdresserId, customerId } = useLocalSearchParams<{ 
    serviceId: string; 
    hairdresserId: string; 
    customerId: string; 
  }>();

  // --- State for fetched data ---
  const [service, setService] = useState<ServiceResponse | null>(null);
  const [hairdresser, setHairdresser] = useState<HairdresserResponse | null>(null);
  const [nonWorkingDays, setNonWorkingDays] = useState<number[]>([]);
  const [availableSlots, setAvailableSlots] = useState<string[]>([]);
  
  // --- State for UI and selections ---
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [selectedTime, setSelectedTime] = useState<string | null>(null);
  const [showCalendar, setShowCalendar] = useState(false);
  const [showConfirmationModal, setShowConfirmationModal] = useState(false);
  const [loading, setLoading] = useState(true);
  const [slotsLoading, setSlotsLoading] = useState(false);
  const [errorInfo, setErrorInfo] = useState<{ visible: boolean; message: string }>({
    visible: false,
    message: '',
  });

  const initialDate = useMemo(() => new Date().toISOString().split('T')[0], []);

  // --- Effect 1: Fetch initial core data (Service, Hairdresser, Non-working days) ---
  useEffect(() => {
    const fetchInitialData = async () => {
      if (!serviceId || !hairdresserId) return;

      setLoading(true);
      try {
        const [serviceData, hairdresserData, availabilityResponse] = await Promise.all([
          getServiceById(Number(serviceId)), // You'll need to create this service function
          getHairdresser(hairdresserId),
          listAvailabilitiesByHairdresser(Number(hairdresserId)),
        ]);

        setService(serviceData.data);
        setHairdresser(hairdresserData.data);
        setNonWorkingDays(availabilityResponse.non_working_days);
      } catch (error) {
        console.error("Failed to fetch initial booking data:", error);
        Alert.alert("Erro", "Não foi possível carregar os dados do serviço.");
      } finally {
        setLoading(false);
      }
    };
    fetchInitialData();
  }, [serviceId, hairdresserId]);

  // --- Effect 2: Fetch available time slots whenever a date is selected ---
  useEffect(() => {
    const fetchAvailableSlots = async () => {
      if (!selectedDate || !hairdresserId || !serviceId) return;

      setSlotsLoading(true);
      try {
        const response = await getAvailableResearchSlots(hairdresserId, serviceId, selectedDate);
        setAvailableSlots(response.available_slots);
      } catch (error) {
        console.error("Failed to fetch available slots:", error);
      } finally {
        setSlotsLoading(false);
      }
    };
    fetchAvailableSlots();
  }, [selectedDate, hairdresserId, serviceId]);

  // --- Memoize marked dates for the calendar ---
  const markedDates = useMemo(() => {
    const marked: { [key: string]: any } = {};
    const today = new Date();
    const maxDate = new Date();
    maxDate.setFullYear(today.getFullYear() + 1);

    // --- Step 1: Mark all non-working days as disabled ---
    if (nonWorkingDays && nonWorkingDays.length > 0) {
      // We start from today and loop for one full year
      let currentDate = new Date(today.setHours(0, 0, 0, 0)); 
      
      while (currentDate <= maxDate) {
        // getDay() gives the day of the week: 0 for Sunday, 1 for Monday, etc.
        if (nonWorkingDays.includes(currentDate.getDay())) {
          const dateString = currentDate.toISOString().split('T')[0];
          marked[dateString] = {
            disabled: true,
            disableTouchEvent: true,
          };
        }
        // Move to the next day
        currentDate.setDate(currentDate.getDate() + 1);
      }
    }

    // --- Step 2: Mark the currently selected date ---
    // This comes after, so it can override the 'disabled' style for the selected day itself,
    // making it clear which day is selected.
    if (selectedDate) {
      marked[selectedDate] = {
        ...marked[selectedDate], // Keep the disabled property if it exists, but override visual styling
        selected: true,
        disableTouchEvent: false, // Make sure we can still interact with it
        selectedColor: '#F06543',
        selectedTextColor: '#ffffff',
      };
    }

    return marked;
  }, [nonWorkingDays, selectedDate]);

  // --- Handlers ---
  const handleDayPress = (day: { dateString: string }) => {
    setSelectedDate(day.dateString);
    setSelectedTime(null); // Reset time when a new date is picked
  };

  const handleBooking = async () => {
    if (!selectedTime || !selectedDate || !service || !hairdresser || !customerId) {
      setErrorInfo({
        visible: true,
        message: "Por favor, selecione uma data e um horário para continuar."
    });
    return;
  }
    
    const reserveData = {
      customer: Number(customerId),
      service: service.id,
      hairdresser: hairdresser.id,
      start_time: `${selectedDate}T${selectedTime}:00`,
    };

    try {
        await createReserve(reserveData);
        setService(null);
        setHairdresser(null);
        setNonWorkingDays([]);
        setSelectedDate(null);
        setSelectedTime(null);
        setShowConfirmationModal(false);
        Alert.alert("Sucesso!", "Sua reserva foi concluída com sucesso :D");
        router.replace('/(app)/(customer)/reserves');
    } catch (err: any) {
        setShowConfirmationModal(false);
        if (err.response && err.response.data && err.response.data.error) {
          setErrorInfo({
              visible: true,
              message: err.response.data.error,
          });
        } else {
          setErrorInfo({
              visible: true,
              message: "Não foi possível confirmar sua reserva. Tente novamente mais tarde.",
          });
        }
    }
  };

  const closeErrorModal = () => {
    setErrorInfo({ visible: false, message: '' });
  };

  return {
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
    formattedSelectedDate: selectedDate ? formatDate(selectedDate) : '',
    errorInfo,
    closeErrorModal
  };
};