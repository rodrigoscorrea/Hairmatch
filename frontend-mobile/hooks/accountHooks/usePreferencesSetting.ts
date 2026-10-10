import { useCallback, useEffect, useRef, useState } from 'react';
import { useAuth } from '@/app/_layout';
import { Preference } from '@/models/Preferences.types';
import { assignPreference, unassignPreference } from '@/services/account.service';
import { getPreferencesByUser, listPreferences } from '@/services/preferences.service';
import { problemMessage, toApiProblem } from '@/utils/api-problem';

type FeedbackModal = { visible: boolean; title?: string; message: string };

const LOAD_FALLBACK = 'Não foi possível carregar as preferências. Tente novamente.';

export const usePreferencesSetting = () => {
  const { userInfo } = useAuth();
  const userId: number | undefined = (userInfo?.customer ?? userInfo?.hairdresser)?.user?.id;

  const [catalog, setCatalog] = useState<Preference[]>([]);
  // What the backend has stored, to tell the added from the removed ones on save.
  const [saved, setSaved] = useState<number[]>([]);
  const [selected, setSelected] = useState<number[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadFailed, setLoadFailed] = useState(false);
  const [saving, setSaving] = useState(false);
  const [modal, setModal] = useState<FeedbackModal>({ visible: false, message: '' });
  const savingRef = useRef(false);

  // The route answers 404 when the user has no preference: that is an empty list, not an error.
  const fetchUserPreferences = useCallback(async (): Promise<number[]> => {
    try {
      const preferences: Preference[] = (await getPreferencesByUser(userId)) ?? [];
      return preferences.map(preference => preference.id);
    } catch (error) {
      if (toApiProblem(error)?.status === 404) return [];
      throw error;
    }
  }, [userId]);

  useEffect(() => {
    if (!userId) return;
    let active = true;
    const load = async () => {
      setLoading(true);
      try {
        const [all, current] = await Promise.all([listPreferences(), fetchUserPreferences()]);
        if (!active) return;
        setCatalog(all);
        setSaved(current);
        setSelected(current);
        setLoadFailed(false);
      } catch (error) {
        // Without the catalog or the stored list, a save would compare against the wrong state: Save stays disabled.
        if (!active) return;
        setLoadFailed(true);
        setModal({ visible: true, message: problemMessage(error, LOAD_FALLBACK) });
      } finally {
        if (active) setLoading(false);
      }
    };
    load();
    return () => {
      active = false;
    };
  }, [userId, fetchUserPreferences]);

  const togglePreference = (id: number) => {
    setSelected(prev => (prev.includes(id) ? prev.filter(prefId => prefId !== id) : [...prev, id]));
  };

  const handleSave = async () => {
    if (savingRef.current || loadFailed) return;

    const added = selected.filter(id => !saved.includes(id));
    const removed = saved.filter(id => !selected.includes(id));
    if (added.length === 0 && removed.length === 0) {
      setModal({ visible: true, title: 'Aviso', message: 'Nenhuma alteração para salvar.' });
      return;
    }

    savingRef.current = true;
    setSaving(true);
    try {
      // One call at a time, stopping at the first failure.
      for (const id of added) await assignPreference(id);
      for (const id of removed) await unassignPreference(id);
      setSaved(selected);
      setModal({ visible: true, title: 'Sucesso', message: 'Preferências atualizadas com sucesso.' });
    } catch (error) {
      setModal({ visible: true, message: problemMessage(error, 'Não foi possível salvar as preferências. Tente novamente.') });
      // Some calls may have gone through: show what the backend kept.
      try {
        const current = await fetchUserPreferences();
        setSaved(current);
        setSelected(current);
      } catch {
        // The save error is already on the screen; the selection stays as typed.
      }
    } finally {
      savingRef.current = false;
      setSaving(false);
    }
  };

  return {
    catalog,
    selected,
    loading,
    saving,
    saveDisabled: loading || loadFailed || saving,
    modal,
    togglePreference,
    handleSave,
    closeModal: () => setModal(prev => ({ ...prev, visible: false })),
  };
};
