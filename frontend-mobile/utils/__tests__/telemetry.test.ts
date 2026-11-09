/// <reference types="jest" />
/// <reference types="node" />
import * as fs from 'fs';
import * as path from 'path';

import * as native from '../telemetry';
import * as web from '../telemetry.web';

const TRACEPARENT = /^00-[0-9a-f]{32}-[0-9a-f]{16}-01$/;
const FLAG = 'EXPO_PUBLIC_TRACE_PROPAGATION';

const variants = [
  ['native', native],
  ['web', web],
] as const;

const original = process.env[FLAG];
afterEach(() => {
  if (original === undefined) delete process.env[FLAG];
  else process.env[FLAG] = original;
  jest.restoreAllMocks();
});

describe.each(variants)('%s telemetry', (_name, telemetry) => {
  it('makes 00-<32 hex>-<16 hex>-01 in lower case (TEL-68)', () => {
    for (let call = 0; call < 200; call += 1) {
      expect(telemetry.createTraceparent()).toMatch(TRACEPARENT);
    }
  });

  it('never makes a trace id or a parent id of zeros, even when the source gives only zeros (TEL-69)', () => {
    jest.spyOn(Math, 'random').mockReturnValue(0);
    jest.spyOn(globalThis.crypto, 'getRandomValues').mockImplementation(((array: Uint8Array) => array.fill(0)) as never);

    const [, traceId, parentId] = telemetry.createTraceparent().split('-');

    expect(traceId).not.toBe('0'.repeat(32));
    expect(parentId).not.toBe('0'.repeat(16));
    expect(telemetry.createTraceparent()).toMatch(TRACEPARENT);
  });

  it('draws the trace id again when the first draw is all zeros, and uses the second draw as it came (TEL-69)', () => {
    let nativeDraws = 0;
    let webDraws = 0;
    jest.spyOn(Math, 'random').mockImplementation(() => {
      nativeDraws += 1;
      return nativeDraws <= 16 ? 0 : 0.5; // 16 zero bytes, then 0x80 for everything else
    });
    jest.spyOn(globalThis.crypto, 'getRandomValues').mockImplementation(((array: Uint8Array) => {
      webDraws += 1;
      return array.fill(webDraws === 1 ? 0 : 0x80);
    }) as never);

    const [, traceId, parentId] = telemetry.createTraceparent().split('-');

    expect(traceId).toBe('80'.repeat(16));
    expect(parentId).toBe('80'.repeat(8));
  });

  it('gives a different trace id to each call (TEL-70)', () => {
    const ids = new Set(Array.from({ length: 500 }, () => telemetry.createTraceparent().split('-')[1]));
    expect(ids.size).toBe(500);
  });

  it('adds the header only when the flag is exactly `true` (TEL-68, TEL-71)', () => {
    process.env[FLAG] = 'true';
    expect(telemetry.traceHeaders()).toEqual({ traceparent: expect.stringMatching(TRACEPARENT) });

    for (const value of ['', 'false', 'TRUE', '1', 'yes', ' true']) {
      process.env[FLAG] = value;
      expect(telemetry.traceHeaders()).toEqual({});
    }
    delete process.env[FLAG];
    expect(telemetry.traceHeaders()).toEqual({});
    expect(telemetry.isTracePropagationEnabled()).toBe(false);
  });

  it('gives no header and does not throw when the generator fails (TEL-72)', () => {
    process.env[FLAG] = 'true';
    jest.spyOn(Math, 'random').mockImplementation(() => {
      throw new Error('no entropy');
    });
    jest.spyOn(globalThis.crypto, 'getRandomValues').mockImplementation(() => {
      throw new Error('no entropy');
    });

    expect(() => telemetry.traceHeaders()).not.toThrow();
    expect(telemetry.traceHeaders()).toEqual({});
  });
});

describe('the two versions (TEL-73, TEL-74)', () => {
  it('have the same exports', () => {
    expect(Object.keys(web).sort()).toEqual(Object.keys(native).sort());
    expect(Object.keys(native).sort()).toEqual(['createTraceparent', 'isTracePropagationEnabled', 'traceHeaders']);
  });

  it('import nothing, so the telemetry brings no native package', () => {
    for (const file of ['telemetry.ts', 'telemetry.web.ts']) {
      const source = fs.readFileSync(path.join(__dirname, '..', file), 'utf8');
      const code = source.replace(/\/\/.*$/gm, '');
      expect(code).not.toMatch(/\bimport\s|\brequire\(|\bfrom\s+['"]/);
    }
  });
});
