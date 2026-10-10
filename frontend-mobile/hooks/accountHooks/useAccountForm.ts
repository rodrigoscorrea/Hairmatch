import { useMemo, useRef, useState } from 'react';
import { useAuth } from '@/app/_layout';
import { AccountUpdate, updateMe } from '@/services/account.service';
import { validateAccountUpdate } from '@/utils/account-validation';
import { problemMessage } from '@/utils/api-problem';
import { formatCNPJ, formatCPF, formatPhone, stripNonDigits } from '@/utils/forms';

export type AccountRole = 'customer' | 'hairdresser';
type AccountFields = { first_name: string; last_name: string; phone: string; document: string };
type AccountField = keyof AccountFields;
type FeedbackModal = { visible: boolean; title?: string; message: string };

const documentFieldOf = (role: AccountRole) => (role === 'customer' ? 'cpf' : 'cnpj');
const formatDocument = (role: AccountRole, value?: string) =>
  role === 'customer' ? formatCPF(value) : formatCNPJ(value);

// The stored phone carries the country code; the screen shows it without, the way sign-up asks for it.
// A phone in another format (the seed's raw ones) is shown as its digits.
const localPhone = (stored?: string) => {
  const digits = stripNonDigits(stored ?? '');
  return digits.startsWith('55') && (digits.length === 12 || digits.length === 13) ? digits.slice(2) : digits;
};

const fieldsFrom = (profile: any, role: AccountRole): AccountFields => ({
  first_name: profile?.user?.first_name ?? '',
  last_name: profile?.user?.last_name ?? '',
  phone: formatPhone(localPhone(profile?.user?.phone)),
  document: formatDocument(role, profile?.[documentFieldOf(role)]),
});

// Only what changed goes to the PATCH, so a stored value the backend would no longer accept is never resent.
const changedFields = (values: AccountFields, initial: AccountFields, role: AccountRole): Partial<AccountUpdate> => {
  const body: Partial<AccountUpdate> = {};
  (['first_name', 'last_name'] as const).forEach(field => {
    if (values[field].trim() !== initial[field].trim()) body[field] = values[field].trim();
  });
  const phone = stripNonDigits(values.phone);
  if (phone !== stripNonDigits(initial.phone)) body.phone = phone ? `55${phone}` : '';
  const document = stripNonDigits(values.document);
  if (document !== stripNonDigits(initial.document)) body[documentFieldOf(role)] = document;
  return body;
};

export const useAccountForm = (role: AccountRole) => {
  const { userInfo, loadSession } = useAuth();
  const profile = userInfo?.[role];
  const initial = useMemo(() => fieldsFrom(profile, role), [profile, role]);

  const [values, setValues] = useState<AccountFields>(initial);
  const [errors, setErrors] = useState<Partial<Record<AccountField, boolean>>>({});
  const [saving, setSaving] = useState(false);
  const [modal, setModal] = useState<FeedbackModal>({ visible: false, message: '' });
  // Two taps can land before `saving` re-renders the button as disabled.
  const savingRef = useRef(false);

  // A saved change reloads userInfo: the form starts again from what the backend stored.
  // Reset during render, as React advises for state derived from a prop, instead of in an effect.
  const [seed, setSeed] = useState(initial);
  if (seed !== initial) {
    setSeed(initial);
    setValues(initial);
    setErrors({});
  }

  const handleChange = (field: AccountField, text: string) => {
    const value =
      field === 'phone' ? formatPhone(text) : field === 'document' ? formatDocument(role, text) : text;
    setValues(prev => ({ ...prev, [field]: value }));
    if (errors[field]) setErrors(prev => ({ ...prev, [field]: false }));
  };

  const handleSave = async () => {
    if (savingRef.current) return;

    const body = changedFields(values, initial, role);
    if (Object.keys(body).length === 0) {
      setModal({ visible: true, title: 'Aviso', message: 'Nenhuma alteração para salvar.' });
      return;
    }

    const validation = validateAccountUpdate(body);
    if (validation.messages.length > 0) {
      const { cpf, cnpj, ...rest } = validation.errors;
      setErrors({ ...rest, document: cpf || cnpj });
      setModal({ visible: true, message: validation.messages[0] });
      return;
    }

    savingRef.current = true;
    setSaving(true);
    try {
      await updateMe(body);
      await loadSession();
      setModal({ visible: true, title: 'Sucesso', message: 'Dados atualizados com sucesso.' });
    } catch (error) {
      // The typed values stay on the screen for another try.
      setModal({ visible: true, message: problemMessage(error, 'Não foi possível salvar os dados. Tente novamente.') });
    } finally {
      savingRef.current = false;
      setSaving(false);
    }
  };

  return {
    values,
    errors,
    email: profile?.user?.email ?? '',
    profilePicture: profile?.user?.profile_picture as string | undefined,
    saving,
    modal,
    handleChange,
    handleSave,
    closeModal: () => setModal(prev => ({ ...prev, visible: false })),
  };
};
