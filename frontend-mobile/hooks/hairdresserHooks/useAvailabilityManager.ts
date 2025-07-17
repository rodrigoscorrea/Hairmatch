// hooks/hairdresserHooks/useAvailabilityManager.ts
import { useState, useCallback } from 'react';
import { useRouter, useFocusEffect } from 'expo-router';
import { useAuth } from '@/app/_layout';
import { listAvailabilitiesByHairdresser } from '@/services/availability.service';
import { AvailabilityResponse } from '@/models/Availability.types';

export const useAvailabilityManager = () => {
  const router = useRouter();
  const { userInfo } = useAuth();
  const hairdresserId = userInfo?.hairdresser?.id;

  const [availabilities, setAvailabilities] = useState<AvailabilityResponse[]>([]);
  const [nonWorkingDays, setNonWorkingDays] = useState<number[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // useFocusEffect re-fetches data every time the screen comes into view
  useFocusEffect(
    useCallback(() => {
      const fetchAvailability = async () => {
        if (!hairdresserId) return;
        setIsLoading(true);
        try {
          const response = await listAvailabilitiesByHairdresser(hairdresserId);
          setAvailabilities(response.data);
          setNonWorkingDays(response.non_working_days);
        } catch (error) {
          console.error("Failed to fetch availabilities:", error);
        } finally {
          setIsLoading(false);
        }
      };
      fetchAvailability();
    }, [hairdresserId])
  );

  const goToCreate = () => router.push('/(app)/(hairdresser)/availability/create');
  const goToEdit = () => router.push(`/(app)/(hairdresser)/availability/edit/${hairdresserId}`);
  const goBack = () => router.back();

  return {
    isLoading,
    availabilities,
    goToCreate,
    goToEdit,
    goBack,
  };
};