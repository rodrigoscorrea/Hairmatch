// hooks/hairdresserHooks/useRateCustomer.ts
import { useEffect, useRef, useState } from 'react';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { ReserveWithService } from '@/models/Reserve.types';
import { getReserveById } from '@/services/reserve.service';
import { createCustomerRating } from '@/services/customer-rating.service';
import { problemMessage } from '@/utils/api-problem';

export const COMMENT_MAX_LENGTH = 500;

const single = (value: string | string[] | undefined) => (Array.isArray(value) ? value[0] : value);

export const useRateCustomer = () => {
  const router = useRouter();
  const params = useLocalSearchParams<{ reservationId: string; customerName?: string }>();
  const reservationId = single(params.reservationId);
  // The name only comes from the agenda: GET /api/reservations/{id} has no customer name, and a web refresh drops the params.
  const customerName = single(params.customerName) || 'Cliente';

  const [reservation, setReservation] = useState<ReserveWithService | null>(null);
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState('');
  const [confirmVisible, setConfirmVisible] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorModal, setErrorModal] = useState<{ visible: boolean; message: string }>({ visible: false, message: '' });
  // A second tap lands before the re-render that disables the button.
  const submittingRef = useRef(false);

  // The screen stays mounted between visits, so the form starts over for each reservation
  // (state adjusted while rendering, as React recommends over an effect).
  const [formReservationId, setFormReservationId] = useState(reservationId);
  if (formReservationId !== reservationId) {
    setFormReservationId(reservationId);
    setRating(0);
    setComment('');
    setReservation(null);
  }

  useEffect(() => {
    if (!reservationId) return;

    let active = true;
    getReserveById(reservationId)
      .then((response) => {
        if (active) setReservation(response.data);
      })
      .catch((error) => console.error('Failed to fetch the reservation to rate:', error));
    return () => {
      active = false;
    };
  }, [reservationId]);

  // SPEC_DEVIATION: the design says router.back(); the screen goes to the agenda explicitly.
  // Reason: the tab navigator's back may land on another tab, and a web refresh leaves no history.
  const goToAgenda = () => router.push('/(app)/hairdresser/agenda');

  const openConfirm = () => {
    if (rating === 0 || isSubmitting) return;
    setConfirmVisible(true);
  };

  const closeConfirm = () => setConfirmVisible(false);

  const submit = async () => {
    if (rating === 0 || submittingRef.current || !reservationId) return;
    submittingRef.current = true;
    setConfirmVisible(false);
    setIsSubmitting(true);
    try {
      await createCustomerRating({ reservation: Number(reservationId), rating, comment: comment.trim() || null });
      setRating(0);
      setComment('');
      goToAgenda();
    } catch (error) {
      // The form keeps the rating and the comment, so the hairdresser can retry.
      setErrorModal({ visible: true, message: problemMessage(error, 'Não foi possível enviar a avaliação.') });
    } finally {
      submittingRef.current = false;
      setIsSubmitting(false);
    }
  };

  return {
    customerName,
    reservation,
    rating,
    setRating,
    comment,
    setComment,
    confirmVisible,
    openConfirm,
    closeConfirm,
    submit,
    isSubmitting,
    errorModal,
    closeError: () => setErrorModal({ visible: false, message: '' }),
    goToAgenda,
  };
};
