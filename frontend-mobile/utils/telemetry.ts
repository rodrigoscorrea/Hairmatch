// The trace context the app sends to the backend (#194). When EXPO_PUBLIC_TRACE_PROPAGATION is `true`, each request
// carries a W3C `traceparent`, so the trace of the backend starts from the id the app made. Nothing here may break a request:
// a failure gives no header and the request goes out as it would with the flag off.
//
// Native version. The web one (telemetry.web.ts) has the same exports and draws the ids from `crypto.getRandomValues`.
// A trace id is not a secret, it only links a request to its trace, so `Math.random` is enough and no native package is needed.

const TRACE_ID_BYTES = 16;
const PARENT_ID_BYTES = 8;
const MAX_DRAWS = 8;

const randomBytes = (count: number): number[] => {
  const bytes: number[] = [];
  for (let index = 0; index < count; index += 1) {
    bytes.push(Math.floor(Math.random() * 256));
  }
  return bytes;
};

const toHex = (bytes: number[]): string => bytes.map((byte) => byte.toString(16).padStart(2, '0')).join('');

// W3C: an id of all zeros is invalid, so it is drawn again. After MAX_DRAWS the last byte is forced to 1.
const isZero = (bytes: number[]): boolean => !bytes.some((byte) => byte !== 0);

const randomId = (count: number): string => {
  let bytes = randomBytes(count);
  for (let draw = 1; draw < MAX_DRAWS && isZero(bytes); draw += 1) {
    bytes = randomBytes(count);
  }
  if (isZero(bytes)) {
    bytes[count - 1] = 1;
  }
  return toHex(bytes);
};

export const isTracePropagationEnabled = (): boolean => process.env.EXPO_PUBLIC_TRACE_PROPAGATION === 'true';

// `00-<32 hex>-<16 hex>-01`: version 00, sampled. It may throw: the caller is `traceHeaders`.
export const createTraceparent = (): string => `00-${randomId(TRACE_ID_BYTES)}-${randomId(PARENT_ID_BYTES)}-01`;

// The headers to add to a request: `{ traceparent }` with the flag on, `{}` otherwise or if the generator fails.
export const traceHeaders = (): Record<string, string> => {
  if (!isTracePropagationEnabled()) {
    return {};
  }
  try {
    return { traceparent: createTraceparent() };
  } catch {
    return {};
  }
};
