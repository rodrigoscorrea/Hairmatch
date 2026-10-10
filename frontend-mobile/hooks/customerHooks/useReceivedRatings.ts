// hooks/customerHooks/useReceivedRatings.ts
import { useCallback, useState } from 'react';
import { useFocusEffect, useRouter } from 'expo-router';
import { useAuth } from '@/app/_layout';
import { CustomerRating } from '@/models/CustomerRating.types';
import { getCustomerRatings } from '@/services/customer-rating.service';
import { problemMessage } from '@/utils/api-problem';

export const useReceivedRatings = () => {
  const { userInfo } = useAuth();
  const router = useRouter();
  const customerId: number | undefined = userInfo?.customer?.id;

  const [ratings, setRatings] = useState<CustomerRating[]>([]);
  // Only a successful fetch shows the empty message; a failure shows the error modal instead.
  const [isLoaded, setIsLoaded] = useState(false);
  const [errorModal, setErrorModal] = useState<{ visible: boolean; message: string }>({ visible: false, message: '' });

  useFocusEffect(
    useCallback(() => {
      if (!customerId) return;
      let active = true;
      getCustomerRatings(customerId)
        .then((response) => {
          if (!active) return;
          // The API already sends the most recent first.
          setRatings(response.data.ratings);
          setIsLoaded(true);
        })
        .catch((error) => {
          if (!active) return;
          setErrorModal({ visible: true, message: problemMessage(error, 'Não foi possível carregar suas avaliações.') });
        });
      return () => {
        active = false;
      };
    }, [customerId])
  );

  const handleGoBack = () => router.push('/(app)/customer/profile');

  return {
    ratings,
    isLoaded,
    errorModal,
    closeError: () => setErrorModal({ visible: false, message: '' }),
    handleGoBack,
  };
};
