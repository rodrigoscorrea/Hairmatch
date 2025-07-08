// hooks/customerHooks/useSearch.ts
import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'expo-router';
import { useAuth } from '@/app/_layout';
import { searchHairdressers } from '@/services/auth-user.service';
import { Hairdresser } from '@/models/Hairdresser.types';
import { ServiceRequest, ServiceResponseWithHairdresser } from '@/models/Service.types';

export const useSearch = () => {
  const router = useRouter();
  const { userInfo } = useAuth();

  // State for the search query and results
  const [searchText, setSearchText] = useState("");
  const [hairdresserResults, setHairdresserResults] = useState<Hairdresser[]>([]);
  const [serviceResults, setServiceResults] = useState<ServiceResponseWithHairdresser[]>([]);
  const [loading, setLoading] = useState(false);

  const debounceTimeout = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (debounceTimeout.current) clearTimeout(debounceTimeout.current);

    debounceTimeout.current = setTimeout(() => {
      if (searchText.trim().length > 0) {
        fetchResults(searchText);
      } else {
        setHairdresserResults([]);
        setServiceResults([]);
      }
    }, 1000); 

    return () => {
      if (debounceTimeout.current) clearTimeout(debounceTimeout.current);
    };
  }, [searchText]);

  const fetchResults = async (query: string) => {
    setLoading(true);
    try {
      const response = await searchHairdressers(query);
      const newHairdressers: Hairdresser[] = [];
      const newServices: ServiceResponseWithHairdresser[] = [];

      response.data.forEach((item: any) => {
        if (item.result_type === 'hairdresser') {
          newHairdressers.push(item);
        } else if (item.result_type === 'service') {
          newServices.push(item);
        }
      });
      setHairdresserResults(newHairdressers);
      setServiceResults(newServices);
    } catch (error) {
      console.error("Error searching:", error);
    } finally {
      setLoading(false);
    }
  };

  // --- Navigation Handlers ---
  const handleNavigateToHairdresser = (hairdresserId: number) => {
    router.push(`/(app)/(customer)/hairdresser-reservation/${hairdresserId}`);
  };

  const handleNavigateToService = (service: ServiceResponseWithHairdresser) => {
    const customerId = userInfo?.customer?.id;
    if (!customerId) {
      console.error("Customer ID not found for navigation");
      return;
    }
    router.push({
      pathname: '/(app)/(customer)/service-booking',
      params: {
        serviceId: service.id,
        hairdresserId: service.hairdresser.id,
        customerId: customerId,
      }
    });
  };

  const handleGoBack = () => {
    router.push('/(app)/(customer)/home');
  };

  return {
    searchText,
    setSearchText,
    loading,
    hairdresserResults,
    serviceResults,
    handleNavigateToHairdresser,
    handleNavigateToService,
    handleGoBack
  };
};