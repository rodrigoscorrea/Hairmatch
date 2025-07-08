// hooks/hairdresserHooks/useAvailabilityForm.ts
import { useState, useEffect } from 'react';
import { useRouter } from 'expo-router';
import { useAuth } from '@/app/_layout';
import { formatTimeInput } from '@/utils/forms';
import { createAvailability, updateAvailability, listAvailabilitiesByHairdresser } from '@/services/availability.service';

const DAYS_OF_WEEK = [
  { name: 'Domingo', weekday: 'sunday' },
  { name: 'Segunda-Feira', weekday: 'monday' },
  { name: 'Terça-Feira', weekday: 'tuesday' },
  { name: 'Quarta-Feira', weekday: 'wednesday' },
  { name: 'Quinta-Feira', weekday: 'thursday' },
  { name: 'Sexta-Feira', weekday: 'friday' },
  { name: 'Sábado', weekday: 'saturday' },
];

type DayState = {
  info: typeof DAYS_OF_WEEK[0];
  active: boolean;
  start: string;
  end: string;
};

const createPayloadFromDays = (days: DayState[]) => {
    return days
      .filter(day => day.active)
      .map(day => ({
        weekday: day.info.weekday,
        start_time: `${day.start}:00`,
        end_time: `${day.end}:00`,
      }));
};

export const useAvailabilityForm = (mode: 'create' | 'edit') => {
  const router = useRouter();
  const { userInfo } = useAuth();
  const hairdresserId = userInfo?.hairdresser?.id;

  const [errorModal, setErrorModal] = useState({ visible: false, message: '' });
  
  const [initialPayload, setInitialPayload] = useState<object[] | null>(null);
  const [isDirty, setIsDirty] = useState(false);
  const [days, setDays] = useState<DayState[]>(() => DAYS_OF_WEEK.map(day => ({
    info: day,
    active: ![0, 6].includes(DAYS_OF_WEEK.indexOf(day)),
    start: '08:00',
    end: '18:00',
  })));
  const [formMode, setFormMode] = useState<'all' | 'custom'>('all');
  const [allStart, setAllStart] = useState('08:00');
  const [allEnd, setAllEnd] = useState('18:00');
  const [loading, setLoading] = useState(mode === 'edit');

  useEffect(() => {
    if (mode === 'edit' && hairdresserId) {
      const fetchInitialData = async () => {
        try {
          const { data: existingAvailabilities } = await listAvailabilitiesByHairdresser(hairdresserId);
          if (existingAvailabilities && existingAvailabilities.length > 0) {
            const initialDaysState = DAYS_OF_WEEK.map((day) => {
              const availability = existingAvailabilities.find((a:any) => a.weekday === day.weekday);
              return {
                info: day,
                active: !!availability,
                start: availability ? availability.start_time.substring(0, 5) : '08:00',
                end: availability ? availability.end_time.substring(0, 5) : '18:00',
              };
            });
            setDays(initialDaysState);
            setInitialPayload(createPayloadFromDays(initialDaysState));
          } else {
            setInitialPayload([]);
          }
        } catch (error) { console.error("Failed to fetch data for edit form", error); }
        finally { setLoading(false); }
      };
      fetchInitialData();
    }
  }, [mode, hairdresserId]);

  useEffect(() => {
    if (mode === 'edit' && initialPayload) {
      const currentPayload = createPayloadFromDays(days);
      const dirty = JSON.stringify(currentPayload) !== JSON.stringify(initialPayload);
      setIsDirty(dirty);
    }
  }, [days, initialPayload, mode]);

  const handleTimeChange = (index: number, key: 'start' | 'end', value: string) => {
    const numericValue = value.replace(/[^0-9]/g, '');
    const newDays = [...days];

    // Se o valor numérico resultante estiver vazio (ex: o usuário digitou 'aaaa'),
    // defina o campo como uma string vazia para que a validação de 'handleSubmit' possa pegá-lo.
    // Caso contrário, formate o valor como antes.
    if (numericValue) {
        newDays[index][key] = formatTimeInput(numericValue);
    } else {
        newDays[index][key] = ''; // Define explicitamente como vazio
    }
    
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
      setDays(currentDays => currentDays.map(day => ({ ...day, active: true, start: allStart, end: allEnd })));
    }
  };

  useEffect(() => {
    if (formMode === 'all') {
      setDays(currentDays => currentDays.map(day => ({ ...day, active: true, start: allStart, end: allEnd })));
    }
  }, [allStart, allEnd]);

  const handleSubmit = async () => {
    const isValidTime = (time: string): boolean => /^[0-9:]*$/.test(time);

    for (const day of days) {
      if (day.active) {
        if (!isValidTime(day.start) || !isValidTime(day.end) || day.start.length < 5 || day.end.length < 5) {
          setErrorModal({ visible: true, message: "Formato de horário inválido. Use HH:MM." });
          return;
        }
      }
    }

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
      router.back();
    } catch (error) {
      console.error("Error saving availability:", error);
      setErrorModal({ visible: true, message: "Ocorreu um erro ao salvar. Tente novamente." });
    }
  };

  const isAtLeastOneDayActive = days.some(day => day.active);

  return {
    loading,
    days,
    formMode,
    isDirty,
    isSaveDisabled: (mode === 'edit' ? !isDirty : false) || !isAtLeastOneDayActive,
    handleModeChange,
    allStart, setAllStart,
    allEnd, setAllEnd,
    toggleDay,
    handleTimeChange,
    handleSubmit,
    goBack: () => router.back(),
    errorModal,
    closeErrorModal: () => setErrorModal({ visible: false, message: '' }),
  };
};
