import { useState, useEffect, useCallback, useRef } from 'react';
import { Alert } from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import { useAuth } from '@/app/_layout';
import { useLocalSearchParams, router } from 'expo-router';
import { ReserveWithService } from '@/models/Reserve.types';
import { ReviewPicture } from '@/models/Review.types';
import { PickedImage } from '@/services/account.service';
import { getReserveById } from '@/services/reserve.service';
import { addReviewPictures, createReview, deleteReviewPicture, updateReview } from '@/services/review.service';
import { problemMessage } from '@/utils/api-problem';

const MAX_PICTURES = 5;

type FeedbackModal = { visible: boolean; title: string; message: string };

export const useReviewForm = () => {
  const [rating, setRating] = useState<number>(0);
  const [comment, setComment] = useState('');
  // The pictures the review keeps on the server, the ones marked for removal at the next save, and the new ones in line.
  const [existing, setExisting] = useState<ReviewPicture[]>([]);
  const [removedIds, setRemovedIds] = useState<number[]>([]);
  const [queued, setQueued] = useState<PickedImage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [modal, setModal] = useState<FeedbackModal>({ visible: false, title: 'Erro', message: '' });
  const { userInfo } = useAuth();
  const { id } = useLocalSearchParams<{ id: string }>();
  const [reserve, setReserve] = useState<ReserveWithService | null>(null);
  // Two taps can land before `isSubmitting` re-renders the button as busy.
  const submittingRef = useRef(false);

  const isEditing = !!reserve?.review;
  const remaining = MAX_PICTURES - existing.length - queued.length;

  const showModal = (message: string, title = 'Erro') => setModal({ visible: true, title, message });
  const closeModal = () => setModal(previous => ({ ...previous, visible: false }));

  useEffect(() => {
    const fetchReserve = async () => {
      if (!id) return;
      setIsLoading(true);
      try {
        const response = await getReserveById(Number(id));
        setReserve(response.data);
        // An existing review opens the form filled (REV-61).
        const review = response.data.review;
        if (review) {
          setRating(review.rating);
          setComment(review.comment ?? '');
          setExisting(review.pictures);
        }
      } catch (error) {
        console.error("Failed to fetch reserve details:", error);
        showModal(problemMessage(error, 'Não foi possível carregar os detalhes do agendamento.'));
      } finally {
        setIsLoading(false);
      }
    };
    fetchReserve();
  }, [id]);

  const handleGoBack = () => {
    router.push(`/(app)/customer/reserves/${id}`);
  }

  const pickPictures = useCallback(async () => {
    if (remaining <= 0) return;
    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (status !== 'granted') {
      showModal('Permita o acesso às fotos para anexar imagens à avaliação.');
      return;
    }

    // `allowsEditing` and `allowsMultipleSelection` exclude each other, so the pictures are not cropped.
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ['images'],
      allowsMultipleSelection: true,
      selectionLimit: remaining,
      quality: 0.5,
    });
    if (result.canceled) return;

    const picked: PickedImage[] = result.assets.map((asset, index) => ({
      uri: asset.uri,
      type: asset.mimeType || 'image/jpeg',
      name: asset.fileName || `review_${Date.now()}_${index}.jpg`,
    }));
    // The web has no selectionLimit: the gallery can return more than fits, and the app keeps the first ones.
    setQueued(previous => [...previous, ...picked.slice(0, remaining)]);
    if (picked.length > remaining) {
      showModal(`Você pode enviar até ${MAX_PICTURES} fotos.`, 'Aviso');
    }
  }, [remaining]);

  // Removing only changes the form. A picture that already exists is deleted on the server when the form is saved.
  const removeExisting = (pictureId: number) => {
    setExisting(previous => previous.filter(picture => picture.id !== pictureId));
    setRemovedIds(previous => [...previous, pictureId]);
  };

  const removeQueued = (index: number) => {
    setQueued(previous => previous.filter((_, position) => position !== index));
  };

  // After a failed save: shows what the server really holds. What was not sent stays in the form.
  const reloadAfterFailure = async (pendingRemoval: number[]) => {
    try {
      const response = await getReserveById(Number(id));
      setReserve(response.data);
      const stored: ReviewPicture[] = response.data.review?.pictures ?? [];
      // Pictures marked for removal that are still stored stay hidden and marked, for the next save.
      const stillMarked = pendingRemoval.filter(pictureId => stored.some(picture => picture.id === pictureId));
      setRemovedIds(stillMarked);
      setExisting(stored.filter(picture => !stillMarked.includes(picture.id)));
    } catch (error) {
      console.error("Failed to reload the reserve:", error);
    }
  };

  const handleSubmit = useCallback(async () => {
    if (submittingRef.current || !reserve) return;
    if (rating === 0) {
      showModal('Escolha de 1 a 5 estrelas para enviar a avaliação.', 'Aviso');
      return;
    }

    submittingRef.current = true;
    setIsSubmitting(true);
    // The removals still to do, so a failure knows which ones the server did not take.
    let pendingRemoval = [...removedIds];
    try {
      if (reserve.review) {
        const reviewId = reserve.review.id;
        await updateReview(reviewId, { rating, comment });
        while (pendingRemoval.length > 0) {
          await deleteReviewPicture(reviewId, pendingRemoval[0]);
          pendingRemoval = pendingRemoval.slice(1);
          setRemovedIds(pendingRemoval);
        }
        if (queued.length > 0) {
          await addReviewPictures(reviewId, queued);
          setQueued([]);
        }
      } else {
        await createReview({
          rating,
          comment,
          hairdresser: Number(reserve.service.hairdresser.id),
          reserve: Number(id),
          pictures: queued,
        });
      }

      // The form is only cleared once everything went through.
      setRating(0);
      setComment('');
      setExisting([]);
      setRemovedIds([]);
      setQueued([]);
      Alert.alert('Hairmatch', reserve.review ? 'Sua avaliação foi atualizada com sucesso.' : 'Sua avaliação foi registrada com sucesso.');
      router.push(`/(app)/customer/reserves/${id}`);
    } catch (error) {
      console.error('Error submitting review:', error);
      showModal(problemMessage(error, 'Algo deu errado. Tente novamente.'));
      await reloadAfterFailure(pendingRemoval);
    } finally {
      submittingRef.current = false;
      setIsSubmitting(false);
    }
  }, [rating, comment, queued, removedIds, reserve, id]);

  return {
    rating,
    setRating,
    comment,
    setComment,
    existing,
    queued,
    canAddPicture: remaining > 0,
    isEditing,
    pickPictures,
    removeExisting,
    removeQueued,
    handleGoBack,
    handleSubmit,
    isLoading,
    isSubmitting,
    reserve,
    userInfo,
    modal,
    closeModal,
  };
};
