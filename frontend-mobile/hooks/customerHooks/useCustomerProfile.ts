import { useState } from 'react';
import { useAuth } from '@/app/_layout'; 
import { useRouter } from 'expo-router';

export const useCustomerProfile = () => {
  const { userInfo, signOut } = useAuth();
  const router = useRouter();

  const [isModalVisible, setIsModalVisible] = useState(false);

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
    router.push(`/(app)/(customer)/configs/accountSetting`);
  };

  const handleAddressSettings = () => {
    router.push(`/(app)/(customer)/configs/addressSetting`);
  };

  const handleGoBack = () => {
    router.push('/(app)/(customer)/profile');
  };

  return {
    customer: userInfo?.customer,
    isModalVisible,
    handleLogout,
    confirmLogout,
    cancelLogout,
    handleAccountSettings,
    handleGoBack,
    handleAddressSettings
  };
};