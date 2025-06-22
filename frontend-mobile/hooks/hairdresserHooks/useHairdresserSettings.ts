// hooks/hairdresserHooks/useHairdresserSettings.ts
import { useState } from 'react';
import { useAuth } from '@/app/_layout';
import { useRouter } from 'expo-router';

export const useHairdresserSettings = () => {
  const { userInfo, signOut } = useAuth();
  const router = useRouter();

  const [isModalVisible, setIsModalVisible] = useState(false);

  const handleLogout = () => setIsModalVisible(true);

  const confirmLogout = async () => {
    await signOut();
    setIsModalVisible(false);
    // The root layout will handle the redirect to login automatically.
  };

  const cancelLogout = () => setIsModalVisible(false);

  const handleBack = () => router.back();

  return {
    hairdresser: userInfo?.hairdresser,
    isModalVisible,
    handleLogout,
    confirmLogout,
    cancelLogout,
    handleBack,
  };
};