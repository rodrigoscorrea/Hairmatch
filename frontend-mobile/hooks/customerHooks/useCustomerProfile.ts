import { useCallback, useState } from 'react';
import { useAuth } from '@/app/_layout'; 
import { useFocusEffect, useRouter } from 'expo-router';
import { getCustomerRatings } from '@/services/customer-rating.service';
import { formatCustomerRating } from '@/utils/rating';

export const useCustomerProfile = () => {
  const { userInfo, signOut } = useAuth();
  const router = useRouter();
  const customerId: number | undefined = userInfo?.customer?.id;

  const [isModalVisible, setIsModalVisible] = useState(false);
  const [ratingLabel, setRatingLabel] = useState('');

  // The average comes from the ratings route on every focus: the session's userInfo is not refreshed after a rating.
  useFocusEffect(
    useCallback(() => {
      if (!customerId) return;
      let active = true;
      getCustomerRatings(customerId)
        .then((response) => {
          if (active) setRatingLabel(formatCustomerRating(response.data.average, response.data.count));
        })
        .catch(() => {
          if (active) setRatingLabel('Nota indisponível');
        });
      return () => {
        active = false;
      };
    }, [customerId])
  );

  const handleLogout = () => {
    setIsModalVisible(true);
  };

  const confirmLogout = async () => {
    await signOut();
    setIsModalVisible(false);
  };

  const cancelLogout = () => {
    setIsModalVisible(false);
  };

  const handleAccountSettings = () => {
    router.push(`/(app)/customer/configs/accountSetting`);
  };

  const handleAddressSettings = () => {
    router.push(`/(app)/customer/configs/addressSetting`);
  };

  const handleReceivedRatings = () => {
    router.push('/(app)/customer/ratings');
  };

  const handleGoBack = () => {
    router.push('/(app)/customer/profile');
  };

  return {
    customer: userInfo?.customer,
    ratingLabel,
    isModalVisible,
    handleLogout,
    confirmLogout,
    cancelLogout,
    handleAccountSettings,
    handleGoBack,
    handleAddressSettings,
    handleReceivedRatings
  };
};