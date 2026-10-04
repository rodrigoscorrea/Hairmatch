import axios from 'axios';
import { ERROR_MESSAGES } from '@/constants/errorMessages';

// The backend answers every error in RFC 9457 (application/problem+json). Its `type` ends with a slug from the
// catalog below, and the screens show the pt-BR text of that slug. The English `detail` is never shown to the user.

export type ProblemSlug =
  | 'validation-error'
  | 'malformed-request'
  | 'invalid-image'
  | 'invalid-postal-code'
  | 'password-policy'
  | 'incorrect-current-password'
  | 'email-change-unsupported'
  | 'invalid-confirmation-code'
  | 'confirmation-code-expired'
  | 'invalid-session'
  | 'invalid-credentials'
  | 'session-expired'
  | 'invalid-google-token'
  | 'signup-session-expired'
  | 'forbidden'
  | 'hairdresser-required'
  | 'customer-required'
  | 'google-account-login'
  | 'google-email-unverified'
  | 'email-not-confirmed'
  | 'not-found'
  | 'postal-code-not-found'
  | 'method-not-allowed'
  | 'email-taken'
  | 'phone-taken'
  | 'google-account-taken'
  | 'google-email-linked'
  | 'availability-exists'
  | 'agenda-overlap'
  | 'service-has-reservations'
  | 'review-exists'
  | 'slot-unavailable'
  | 'customer-schedule-conflict'
  | 'unsupported-media-type'
  | 'too-many-requests'
  | 'internal-error'
  | 'auth-unavailable'
  | 'postal-code-service-unavailable'
  | 'ai-service-unavailable';

export interface ApiProblemError {
  pointer?: string;
  parameter?: string;
  detail: string;
}

export interface ApiProblem {
  // Last segment of the problem `type`. A ProblemSlug for the catalog, any other string for a slug the app does not know.
  slug: ProblemSlug | (string & {});
  status: number;
  // English, for logs. Never shown to the user.
  detail: string;
  errors: ApiProblemError[];
}

export const CONNECTION_ERROR_MESSAGE = 'Não foi possível conectar ao servidor.';

const GENERIC_MESSAGE = 'Não foi possível processar a solicitação. Tente novamente.';

export const PROBLEM_MESSAGES: Record<ProblemSlug, string> = {
  'validation-error': 'Alguns dados estão inválidos. Revise e tente novamente.',
  'malformed-request': GENERIC_MESSAGE,
  'invalid-image': 'A imagem enviada é inválida. Escolha outra foto.',
  'invalid-postal-code': 'CEP inválido. Informe 8 dígitos.',
  'password-policy': 'A senha deve ter ao menos 8 caracteres, com letra maiúscula, letra minúscula e número.',
  'incorrect-current-password': 'Senha atual incorreta.',
  'email-change-unsupported': 'A troca de e-mail não é suportada.',
  'invalid-confirmation-code': 'Código inválido. Confira o e-mail ou peça um novo código.',
  'confirmation-code-expired': 'Este código venceu. Peça um novo código.',
  'invalid-session': 'Sua sessão expirou. Entre novamente.',
  'invalid-credentials': 'E-mail ou senha inválidos.',
  'session-expired': 'Sessão expirada. Entre novamente.',
  'invalid-google-token': 'Não foi possível validar sua conta Google. Tente novamente.',
  'signup-session-expired': 'Sua sessão de cadastro com o Google expirou. Entre com o Google novamente.',
  'forbidden': 'Você não tem permissão para acessar este recurso.',
  'hairdresser-required': 'Apenas profissionais podem realizar esta ação.',
  'customer-required': 'Apenas clientes podem realizar esta ação.',
  'google-account-login': 'Esta conta usa login com Google. Use o botão Entrar com Google.',
  'google-email-unverified': 'Seu e-mail do Google não está verificado.',
  'email-not-confirmed': 'Confirme seu e-mail para entrar.',
  'not-found': 'Não encontramos o que você procurou.',
  'postal-code-not-found': ERROR_MESSAGES.cep_not_found,
  'method-not-allowed': GENERIC_MESSAGE,
  'email-taken': 'Usuário já está cadastrado na nossa base de dados.',
  'phone-taken': 'O número de telefone inserido já está cadastrado na nossa base de dados.',
  'google-account-taken': 'Esta conta Google já está cadastrada na nossa base de dados.',
  'google-email-linked': 'Este e-mail já está vinculado a outra conta Google.',
  'availability-exists': 'Já existe uma disponibilidade para este dia.',
  'agenda-overlap': 'Este horário se sobrepõe a outro compromisso.',
  // No final period: PD-84 fixes this exact text, the one the service screen already showed.
  'service-has-reservations': 'Não é possível excluir esse serviço pois há um agendamento atrelado a ele',
  'review-exists': 'Esta reserva já foi avaliada.',
  'slot-unavailable': 'O profissional não está disponível neste horário.',
  'customer-schedule-conflict': 'Você já tem outra reserva agendada para o mesmo horário.',
  'unsupported-media-type': GENERIC_MESSAGE,
  'too-many-requests': 'Muitas tentativas. Aguarde e tente novamente.',
  'internal-error': 'Ocorreu um erro no servidor. Tente novamente mais tarde.',
  'auth-unavailable': 'Serviço de autenticação indisponível. Tente novamente em instantes.',
  'postal-code-service-unavailable': ERROR_MESSAGES.cep_lookup_failed,
  'ai-service-unavailable': 'Não foi possível gerar a descrição agora. Tente novamente.',
};

// Thrown by the native sign-up when the request never reached the backend (fetch rejects instead of answering).
export class ApiConnectionError extends Error {
  constructor() {
    super(CONNECTION_ERROR_MESSAGE);
    this.name = 'ApiConnectionError';
  }
}

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value);

// The axios error carries the body in `response.data`; the sign-up throws the body itself.
const bodyOf = (error: unknown): unknown => {
  const body = axios.isAxiosError(error) ? error.response?.data : error;
  if (typeof body === 'string') {
    try {
      return JSON.parse(body);
    } catch {
      return null;
    }
  }
  return body;
};

const toErrors = (value: unknown): ApiProblemError[] =>
  (Array.isArray(value) ? value : [])
    .filter((item): item is Record<string, unknown> => isRecord(item) && typeof item.detail === 'string')
    .map((item) => ({
      ...(typeof item.pointer === 'string' ? { pointer: item.pointer } : {}),
      ...(typeof item.parameter === 'string' ? { parameter: item.parameter } : {}),
      detail: item.detail as string,
    }));

/**
 * Turns whatever a failed call threw into an ApiProblem: an AxiosError (axiosInstance or raw axios),
 * the parsed problem body (the native sign-up throws it) or a JSON string of it.
 * Returns null when it is not a problem+json (no response, HTML, another error).
 */
export const toApiProblem = (error: unknown): ApiProblem | null => {
  const body = bodyOf(error);
  if (!isRecord(body) || typeof body.type !== 'string') return null;

  const slug = body.type.split('/').pop() ?? '';
  const status =
    typeof body.status === 'number'
      ? body.status
      : axios.isAxiosError(error)
        ? error.response?.status ?? 0
        : 0;

  return {
    slug,
    status,
    detail: typeof body.detail === 'string' ? body.detail : '',
    errors: toErrors(body.errors),
  };
};

/** Whether the call never got an answer from the backend (network down, timeout). */
export const isConnectionError = (error: unknown): boolean =>
  error instanceof ApiConnectionError || (axios.isAxiosError(error) && !error.response);

/**
 * The pt-BR text to show for a failed call: the catalog text of the problem slug. Without a response it is the
 * connection message; with an unknown slug or a body that is not a problem it is `fallback`, the generic text of the screen.
 */
export const problemMessage = (error: unknown, fallback: string): string => {
  if (isConnectionError(error)) return CONNECTION_ERROR_MESSAGE;
  const problem = toApiProblem(error);
  if (problem && Object.prototype.hasOwnProperty.call(PROBLEM_MESSAGES, problem.slug)) {
    return PROBLEM_MESSAGES[problem.slug as ProblemSlug];
  }
  return fallback;
};
