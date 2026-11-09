import axios, { InternalAxiosRequestConfig } from 'axios';
import { Platform } from 'react-native';
import { REFRESH_PATH, isRefreshExcluded, pathnameOf } from './auth-routes';
import { traceHeaders } from '../utils/telemetry';

const API_BACKEND_URL = process.env.EXPO_PUBLIC_API_BACKEND_URL;

type RetriableConfig = InternalAxiosRequestConfig & { _retry?: boolean };

const axiosInstance = axios.create({
  baseURL: API_BACKEND_URL,
  timeout: 10000,
  withCredentials: Platform.OS === 'web',
  headers: {
    'Content-Type': 'application/json',
    'ngrok-skip-browser-warning': 'true'
  }
});

let sessionExpiredHandler: (() => void) | null = null;
let refreshPromise: Promise<void> | null = null;

// Called when the session cannot be refreshed. The auth context registers the state cleanup and the redirect.
export const setSessionExpiredHandler = (handler: () => void): void => {
  sessionExpiredHandler = handler;
};

// Calls that get a 401 at the same time share one refresh.
const refreshSession = (): Promise<void> => {
  if (!refreshPromise) {
    refreshPromise = axiosInstance
      .post(REFRESH_PATH)
      .then(() => undefined)
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
};

axiosInstance.interceptors.request.use(
  (config) => {
    // With EXPO_PUBLIC_TRACE_PROPAGATION=true each request, the refresh and the retry after it included, carries a
    // traceparent of its own, so the backend continues the trace the app started (#194). A failure sends it without.
    try {
      for (const [name, value] of Object.entries(traceHeaders())) {
        config.headers.set(name, value);
      }
    } catch {
      // The request goes out as it would with the flag off.
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

axiosInstance.interceptors.response.use(
  (response) => {
    return response;
  },
  async (error) => {
    const config: RetriableConfig | undefined = error.config;

    if (
      error.response?.status === 401 &&
      config &&
      !config._retry &&
      !isRefreshExcluded(config.method, config.url)
    ) {
      config._retry = true;
      try {
        await refreshSession();
      } catch (refreshError: any) {
        // Only an answer from the backend means the session is gone; a network failure keeps it.
        if (refreshError.response) {
          sessionExpiredHandler?.();
        }
        return Promise.reject(error);
      }
      return axiosInstance(config);
    }

    // A 401 from the refresh only means there is no session to restore (first visit, logout, expired refresh token).
    const noSessionToRestore = error.response?.status === 401 && pathnameOf(config?.url) === REFRESH_PATH;
    if (!noSessionToRestore) {
      console.error('Response error:', {
        url: error.config?.url,
        status: error.response?.status,
        data: error.response?.data,
        platform: Platform.OS
      });
    }
    return Promise.reject(error);
  }
);

export default axiosInstance;
