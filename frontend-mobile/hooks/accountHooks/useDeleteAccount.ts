import { useRef, useState } from 'react';
import { useRouter } from 'expo-router';
import { useAuth } from '@/app/_layout';
import { deleteMe } from '@/services/account.service';
import { problemMessage } from '@/utils/api-problem';
import { AccountRole } from './useAccountForm';

const DELETE_WARNING = 'Esta ação é permanente. Sua conta, suas reservas e suas avaliações serão apagadas.';
const HAIRDRESSER_WARNING = 'As reservas dos seus clientes serão canceladas.';

export const useDeleteAccount = (role: AccountRole) => {
  const router = useRouter();
  const { clearSession } = useAuth();
  const [confirmVisible, setConfirmVisible] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [errorModal, setErrorModal] = useState({ visible: false, message: '' });
  // The confirmation modal has no disabled state: a second tap during the request must not send another DELETE.
  const deletingRef = useRef(false);

  const cancelDelete = () => {
    if (!deletingRef.current) setConfirmVisible(false);
  };

  const confirmDelete = async () => {
    if (deletingRef.current) return;
    deletingRef.current = true;
    setDeleting(true);
    try {
      await deleteMe();
    } catch (error) {
      // The account and the session stay.
      deletingRef.current = false;
      setDeleting(false);
      setConfirmVisible(false);
      setErrorModal({ visible: true, message: problemMessage(error, 'Não foi possível excluir a conta. Tente novamente.') });
      return;
    }
    // The 204 already cleared the cookies. Leave for the login before userInfo empties, in the same tick, so the
    // layout never sees the token while on the login nor a settings screen without a user.
    setConfirmVisible(false);
    router.replace('/(auth)/login');
    clearSession();
  };

  return {
    confirmVisible,
    deleting,
    description: role === 'hairdresser' ? `${DELETE_WARNING} ${HAIRDRESSER_WARNING}` : DELETE_WARNING,
    errorModal,
    openDelete: () => setConfirmVisible(true),
    cancelDelete,
    confirmDelete,
    closeError: () => setErrorModal(prev => ({ ...prev, visible: false })),
  };
};
