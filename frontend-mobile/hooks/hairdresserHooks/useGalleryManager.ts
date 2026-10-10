import { useCallback, useEffect, useRef, useState } from 'react';
import { useRouter } from 'expo-router';
import * as ImagePicker from 'expo-image-picker';
import { useAuth } from '@/app/_layout';
import { listGalleryPhotos, removeGalleryPhoto, uploadGalleryPhoto } from '@/services/gallery.service';
import { GALLERY_MAX_PHOTOS, GalleryPhoto } from '@/models/Gallery.types';
import { problemMessage, toApiProblem } from '@/utils/api-problem';

type FeedbackModal = { visible: boolean; message: string };
type Progress = { current: number; total: number };

/** The state of the "Minha galeria" screen: the grid, the multi-photo upload and the removal with confirmation. */
export const useGalleryManager = () => {
  const router = useRouter();
  const { userInfo } = useAuth();
  const hairdresserId = userInfo?.hairdresser?.id;

  const [photos, setPhotos] = useState<GalleryPhoto[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState<Progress | null>(null);
  const [pendingRemoval, setPendingRemoval] = useState<GalleryPhoto | null>(null);
  const [modal, setModal] = useState<FeedbackModal>({ visible: false, message: '' });
  // Two taps can land before `busy` re-renders the buttons as disabled.
  const busyRef = useRef(false);

  const count = photos.length;
  const canAdd = count < GALLERY_MAX_PHOTOS && !busy;

  const showMessage = (message: string) => setModal({ visible: true, message });

  const reload = useCallback(async () => {
    if (!hairdresserId) return;
    try {
      setPhotos(await listGalleryPhotos(hairdresserId));
    } catch (error) {
      showMessage(problemMessage(error, 'Não foi possível carregar a galeria. Tente novamente.'));
    }
  }, [hairdresserId]);

  useEffect(() => {
    reload().finally(() => setLoading(false));
  }, [reload]);

  // Runs `task` with the screen locked: no second upload or removal can start until it ends.
  const runLocked = async (task: () => Promise<void>) => {
    if (busyRef.current) return;
    busyRef.current = true;
    setBusy(true);
    try {
      await task();
    } finally {
      busyRef.current = false;
      setBusy(false);
      setProgress(null);
    }
  };

  const pickAndUpload = () =>
    runLocked(async () => {
      if (!hairdresserId || count >= GALLERY_MAX_PHOTOS) return;

      const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (status !== 'granted') {
        showMessage('Permita o acesso às fotos para adicionar fotos à galeria.');
        return;
      }

      const slots = GALLERY_MAX_PHOTOS - count;
      // The same picker as sign-up, with several photos and no crop (the picker cannot crop a selection).
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ['images'],
        allowsMultipleSelection: true,
        selectionLimit: slots,
        quality: 0.5,
      });
      if (result.canceled) return;

      // The web picker ignores selectionLimit, so the cut happens here too.
      const assets = result.assets.slice(0, slots);
      const notices: string[] = [];
      if (result.assets.length > slots) {
        notices.push(`Só cabem mais ${slots} fotos. As outras não foram enviadas.`);
      }

      // One request per photo, one at a time: the backend serializes them anyway, and "i de K" stays exact.
      let failures = 0;
      let firstFailure = '';
      for (let index = 0; index < assets.length; index++) {
        const asset = assets[index];
        setProgress({ current: index + 1, total: assets.length });
        try {
          await uploadGalleryPhoto(hairdresserId, {
            uri: asset.uri,
            type: asset.mimeType || 'image/jpeg',
            name: asset.fileName || `gallery_${Date.now()}_${index}.jpg`,
          });
        } catch (error) {
          failures += 1;
          if (!firstFailure) firstFailure = problemMessage(error, 'Não foi possível enviar a foto. Tente novamente.');
        }
      }
      setProgress(null);

      await reload();
      if (failures > 0) notices.push(`${failures} de ${assets.length} fotos não foram enviadas. ${firstFailure}`);
      if (notices.length > 0) showMessage(notices.join('\n'));
    });

  const requestRemove = (photo: GalleryPhoto) => {
    if (!busyRef.current) setPendingRemoval(photo);
  };

  const cancelRemove = () => setPendingRemoval(null);

  const confirmRemove = () => {
    const photo = pendingRemoval;
    setPendingRemoval(null);
    if (!photo || !hairdresserId) return Promise.resolve();
    return runLocked(async () => {
      try {
        await removeGalleryPhoto(hairdresserId, photo.id);
        setPhotos((current) => current.filter((item) => item.id !== photo.id));
      } catch (error) {
        // Removed from another session: the grid is stale, not wrong.
        if (toApiProblem(error)?.slug === 'not-found') {
          await reload();
        } else {
          showMessage(problemMessage(error, 'Não foi possível remover a foto. Tente novamente.'));
        }
      }
    });
  };

  return {
    photos,
    loading,
    count,
    canAdd,
    busy,
    progress,
    pendingRemoval,
    modal,
    pickAndUpload,
    requestRemove,
    confirmRemove,
    cancelRemove,
    closeModal: () => setModal((current) => ({ ...current, visible: false })),
    handleBack: () => router.back(),
  };
};
