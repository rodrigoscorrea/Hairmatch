import { useEffect, useMemo, useRef, useState } from 'react';
import { TextInput } from 'react-native';
import { useAuth } from '@/app/_layout';
import { useCepLookup } from '@/hooks/authHooks/useCepLookup';
import { AccountUpdate, updateMe } from '@/services/account.service';
import { CepAddress } from '@/services/cep.service';
import { validateAccountUpdate } from '@/utils/account-validation';
import { problemMessage } from '@/utils/api-problem';
import { formatCEP, stripNonDigits } from '@/utils/forms';

type AddressFields = Pick<
  AccountUpdate,
  'postal_code' | 'address' | 'number' | 'complement' | 'neighborhood' | 'city' | 'state'
>;
type AddressField = keyof AddressFields;
type FeedbackModal = { visible: boolean; title?: string; message: string };

const TEXT_FIELDS = ['address', 'number', 'complement', 'neighborhood', 'city'] as const;
const CEP_FIELDS = ['address', 'neighborhood', 'city', 'state'] as const;

const fieldsFrom = (user: any): AddressFields => ({
  postal_code: formatCEP(user?.postal_code),
  address: user?.address ?? '',
  number: user?.number ?? '',
  complement: user?.complement ?? '',
  neighborhood: user?.neighborhood ?? '',
  city: user?.city ?? '',
  state: user?.state ?? '',
});

// Only what changed goes to the PATCH, with the postal code as digits.
const changedFields = (values: AddressFields, initial: AddressFields): Partial<AccountUpdate> => {
  const body: Partial<AccountUpdate> = {};
  const postalCode = stripNonDigits(values.postal_code);
  if (postalCode !== stripNonDigits(initial.postal_code)) body.postal_code = postalCode;
  TEXT_FIELDS.forEach(field => {
    if (values[field].trim() !== initial[field].trim()) body[field] = values[field].trim();
  });
  const state = values.state.trim().toUpperCase();
  if (state !== initial.state.trim().toUpperCase()) body.state = state;
  return body;
};

export const useAddressForm = () => {
  const { userInfo, loadSession } = useAuth();
  const user = (userInfo?.customer ?? userInfo?.hairdresser)?.user;
  const initial = useMemo(() => fieldsFrom(user), [user]);

  const [values, setValues] = useState<AddressFields>(initial);
  const [errors, setErrors] = useState<Partial<Record<AddressField, boolean>>>({});
  const [saving, setSaving] = useState(false);
  const [modal, setModal] = useState<FeedbackModal>({ visible: false, message: '' });
  const savingRef = useRef(false);
  const { loading: cepLoading, message: cepMessage, lookup, cancel } = useCepLookup();
  const numberInputRef = useRef<TextInput>(null);
  // The other fields stay locked until the CEP has 8 digits, as at sign-up; they never lock again.
  const [addressUnlocked, setAddressUnlocked] = useState(stripNonDigits(initial.postal_code).length === 8);
  // Latest values for the async lookup callback, which would otherwise see a stale closure.
  const valuesRef = useRef(values);
  useEffect(() => {
    valuesRef.current = values;
  });
  // Values the last CEP lookup wrote, to tell them apart from what the user typed.
  const lastAutofillRef = useRef<Partial<CepAddress>>({});

  // A saved change reloads userInfo: the form starts again from what the backend stored.
  const [seed, setSeed] = useState(initial);
  if (seed !== initial) {
    setSeed(initial);
    setValues(initial);
    setErrors({});
  }

  const handleInputChange = (field: AddressField, value: string) => {
    setValues(prev => ({ ...prev, [field]: value }));
    if (errors[field]) setErrors(prev => ({ ...prev, [field]: false }));
  };

  // The same merge as sign-up (useAddress): a found field replaces the value, a missing one clears only what the
  // previous lookup wrote, and number and complement are never touched.
  const applyCepAddress = (found: CepAddress) => {
    const current = valuesRef.current;
    const merged: Partial<CepAddress> = {};
    const written: Partial<CepAddress> = {};
    CEP_FIELDS.forEach(field => {
      if (found[field]) {
        merged[field] = written[field] = found[field];
      } else if (current[field] === lastAutofillRef.current[field]) {
        merged[field] = written[field] = '';
      } else {
        merged[field] = current[field];
      }
    });
    lastAutofillRef.current = { ...lastAutofillRef.current, ...written };
    setValues(prev => ({ ...prev, ...merged }));
    setErrors(prev => {
      const next = { ...prev };
      CEP_FIELDS.forEach(field => { next[field] = false; });
      return next;
    });
    numberInputRef.current?.focus();
  };

  const handlePostalCodeChange = (text: string) => {
    const masked = formatCEP(text);
    handleInputChange('postal_code', masked);
    const digits = stripNonDigits(masked);
    if (digits.length === 8) {
      setAddressUnlocked(true);
      lookup(digits, applyCepAddress);
    } else {
      cancel();
    }
  };

  const handleSave = async () => {
    if (savingRef.current) return;

    const body = changedFields(values, initial);
    if (Object.keys(body).length === 0) {
      setModal({ visible: true, title: 'Aviso', message: 'Nenhuma alteração para salvar.' });
      return;
    }

    const validation = validateAccountUpdate(body);
    if (validation.messages.length > 0) {
      setErrors(validation.errors);
      setModal({ visible: true, message: validation.messages[0] });
      return;
    }

    savingRef.current = true;
    setSaving(true);
    try {
      await updateMe(body);
      await loadSession();
      setModal({ visible: true, title: 'Sucesso', message: 'Endereço atualizado com sucesso.' });
    } catch (error) {
      // The typed values stay on the screen for another try.
      setModal({ visible: true, message: problemMessage(error, 'Não foi possível salvar o endereço. Tente novamente.') });
    } finally {
      savingRef.current = false;
      setSaving(false);
    }
  };

  return {
    values,
    errors,
    handleInputChange,
    handlePostalCodeChange,
    cepLoading,
    cepMessage,
    numberInputRef,
    addressUnlocked,
    saving,
    modal,
    handleSave,
    closeModal: () => setModal(prev => ({ ...prev, visible: false })),
  };
};
