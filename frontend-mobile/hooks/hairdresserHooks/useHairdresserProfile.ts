// hooks/hairdresserHooks/useHairdresserProfile.ts
import { useState, useEffect } from 'react';
import { useRouter } from 'expo-router';
import { useAuth } from '@/app/_layout';
import { getPreferencesByUser } from '@/services/preferences.service';
import { PreferencesResponse } from '@/models/Preferences.types';

export const useHairdresserProfile = () => {
  const router = useRouter();
  const { userInfo } = useAuth();
  const hairdresser = userInfo?.hairdresser;

  const [preferences, setPreferences] = useState<PreferencesResponse[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchPreferences = async () => {
      if (!hairdresser?.user?.id) return;
      try {
        setLoading(true);
        const response = await getPreferencesByUser(hairdresser.user.id);
        setPreferences(response);
      } catch (error) {
        console.error("Failed to fetch hairdresser preferences:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchPreferences();
  }, [hairdresser?.user?.id]);

  // Navigation Handlers
  const goToSettings = () => router.push('/(app)/(hairdresser)/profile/settings');
  const goToServices = () => router.push('/(app)/(hairdresser)/services'); // Navigates to the services tab
  const goToAvailability = () => router.push('/(app)/(hairdresser)/availability'); // You'll create this screen
  const handleGoBack = () => {
    router.push('/(app)/(hairdresser)/profile/settings');
  };

  return {
    loading,
    hairdresser,
    preferences,
    goToSettings,
    goToServices,
    goToAvailability,
    handleGoBack
  };
};