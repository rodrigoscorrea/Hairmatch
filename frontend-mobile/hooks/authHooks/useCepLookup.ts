import { useRef, useState } from 'react';
import axios from 'axios';
import { ERROR_MESSAGES } from '@/app/../constants/errorMessages';
import { CepAddress, lookupCep } from '@/services/cep.service';

export const useCepLookup = () => {
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  // The CEP whose response is still wanted; any other response is stale.
  const latestCepRef = useRef<string | null>(null);

  const lookup = async (digits: string, onFound: (address: CepAddress) => void) => {
    latestCepRef.current = digits;
    setLoading(true);
    setMessage('');
    try {
      const address = await lookupCep(digits);
      if (latestCepRef.current !== digits) return;
      onFound(address);
    } catch (error) {
      if (latestCepRef.current !== digits) return;
      const notFound = axios.isAxiosError(error) && error.response?.status === 404;
      setMessage(notFound ? ERROR_MESSAGES.cep_not_found : ERROR_MESSAGES.cep_lookup_failed);
    } finally {
      if (latestCepRef.current === digits) setLoading(false);
    }
  };

  const cancel = () => {
    latestCepRef.current = null;
    setLoading(false);
    setMessage('');
  };

  return { loading, message, lookup, cancel };
};
