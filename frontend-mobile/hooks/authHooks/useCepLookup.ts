import { useRef, useState } from 'react';
import { ERROR_MESSAGES } from '@/app/../constants/errorMessages';
import { CepAddress, lookupCep } from '@/services/cep.service';
import { toApiProblem } from '@/utils/api-problem';

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
      const notFound = toApiProblem(error)?.slug === 'postal-code-not-found';
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
