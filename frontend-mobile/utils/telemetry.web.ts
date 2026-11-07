// The web version of telemetry.ts (#194): the same exports, with the ids drawn from `crypto.getRandomValues`, which every
// browser that runs the app has. See telemetry.ts for what the module is for.

const TRACE_ID_BYTES = 16;
const PARENT_ID_BYTES = 8;
const MAX_DRAWS = 8;

const randomBytes = (count: number): Uint8Array => crypto.getRandomValues(new Uint8Array(count));

const toHex = (bytes: Uint8Array): string => Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('');

const isZero = (bytes: Uint8Array): boolean => !bytes.some((byte) => byte !== 0);

// W3C: an id of all zeros is invalid, so it is drawn again. After MAX_DRAWS the last byte is forced to 1.
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

export const createTraceparent = (): string => `00-${randomId(TRACE_ID_BYTES)}-${randomId(PARENT_ID_BYTES)}-01`;

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
