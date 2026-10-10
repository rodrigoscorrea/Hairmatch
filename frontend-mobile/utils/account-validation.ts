import { ERROR_MESSAGES } from '@/constants/errorMessages';
import { AccountUpdate } from '@/services/account.service';
import { stripNonDigits } from './forms';

// The same limits as PATCH /api/users/me (the model's max_length and the resume cap).
export const ACCOUNT_MAX_LENGTH = {
  first_name: 100,
  last_name: 100,
  address: 150,
  neighborhood: 150,
  city: 150,
  complement: 150,
  number: 6,
  resume: 1000,
} as const;

export type AccountValidation = {
  errors: Partial<Record<keyof AccountUpdate, boolean>>;
  messages: string[];
};

const REQUIRED_MESSAGES = {
  first_name: ERROR_MESSAGES.first_name_required,
  last_name: ERROR_MESSAGES.last_name_required,
  phone: ERROR_MESSAGES.phone_required,
  postal_code: ERROR_MESSAGES.postal_code_required,
  address: ERROR_MESSAGES.address_required,
  neighborhood: ERROR_MESSAGES.neighborhood_required,
  city: ERROR_MESSAGES.city_required,
  state: ERROR_MESSAGES.state_required,
};

const TOO_LONG_MESSAGES = {
  first_name: ERROR_MESSAGES.first_name_too_long,
  last_name: ERROR_MESSAGES.last_name_too_long,
  address: ERROR_MESSAGES.address_too_long,
  number: ERROR_MESSAGES.number_invalid,
  complement: ERROR_MESSAGES.complement_too_long,
  neighborhood: ERROR_MESSAGES.neighborhood_too_long,
  city: ERROR_MESSAGES.city_too_long,
  resume: ERROR_MESSAGES.resume_too_long,
};

// Screen order, so the first message is about the first wrong field.
const FIELD_ORDER: (keyof AccountUpdate)[] = [
  'first_name', 'last_name', 'cpf', 'cnpj', 'phone',
  'postal_code', 'address', 'number', 'complement', 'neighborhood', 'city', 'state',
  'resume',
];

/**
 * Checks the body about to go to PATCH /api/users/me with the backend rules. Like the backend, only the fields
 * present are checked. The values are the ones sent: phone as "55" + digits (or '' when cleared), postal code and
 * documents as digits only.
 */
export const validateAccountUpdate = (fields: Partial<AccountUpdate>): AccountValidation => {
  const errors: AccountValidation['errors'] = {};
  const messages: string[] = [];
  const fail = (field: keyof AccountUpdate, message: string) => {
    errors[field] = true;
    messages.push(message);
  };

  FIELD_ORDER.forEach(field => {
    const value = fields[field];
    if (value === undefined) return;

    if (field in REQUIRED_MESSAGES && !value.trim()) {
      fail(field, REQUIRED_MESSAGES[field as keyof typeof REQUIRED_MESSAGES]);
      return;
    }
    if (field in ACCOUNT_MAX_LENGTH && value.length > ACCOUNT_MAX_LENGTH[field as keyof typeof ACCOUNT_MAX_LENGTH]) {
      fail(field, TOO_LONG_MESSAGES[field as keyof typeof TOO_LONG_MESSAGES]);
      return;
    }
    if (field === 'phone' && !/^55\d{10,11}$/.test(value)) fail(field, ERROR_MESSAGES.phone_invalid);
    if (field === 'postal_code' && stripNonDigits(value).length !== 8) fail(field, ERROR_MESSAGES.postal_code_invalid);
    if (field === 'state' && !/^[A-Za-z]{2}$/.test(value.trim())) fail(field, ERROR_MESSAGES.state_invalid);
    if (field === 'cpf' && stripNonDigits(value).length !== 11) fail(field, ERROR_MESSAGES.cpf_invalid);
    if (field === 'cnpj' && stripNonDigits(value).length !== 14) fail(field, ERROR_MESSAGES.cnpj_invalid);
  });

  return { errors, messages };
};
