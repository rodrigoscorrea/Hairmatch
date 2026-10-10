// hooks/hairdresserHooks/useRateCustomer.ts
import { useCallback, useEffect, useRef, useState } from 'react';
import { useFocusEffect, useLocalSearchParams, useRouter } from 'expo-router';
import { ReserveWithService } from '@/models/Reserve.types';
import { getReserveById } from '@/services/reserve.service';
import { createCustomerRating, getCustomerRatings, updateCustomerRating } from '@/services/customer-rating.service';
import { problemMessage } from '@/utils/api-problem';

export const COMMENT_MAX_LENGTH = 500;

const single = (value: string | string[] | undefined) => (Array.isArray(value) ? value[0] : value);

export const useRateCustomer = () => {
  const router = useRouter();
  const params = useLocalSearchParams<{
    reservationId: string;
    customerName?: string;
    customerId?: string;
    ratingId?: string;
  }>();
  const reservationId = single(params.reservationId);
  // The agenda passes the rating to edit. Without `ratingId` the screen rates the customer for the first time.
  const customerId = single(params.customerId);
  const ratingId = single(params.ratingId);
  const isEditing = !!ratingId;
  // The name only comes from the agenda: GET /api/reservations/{id} has no customer name, and a web refresh drops the params.
  const customerName = single(params.customerName) || 'Cliente';

  const [reservation, setReservation] = useState<ReserveWithService | null>(null);
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState('');
  const [confirmVisible, setConfirmVisible] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorModal, setErrorModal] = useState<{ visible: boolean; message: string }>({ visible: false, message: '' });
  // The rating to edit could not be read: there is nothing to edit, so closing the error leaves the screen.
  const [loadFailed, setLoadFailed] = useState(false);
  // A second tap lands before the re-render that disables the button.
  const submittingRef = useRef(false);

  // The screen stays mounted between visits, so the form starts over for each reservation
  // (state adjusted while rendering, as React recommends over an effect).
  const formKey = `${reservationId}|${ratingId ?? ''}`;
  const [formKeyShown, setFormKeyShown] = useState(formKey);
  if (formKeyShown !== formKey) {
    setFormKeyShown(formKey);
    setRating(0);
    setComment('');
    setReservation(null);
    setLoadFailed(false);
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

  // In edit mode the form opens with the current rating, read by id from the ratings of the customer (RT-87).
  // On every focus, because the screen stays mounted and the same rating can be edited twice.
  useFocusEffect(
    useCallback(() => {
      if (!ratingId || !customerId) return;

      let active = true;
      getCustomerRatings(Number(customerId))
        .then((response) => {
          if (!active) return;
          const current = response.data.ratings.find((item) => item.id === Number(ratingId));
          if (!current) throw new Error('rating not found');
          setRating(current.rating);
          setComment(current.comment ?? '');
        })
        .catch((error) => {
          if (!active) return;
          console.error('Failed to fetch the rating to edit:', error);
          setLoadFailed(true);
          setErrorModal({ visible: true, message: 'Não foi possível carregar a avaliação.' });
        });
      return () => {
        active = false;
      };
    }, [ratingId, customerId])
  );

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
      const trimmed = comment.trim() || null;
      if (ratingId) {
        await updateCustomerRating(Number(ratingId), { rating, comment: trimmed });
      } else {
        await createCustomerRating({ reservation: Number(reservationId), rating, comment: trimmed });
      }
      setRating(0);
      setComment('');
      goToAgenda();
    } catch (error) {
      // The form keeps the rating and the comment, so the hairdresser can retry.
      setErrorModal({
        visible: true,
        message: problemMessage(error, isEditing ? 'Não foi possível salvar a avaliação.' : 'Não foi possível enviar a avaliação.'),
      });
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
    closeError: () => {
      setErrorModal({ visible: false, message: '' });
      if (loadFailed) {
        setLoadFailed(false);
        goToAgenda();
      }
    },
    isEditing,
    goToAgenda,
  };
};
