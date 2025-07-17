// hooks/useHairdresserProfile.ts
import { useState, useEffect } from 'react';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { useAuth } from '@/app/_layout';

// Import all your services
import { getHairdresser } from '@/services/hairdresser.service';
import { listAvailabilitiesByHairdresser } from '@/services/availability.service';
import { listServicesByHairdresser } from '@/services/service.service';
import { getPreferencesByUser } from '@/services/preferences.service';

// Import your types
import { HairdresserResponse } from '@/models/Hairdresser.types';
import { AvailabilityResponse } from '@/models/Availability.types';
import { ServiceResponse } from '@/models/Service.types';
import { PreferencesResponse } from '@/models/Preferences.types';

export const useHairdresserProfile = () => {
  const router = useRouter();
  const { userInfo } = useAuth();
  
  // Get the `id` from the URL, e.g., /hairdresser/123
  const { id } = useLocalSearchParams<{ id: string }>();

  // State for all the data this screen needs
  const [hairdresser, setHairdresser] = useState<HairdresserResponse | null>(null);
  const [availabilities, setAvailabilities] = useState<AvailabilityResponse[]>([]);
  const [services, setServices] = useState<ServiceResponse[]>([]);
  const [preferences, setPreferences] = useState<PreferencesResponse[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      if (!id) return; 
      setLoading(true);
      try {
        const [
          hairdresserData,
          availabilitiesData,
          servicesData,
          preferencesData,
        ] = await Promise.all([
          getHairdresser(id),
          listAvailabilitiesByHairdresser(Number(id)),
          listServicesByHairdresser(Number(id)),
          getPreferencesByUser(userInfo.customer.user.id),
        ]);

        setHairdresser(hairdresserData.data);
        setAvailabilities(availabilitiesData.data);
        setServices(servicesData.data);
        setPreferences(preferencesData)

      } catch (error) {
        console.error("Failed to fetch hairdresser profile data:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [id]);

  const handleBookService = (service: ServiceResponse) => {
    if (!hairdresser || !userInfo?.customer?.id) return;
    
    router.push({
      pathname: '/(app)/(customer)/service-booking',
      params: { 
        serviceId: service.id, 
        customerId: userInfo.customer.id,
        hairdresserId: hairdresser.id 
      }
    });
  };

  const handleBack = () => {
    router.back();
  };

  return {
    loading,
    hairdresser,
    availabilities,
    services,
    preferences,
    handleBookService,
    handleBack,
  };
};