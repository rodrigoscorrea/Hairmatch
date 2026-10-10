// hooks/customerHooks/useFavoriteToggle.ts
import { useCallback, useRef, useState } from 'react';
import { useFocusEffect } from 'expo-router';
import {
  addFavoriteHairdresser,
  listFavoriteHairdressers,
  removeFavoriteHairdresser,
} from '@/services/favorite-hairdresser.service';
import { problemMessage } from '@/utils/api-problem';

/** The heart of a hairdresser's public profile: whether the logged customer favorited them, and the toggle. */
export const useFavoriteToggle = (hairdresserId: number | undefined) => {
  const [isFavorite, setIsFavorite] = useState(false);
  // Until the list is read the state of the heart is unknown, so the heart stays disabled.
  const [loaded, setLoaded] = useState(false);
  const [pending, setPending] = useState(false);
  const [errorModal, setErrorModal] = useState<{ visible: boolean; message: string }>({ visible: false, message: '' });
  // The tab keeps the screen mounted, so the id can change while a request is still in flight.
  const currentId = useRef(hairdresserId);
  currentId.current = hairdresserId;
  const pendingId = useRef<number | null>(null);

  useFocusEffect(
    useCallback(() => {
      // The state of another hairdresser, or an unread one, must not show; a toggle in flight keeps its own.
      if (pendingId.current !== hairdresserId) {
        setIsFavorite(false);
        setLoaded(false);
      }
      if (!hairdresserId) return;
      let active = true;
      listFavoriteHairdressers()
        .then((favorites) => {
          if (!active) return;
          // A toggle in flight for this hairdresser already shows the state the customer asked for.
          if (pendingId.current !== hairdresserId) setIsFavorite(favorites.some((favorite) => favorite.id === hairdresserId));
          setLoaded(true);
        })
        .catch(() => {
          // The rest of the profile opens normally: the heart stays empty and disabled.
        });
      return () => {
        active = false;
      };
    }, [hairdresserId])
  );

  const toggle = async () => {
    if (!hairdresserId || !loaded || pendingId.current !== null) return;
    const previous = isFavorite;
    setIsFavorite(!previous);
    pendingId.current = hairdresserId;
    setPending(true);
    try {
      if (previous) {
        await removeFavoriteHairdresser(hairdresserId);
      } else {
        await addFavoriteHairdresser(hairdresserId);
      }
    } catch (error) {
      if (currentId.current === hairdresserId) setIsFavorite(previous);
      setErrorModal({ visible: true, message: problemMessage(error, 'Não foi possível atualizar seus favoritos.') });
    } finally {
      pendingId.current = null;
      setPending(false);
    }
  };

  return {
    isFavorite,
    disabled: pending || !loaded,
    toggle,
    errorModal,
    closeError: () => setErrorModal({ visible: false, message: '' }),
  };
};
