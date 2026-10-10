// hooks/customerHooks/useFavoriteHairdressers.ts
import { useCallback, useRef, useState } from 'react';
import { useFocusEffect, useRouter } from 'expo-router';
import { FavoriteHairdresser } from '@/models/FavoriteHairdresser.types';
import { listFavoriteHairdressers, removeFavoriteHairdresser } from '@/services/favorite-hairdresser.service';
import { problemMessage } from '@/utils/api-problem';

export const useFavoriteHairdressers = () => {
  const router = useRouter();

  const [favorites, setFavorites] = useState<FavoriteHairdresser[]>([]);
  // Only a successful fetch shows the empty message; a failure shows the error modal instead.
  const [isLoaded, setIsLoaded] = useState(false);
  const [removing, setRemoving] = useState(false);
  const removingRef = useRef(false);
  const [errorModal, setErrorModal] = useState<{ visible: boolean; message: string }>({ visible: false, message: '' });

  // Read again on every focus, so a heart toggled on a profile shows here when the customer comes back.
  useFocusEffect(
    useCallback(() => {
      let active = true;
      listFavoriteHairdressers()
        .then((list) => {
          if (!active) return;
          // The API already sends the most recently favorited first. A removal in flight owns the list.
          if (!removingRef.current) setFavorites(list);
          setIsLoaded(true);
        })
        .catch((error) => {
          if (!active) return;
          setIsLoaded(false);
          setErrorModal({ visible: true, message: problemMessage(error, 'Não foi possível carregar seus favoritos.') });
        });
      return () => {
        active = false;
      };
    }, [])
  );

  const handleRemove = async (hairdresserId: number) => {
    const index = favorites.findIndex((favorite) => favorite.id === hairdresserId);
    if (index < 0 || removingRef.current) return;
    const removed = favorites[index];
    // The card leaves at once, with no confirmation: favoriting again undoes it.
    setFavorites((current) => current.filter((favorite) => favorite.id !== hairdresserId));
    removingRef.current = true;
    setRemoving(true);
    try {
      await removeFavoriteHairdresser(hairdresserId);
    } catch (error) {
      // The card goes back to the position it had.
      setFavorites((current) => {
        if (current.some((favorite) => favorite.id === hairdresserId)) return current;
        const restored = [...current];
        restored.splice(Math.min(index, restored.length), 0, removed);
        return restored;
      });
      setErrorModal({ visible: true, message: problemMessage(error, 'Não foi possível atualizar seus favoritos.') });
    } finally {
      removingRef.current = false;
      setRemoving(false);
    }
  };

  const handleOpen = (hairdresserId: number) => router.push(`/(app)/customer/hairdresser-reservation/${hairdresserId}`);

  const handleGoBack = () => router.push('/(app)/customer/profile');

  return {
    favorites,
    isLoaded,
    removing,
    handleRemove,
    handleOpen,
    handleGoBack,
    errorModal,
    closeError: () => setErrorModal({ visible: false, message: '' }),
  };
};
