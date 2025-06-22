import { useState } from 'react';
import { useAuth } from '@/app/_layout'; 

export const useCustomerProfile = () => {
  const { userInfo, signOut } = useAuth();

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

  return {
    customer: userInfo?.customer,
    isModalVisible,
    handleLogout,
    confirmLogout,
    cancelLogout,
  };
};