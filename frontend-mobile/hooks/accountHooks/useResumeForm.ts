import { useRef, useState } from 'react';
import { useAuth } from '@/app/_layout';
import { updateMe } from '@/services/account.service';
import { ACCOUNT_MAX_LENGTH, validateAccountUpdate } from '@/utils/account-validation';
import { problemMessage } from '@/utils/api-problem';

type FeedbackModal = { visible: boolean; title?: string; message: string };

export const RESUME_MAX_LENGTH = ACCOUNT_MAX_LENGTH.resume;

export const useResumeForm = () => {
  const { userInfo, loadSession } = useAuth();
  const initial: string = userInfo?.hairdresser?.resume ?? '';

  const [resume, setResume] = useState(initial);
  const [saving, setSaving] = useState(false);
  const [modal, setModal] = useState<FeedbackModal>({ visible: false, message: '' });
  const savingRef = useRef(false);

  // A saved change reloads userInfo: the form starts again from what the backend stored.
  const [seed, setSeed] = useState(initial);
  if (seed !== initial) {
    setSeed(initial);
    setResume(initial);
  }

  // A paste past the limit keeps only the first 1000 characters.
  const handleChange = (text: string) => setResume(text.slice(0, RESUME_MAX_LENGTH));

  const handleSave = async () => {
    if (savingRef.current) return;

    // The resume goes as typed: the backend stores it as is, and an empty one is allowed.
    if (resume === initial) {
      setModal({ visible: true, title: 'Aviso', message: 'Nenhuma alteração para salvar.' });
      return;
    }

    const validation = validateAccountUpdate({ resume });
    if (validation.messages.length > 0) {
      setModal({ visible: true, message: validation.messages[0] });
      return;
    }

    savingRef.current = true;
    setSaving(true);
    try {
      await updateMe({ resume });
      await loadSession();
      setModal({ visible: true, title: 'Sucesso', message: 'Dados atualizados com sucesso.' });
    } catch (error) {
      // The typed text stays on the screen for another try.
      setModal({ visible: true, message: problemMessage(error, 'Não foi possível salvar o resumo. Tente novamente.') });
    } finally {
      savingRef.current = false;
      setSaving(false);
    }
  };

  return {
    resume,
    count: resume.length,
    saving,
    modal,
    handleChange,
    handleSave,
    closeModal: () => setModal(prev => ({ ...prev, visible: false })),
  };
};
