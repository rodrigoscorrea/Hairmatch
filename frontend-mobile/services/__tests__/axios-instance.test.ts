/// <reference types="jest" />
import { AxiosError, AxiosResponse, InternalAxiosRequestConfig } from 'axios';

import axiosInstance from '../axios-instance';

const TRACEPARENT = /^00-[0-9a-f]{32}-[0-9a-f]{16}-01$/;
const FLAG = 'EXPO_PUBLIC_TRACE_PROPAGATION';

type Seen = { method?: string; url?: string; traceparent?: unknown };

const answer = (config: InternalAxiosRequestConfig, status: number): AxiosResponse => ({
  data: {},
  status,
  statusText: String(status),
  headers: {},
  config,
});

// Replaces the network under the interceptors; `reply` decides the status of each call, in order.
const stubNetwork = (reply: (call: number, seen: Seen) => number) => {
  const seen: Seen[] = [];
  axiosInstance.defaults.adapter = async (config: InternalAxiosRequestConfig) => {
    const entry = { method: config.method, url: config.url, traceparent: config.headers.get('traceparent') };
    seen.push(entry);
    const status = reply(seen.length, entry);
    const response = answer(config, status);
    if (status >= 400) {
      throw new AxiosError(`status ${status}`, 'ERR_BAD_RESPONSE', config, null, response);
    }
    return response;
  };
  return seen;
};

const original = process.env[FLAG];
afterEach(() => {
  if (original === undefined) delete process.env[FLAG];
  else process.env[FLAG] = original;
  jest.restoreAllMocks();
});

describe('axiosInstance and the traceparent', () => {
  it('adds a valid traceparent to every request when the flag is `true` (TEL-68)', async () => {
    process.env[FLAG] = 'true';
    const seen = stubNetwork(() => 200);

    await axiosInstance.get('/api/search');
    await axiosInstance.post('/api/auth/login', {});

    expect(seen.map((entry) => entry.traceparent)).toEqual([
      expect.stringMatching(TRACEPARENT),
      expect.stringMatching(TRACEPARENT),
    ]);
  });

  it('gives two requests different trace ids (TEL-70)', async () => {
    process.env[FLAG] = 'true';
    const seen = stubNetwork(() => 200);

    await axiosInstance.get('/api/search');
    await axiosInstance.get('/api/search');

    const [first, second] = seen.map((entry) => String(entry.traceparent).split('-')[1]);
    expect(first).not.toEqual(second);
  });

  it('adds no header when the flag is absent or is anything but `true` (TEL-71)', async () => {
    const seen = stubNetwork(() => 200);
    delete process.env[FLAG];
    await axiosInstance.get('/api/search');
    for (const value of ['', 'false', 'TRUE', '1']) {
      process.env[FLAG] = value;
      await axiosInstance.get('/api/search');
    }

    expect(seen).toHaveLength(5);
    expect(seen.every((entry) => entry.traceparent === undefined)).toBe(true);
  });

  it('sends the request without the header, with the same result, when the generator fails (TEL-72)', async () => {
    process.env[FLAG] = 'true';
    jest.spyOn(Math, 'random').mockImplementation(() => {
      throw new Error('no entropy');
    });
    const seen = stubNetwork(() => 200);

    const response = await axiosInstance.get('/api/search');

    expect(response.status).toBe(200);
    expect(seen[0].traceparent).toBeUndefined();
  });

  it('gives the 401, the refresh and the retry a traceparent each, all different (TEL-85)', async () => {
    process.env[FLAG] = 'true';
    const seen = stubNetwork((call) => (call === 1 ? 401 : 200));

    const response = await axiosInstance.get('/api/users/me');

    expect(response.status).toBe(200);
    expect(seen.map((entry) => [entry.method, entry.url])).toEqual([
      ['get', '/api/users/me'],
      ['post', '/api/auth/refresh'],
      ['get', '/api/users/me'],
    ]);
    const traceparents = seen.map((entry) => String(entry.traceparent));
    traceparents.forEach((value) => expect(value).toMatch(TRACEPARENT));
    expect(new Set(traceparents.map((value) => value.split('-')[1])).size).toBe(3);
    expect(new Set(traceparents.map((value) => value.split('-')[2])).size).toBe(3);
  });

  it('keeps the refresh without a header when the flag is off (TEL-71, TEL-85)', async () => {
    delete process.env[FLAG];
    const seen = stubNetwork((call) => (call === 1 ? 401 : 200));

    await axiosInstance.get('/api/users/me');

    expect(seen).toHaveLength(3);
    expect(seen.every((entry) => entry.traceparent === undefined)).toBe(true);
  });
});
