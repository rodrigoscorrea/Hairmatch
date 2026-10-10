// hooks/hairdresserHooks/useExternalAppointmentForm.ts
import { useEffect, useRef, useState } from 'react';
import { Alert, Platform } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import dayjs from 'dayjs';
import { useAuth } from '@/app/_layout';
import { listServicesByHairdresser } from '@/services/service.service';
import { createAgendaApointment } from '@/services/agenda.service';
import type { ServiceResponse } from '@/models/Service.types';
import type { CreateAgendaRequest } from '@/models/Agenda.types';
import { problemMessage } from '@/utils/api-problem';
import { formatTimeInput } from '@/utils/forms';

const TIME_PATTERN = /^([01]\d|2[0-3]):[0-5]\d$/;
const LAST_MINUTE_OF_DAY = 23 * 60 + 59;

export interface ExternalAppointmentForm {
  date: string; // YYYY-MM-DD
  startTime: string; // HH:mm
  endTime: string; // HH:mm
  serviceId: number | null; // null is "Sem serviço"
  title: string;
}

/** The HH:mm that is `durationMin` after `start`, or null when `start` is not HH:mm or the result passes 23:59. */
export const computeEndTime = (start: string, durationMin: number): string | null => {
  if (!TIME_PATTERN.test(start)) return null;
  const [hour, minute] = start.split(':').map(Number);
  const total = hour * 60 + minute + durationMin;
  if (total > LAST_MINUTE_OF_DAY) return null;
  const pad = (value: number) => value.toString().padStart(2, '0');
  return `${pad(Math.floor(total / 60))}:${pad(total % 60)}`;
};

/** The first message that blocks saving, in the order EXT-26 to EXT-29, or null when the form is valid. */
export const validateExternalAppointment = (form: ExternalAppointmentForm, now: Date): string | null => {
  if (!TIME_PATTERN.test(form.startTime) || !TIME_PATTERN.test(form.endTime)) {
    return 'Informe os horários de início e término.';
  }
  // Zero-padded HH:mm strings sort in time order.
  if (form.endTime <= form.startTime) {
    return 'O término deve ser depois do início.';
  }
  // Without an offset the date-time is read in the device time zone, the same clock as `now`.
  if (new Date(`${form.date}T${form.startTime}:00`) < now) {
    return 'O início não pode estar no passado.';
  }
  if (form.serviceId === null && !form.title.trim()) {
    return 'Informe um título ou escolha um serviço.';
  }
  return null;
};

export const useExternalAppointmentForm = () => {
  const router = useRouter();
  const { userInfo } = useAuth();
  const hairdresserId = userInfo?.hairdresser?.id;
  // A cell of the Week or Day view opens the screen with its date and time.
  const params = useLocalSearchParams<{ date?: string; time?: string }>();

  // The device's local date, not the UTC one of toISOString().
  const [today] = useState(() => dayjs().format('YYYY-MM-DD'));
  const [date, setDate] = useState(() => params.date ?? today);
  const [startTime, setStartTime] = useState(() => params.time ?? '');
  const [endTime, setEndTime] = useState('');
  const [serviceId, setServiceId] = useState<number | null>(null);
  const [title, setTitle] = useState('');
  const [services, setServices] = useState<ServiceResponse[]>([]);
  const [isSaving, setIsSaving] = useState(false);
  const [errorModal, setErrorModal] = useState({ visible: false, message: '' });

  // The state value is stale inside a second tap of the same render, so the lock is a ref.
  const savingRef = useRef(false);
  const startEditedRef = useRef(false);

  useEffect(() => {
    if (!hairdresserId) return;
    // A failure leaves only "Sem serviço", which still saves with a title.
    listServicesByHairdresser(hairdresserId)
      .then((response) => setServices(response?.data ?? []))
      .catch((error) => console.error('Failed to fetch services:', error));
  }, [hairdresserId]);

  const fillEndTime = (start: string, selectedServiceId: number | null) => {
    const service = services.find((s) => s.id === selectedServiceId);
    if (!service) return;
    const end = computeEndTime(start, service.duration);
    if (end) setEndTime(end);
  };

  const handleSelectService = (selectedServiceId: number | null) => {
    setServiceId(selectedServiceId);
    fillEndTime(startTime, selectedServiceId);
  };

  const handleStartTimeChange = (value: string) => {
    startEditedRef.current = true;
    setStartTime(value);
  };

  // formatTimeInput turns '' into '00:00', so an empty field stays empty.
  const handleStartTimeBlur = () => {
    if (!startTime.trim() || !startEditedRef.current) return;
    startEditedRef.current = false;
    const formatted = formatTimeInput(startTime);
    setStartTime(formatted);
    fillEndTime(formatted, serviceId);
  };

  const handleEndTimeBlur = () => {
    if (!endTime.trim()) return;
    setEndTime(formatTimeInput(endTime));
  };

  const handleSave = async () => {
    if (savingRef.current) return;

    const message = validateExternalAppointment({ date, startTime, endTime, serviceId, title }, new Date());
    if (message) {
      setErrorModal({ visible: true, message });
      return;
    }

    const body: CreateAgendaRequest = {
      start_time: `${date}T${startTime}:00`,
      end_time: `${date}T${endTime}:00`,
      title: title.trim(),
    };
    if (serviceId !== null) body.service = serviceId;

    savingRef.current = true;
    setIsSaving(true);
    try {
      await createAgendaApointment(body);
      // Alert.alert does nothing on react-native-web, so the web shows the browser's own alert.
      if (Platform.OS === 'web') {
        window.alert('Sucesso!\nAtendimento externo registrado.');
      } else {
        Alert.alert('Sucesso!', 'Atendimento externo registrado.');
      }
      router.back();
    } catch (error) {
      setErrorModal({
        visible: true,
        message: problemMessage(error, 'Não foi possível registrar o atendimento externo.'),
      });
    } finally {
      savingRef.current = false;
      setIsSaving(false);
    }
  };

  const handleCancel = () => router.back();

  return {
    today,
    date, setDate,
    startTime, handleStartTimeChange, handleStartTimeBlur,
    endTime, setEndTime, handleEndTimeBlur,
    services,
    serviceId, handleSelectService,
    title, setTitle,
    isSaving,
    handleSave,
    handleCancel,
    errorModal,
    closeErrorModal: () => setErrorModal({ visible: false, message: '' }),
  };
};
