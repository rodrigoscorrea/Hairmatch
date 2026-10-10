import { useCallback, useRef, useState } from 'react';
import { useFocusEffect } from 'expo-router';
import { listGalleryPhotos } from '@/services/gallery.service';
import { GalleryPhoto } from '@/models/Gallery.types';

/**
 * The gallery of a hairdresser for the "Galeria" strip. It loads on every focus, so the profile of the hairdresser
 * shows what changed in the gallery screen on the way back. A failure leaves the list empty, and the strip hides.
 */
export const useGalleryPhotos = (hairdresserId?: number) => {
  const [photos, setPhotos] = useState<GalleryPhoto[]>([]);
  // A slow answer for a previous hairdresser must not replace the current list.
  const latest = useRef(0);

  const refresh = useCallback(async () => {
    const request = ++latest.current;
    if (!hairdresserId) {
      setPhotos([]);
      return;
    }
    let loaded: GalleryPhoto[] = [];
    try {
      loaded = await listGalleryPhotos(hairdresserId);
    } catch {
      loaded = [];
    }
    if (request === latest.current) setPhotos(loaded);
  }, [hairdresserId]);

  useFocusEffect(
    useCallback(() => {
      refresh();
    }, [refresh]),
  );

  return { photos, refresh };
};
