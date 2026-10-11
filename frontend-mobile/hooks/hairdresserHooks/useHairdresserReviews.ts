// hooks/hairdresserHooks/useHairdresserReviews.ts
import { useCallback, useState } from 'react';
import { useFocusEffect, useRouter } from 'expo-router';
import { useAuth } from '@/app/_layout';
import { ReceivedReview } from '@/models/Review.types';
import { getHairdresserReviews } from '@/services/review.service';
import { problemMessage } from '@/utils/api-problem';

export const useHairdresserReviews = () => {
  const { userInfo } = useAuth();
  const router = useRouter();
  const hairdresserId: number | undefined = userInfo?.hairdresser?.id;

  const [reviews, setReviews] = useState<ReceivedReview[]>([]);
  // Only a successful fetch shows the empty message; a failure shows the error modal instead.
  const [isLoaded, setIsLoaded] = useState(false);
  const [errorModal, setErrorModal] = useState<{ visible: boolean; message: string }>({ visible: false, message: '' });

  useFocusEffect(
    useCallback(() => {
      if (!hairdresserId) return;
      let active = true;
      getHairdresserReviews(hairdresserId)
        .then((received) => {
          if (!active) return;
          // The API already sends the most recent first.
          setReviews(received);
          setIsLoaded(true);
        })
        .catch((error) => {
          if (!active) return;
          setErrorModal({ visible: true, message: problemMessage(error, 'Não foi possível carregar suas avaliações.') });
        });
      return () => {
        active = false;
      };
    }, [hairdresserId])
  );

  // The profile stack declares `index` as its initial route, so there is always a screen below this one.
  const handleGoBack = () => router.back();

  return {
    reviews,
    isLoaded,
    errorModal,
    closeError: () => setErrorModal({ visible: false, message: '' }),
    handleGoBack,
  };
};
