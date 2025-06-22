// hooks/hairdresserHooks/useAvailabilityForm.ts
import { useState, useEffect } from 'react';
import { useRouter } from 'expo-router';
import { useAuth } from '@/app/_layout';
import { createAvailability, updateAvailability, listAvailabilitiesByHairdresser } from '@/services/availability.service';

const DAYS_OF_WEEK = [
  { name: 'Domingo', weekday: 'sunday' }, // Mapped to match getDay()
  { name: 'Segunda-Feira', weekday: 'monday' },
  { name: 'Terça-Feira', weekday: 'tuesday' },
  { name: 'Quarta-Feira', weekday: 'wednesday' },
  { name: 'Quinta-Feira', weekday: 'thursday' },
  { name: 'Sexta-Feira', weekday: 'friday' },
  { name: 'Sábado', weekday: 'saturday' },
];

// This defines the shape of our form state for a single day
type DayState = {
  info: typeof DAYS_OF_WEEK[0];
  active: boolean;
  start: string;
  end: string;
};

export const useAvailabilityForm = (mode: 'create' | 'edit') => {
  const router = useRouter();
  const { userInfo } = useAuth();
  const hairdresserId = userInfo?.hairdresser?.id;
  const [initialState, setInitialState] = useState<DayState[] | null>(null);
  const [isDirty, setIsDirty] = useState(false);
  const [days, setDays] = useState<DayState[]>(() => DAYS_OF_WEEK.map(day => ({
    info: day,
    active: ![0, 6].includes(DAYS_OF_WEEK.indexOf(day)), // Default to Mon-Fri active
    start: '08:00',
    end: '18:00',
  })));
  const [formMode, setFormMode] = useState<'all' | 'custom'>('all');
  const [allStart, setAllStart] = useState('08:00');
  const [allEnd, setAllEnd] = useState('18:00');
  const [loading, setLoading] = useState(mode === 'edit');

  useEffect(() => {
    // If in edit mode, fetch existing data to pre-populate the form
    if (mode === 'edit' && hairdresserId) {
      const fetchInitialData = async () => {
        try {
          const { data: existingAvailabilities } = await listAvailabilitiesByHairdresser(hairdresserId);
          const initialDays = DAYS_OF_WEEK.map((day, index) => {
            const availability = existingAvailabilities.find((a:any) => a.weekday === day.weekday);
            return {
              info: day,
              active: !!availability,
              start: availability ? availability.start_time.substring(0, 5) : '08:00',
              end: availability ? availability.end_time.substring(0, 5) : '18:00',
            };
          });
          setDays(initialDays);
          setInitialState(initialDays);
        } catch (error) {
          console.error("Failed to fetch data for edit form", error);
        } finally {
          setLoading(false);
        }
      };
      fetchInitialData();
    }
  }, [mode, hairdresserId]);

  useEffect(() => {
    if (mode === 'edit' && initialState) {
      // For a simple and effective deep comparison of our state array,
      // we can compare their JSON string representations.
      const currentStateString = JSON.stringify(days);
      const initialStateString = JSON.stringify(initialState);
      
      setIsDirty(currentStateString !== initialStateString);
    }
  }, [days, initialState, mode]);


  const handleTimeChange = (index: number, key: 'start' | 'end', value: string) => {
    const newDays = [...days];
    newDays[index][key] = value;
    setDays(newDays);
  };

  const toggleDay = (index: number) => {
    const newDays = [...days];
    newDays[index].active = !newDays[index].active;
    setDays(newDays);
  };

  const handleModeChange = (newMode: 'all' | 'custom') => {
    setFormMode(newMode);
    if (newMode === 'all') {
      setDays(currentDays => currentDays.map(day => ({
        ...day,
        active: true,    
        start: allStart,  
        end: allEnd,      
      })));
    }
  };

  useEffect(() => {
    // Only apply if we are already in 'all' mode
    if (formMode === 'all') {
      setDays(currentDays => currentDays.map(day => ({
        ...day,
        active: true,
        start: allStart,
        end: allEnd,
      })));
    }
  }, [allStart, allEnd]); // Note: formMode is removed from dependency array

  const handleSubmit = async () => {
    if (!hairdresserId) return;

    const availabilitiesPayload = days
      .filter(day => day.active)
      .map(day => ({
        weekday: day.info.weekday,
        start_time: `${day.start}:00`,
        end_time: `${day.end}:00`,
      }));

    try {
      if (mode === 'edit') {
        await updateAvailability(availabilitiesPayload, hairdresserId);
      } else {
        await createAvailability(availabilitiesPayload, hairdresserId);
      }
      router.back(); // Go back to the manager screen
    } catch (error) {
      console.error("Error saving availability:", error);
    }
  };

  return {
    loading,
    days,
    formMode,
    isDirty,
    isSaveDisabled: mode === 'edit' ? !isDirty : false,
    handleModeChange,
    allStart, setAllStart,
    allEnd, setAllEnd,
    toggleDay,
    handleTimeChange,
    handleSubmit,
    goBack: () => router.back(),
  };
};