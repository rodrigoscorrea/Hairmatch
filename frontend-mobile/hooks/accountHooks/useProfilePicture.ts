import { useRef, useState } from 'react';
import * as ImagePicker from 'expo-image-picker';
import { useAuth } from '@/app/_layout';
import { removeProfilePicture, uploadProfilePicture } from '@/services/account.service';
import { problemMessage } from '@/utils/api-problem';

type FeedbackModal = { visible: boolean; message: string };

export const useProfilePicture = () => {
  const { userInfo, loadSession } = useAuth();
  const user = (userInfo?.customer ?? userInfo?.hairdresser)?.user;

  const [optionsVisible, setOptionsVisible] = useState(false);
  const [updating, setUpdating] = useState(false);
  const [modal, setModal] = useState<FeedbackModal>({ visible: false, message: '' });
  // Two taps can land before `updating` re-renders the picture as busy.
  const updatingRef = useRef(false);

  const openOptions = () => {
    if (!updatingRef.current) setOptionsVisible(true);
  };

  // Runs the upload or the removal, then reloads userInfo so every screen shows the stored picture.
  const update = async (request: () => Promise<unknown>, fallback: string) => {
    if (updatingRef.current) return;
    updatingRef.current = true;
    setUpdating(true);
    try {
      await request();
      await loadSession();
    } catch (error) {
      setModal({ visible: true, message: problemMessage(error, fallback) });
    } finally {
      updatingRef.current = false;
      setUpdating(false);
    }
  };

  // The same permission and picker as sign-up (useRegisterForm): square crop, quality 0.5.
  const handlePickNew = async () => {
    setOptionsVisible(false);
    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (status !== 'granted') {
      setModal({ visible: true, message: 'Permita o acesso às fotos para trocar a foto de perfil.' });
      return;
    }

    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ['images'],
      allowsEditing: true,
      aspect: [1, 1],
      quality: 0.5,
    });
    if (result.canceled) return;

    const asset = result.assets[0];
    await update(
      () =>
        uploadProfilePicture({
          uri: asset.uri,
          type: asset.mimeType || 'image/jpeg',
          name: asset.fileName || `profile_${Date.now()}.jpg`,
        }),
      'Não foi possível trocar a foto. Tente novamente.',
    );
  };

  const handleRemove = async () => {
    setOptionsVisible(false);
    await update(removeProfilePicture, 'Não foi possível remover a foto. Tente novamente.');
  };

  return {
    hasPicture: !!user?.profile_picture,
    optionsVisible,
    updating,
    modal,
    openOptions,
    closeOptions: () => setOptionsVisible(false),
    handlePickNew,
    handleRemove,
    closeModal: () => setModal(prev => ({ ...prev, visible: false })),
  };
};
