// hooks/useCustomerHome.ts
import { useState, useEffect } from 'react';
import { useRouter } from 'expo-router';
import { useAuth } from '@/app/_layout';  
import { getCustomerHomeInfo } from '@/services/auth-user.service';
import { CustomerHomeInfoResponse } from '@/models/User.types';
import { Hairdresser } from '@/models/Hairdresser.types';

const maleNames = ["Luis Felipe", "Murilo", "Nicolas", "João Vitor", "Thomas", "Gustavo Henrique", "Thiago", "Igor", "Otávio", "Vitor Gabriel", "Bruno", "João Guilherme", "Cauã", "Guilherme", "Leonardo", "Breno", "Lucca"];
const femaleNames = ["Luna", "Luiza", "Sarah", "Nicole", "Bárbara", "Beatriz", "Larissa", "Isabella", "Helena", "Luisa", "Maria Flor", "Ana Sophia", "Heloisa", "Isabel", "Isabel", "Daniela", "Ana Clara", "Maria Cecília", "Maria Julia", "Yasmin", "Lara", "Luana"];
const maleAvatar = [
  require("../../assets/hairdressers/male/male1.jpg"), require("../../assets/hairdressers/male/male2.jpg"), require("../../assets/hairdressers/male/male3.jpg"), require("../../assets/hairdressers/male/male4.jpg"), require("../../assets/hairdressers/male/male5.jpg")
];
const femaleAvatar = [
  require("../../assets/hairdressers/female/female1.jpg"), require("../../assets/hairdressers/female/female2.jpg"), require("../../assets/hairdressers/female/female3.jpg"), require("../../assets/hairdressers/female/female4.jpg"), require("../../assets/hairdressers/female/female5.jpg")
];
const defaultAvatar = require("../../assets/hairdressers/male/default.jpg");

export const useCustomerHome = () => {
  const router = useRouter();
  const { userInfo } = useAuth();

  const [customerHomeInfo, setCustomerHomeInfo] = useState<CustomerHomeInfoResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchCustomerHomeInfo = async () => {
      if (!userInfo?.customer?.user?.email) {
        return;
      }
      setLoading(true);
      try {
        const response = await getCustomerHomeInfo(userInfo.customer.user.email);
        setCustomerHomeInfo(response);
      } catch (err) {
        console.error("Failed to get customer info:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchCustomerHomeInfo();
  }, [userInfo]);

  const handleClickHairdresser = (hairdresser: Hairdresser, avatar: any) => {
    // We can't pass complex objects like this directly with Expo Router.
    // The best practice is to pass an ID and fetch the data on the next screen.
    // For now, let's just pass the ID. We'll need to create this new page.
    // NOTE: Your file structure shows a 'hairdresser-profile.tsx', let's assume it's dynamic.
    // e.g., app/(app)/(customer)/hairdresser-profile/[id].tsx
    router.push(`/(app)/(customer)/hairdresser-reservation/${hairdresser.id}`);
  };

  const inferGenderFromName = (firstName: string): 'male' | 'female' | 'unknown' => {
    if (maleNames.includes(firstName)) return 'male';
    if (femaleNames.includes(firstName)) return 'female';
    return 'unknown';
  };

  const getRandomAvatarByInferredGender = (firstName: string) => {
    const gender = inferGenderFromName(firstName);
    let selectedAvatars = gender === 'male' ? maleAvatar : (gender === 'female' ? femaleAvatar : []);
    if (selectedAvatars.length === 0) return defaultAvatar;
    const randomIndex = Math.floor(Math.random() * selectedAvatars.length);
    return selectedAvatars[randomIndex];
  };

  return {
    loading,
    customerHomeInfo,
    handleClickHairdresser,
    getRandomAvatarByInferredGender,
    userName: userInfo?.customer?.user?.first_name || '',
  };
};