// hooks/customerHooks/useSearch.ts
import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'expo-router';
import { useAuth } from '@/app/_layout';
import { useBottomTab } from '@/contexts/BottomTabContext';
import { searchHairdressers } from '@/services/auth-user.service';
import { Hairdresser } from '@/models/Hairdresser.types';
import { ServiceRequest, ServiceResponseWithHairdresser } from '@/models/Service.types';

export const useSearch = () => {
  const router = useRouter();
  const { userInfo } = useAuth();
  const { setActiveTab } = useBottomTab();

  // State for the search query and results
  const [searchText, setSearchText] = useState("");
  const [hairdresserResults, setHairdresserResults] = useState<Hairdresser[]>([]);
  const [serviceResults, setServiceResults] = useState<ServiceResponseWithHairdresser[]>([]);
  const [loading, setLoading] = useState(false);

  // useRef is better for storing timeout IDs as it doesn't trigger re-renders
  const debounceTimeout = useRef<NodeJS.Timeout | null>(null);

  // This effect sets the active tab when the screen is focused
  useEffect(() => {
    setActiveTab("Search");
  }, []);

  // This effect handles the debounced search API call
  useEffect(() => {
    // Clear the previous timeout on every keystroke
    if (debounceTimeout.current) clearTimeout(debounceTimeout.current);

    // Set a new timeout
    debounceTimeout.current = setTimeout(() => {
      if (searchText.trim().length > 0) {
        fetchResults(searchText);
      } else {
        // Clear results if search text is empty
        setHairdresserResults([]);
        setServiceResults([]);
      }
    }, 1000); // 1-second debounce delay

    // Cleanup function to clear the timeout if the component unmounts
    return () => {
      if (debounceTimeout.current) clearTimeout(debounceTimeout.current);
    };
  }, [searchText]); // This effect re-runs only when searchText changes

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

  return {
    searchText,
    setSearchText,
    loading,
    hairdresserResults,
    serviceResults,
    handleNavigateToHairdresser,
    handleNavigateToService,
  };
};