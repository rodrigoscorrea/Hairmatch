import axios, { InternalAxiosRequestConfig } from 'axios';
import { Platform } from 'react-native';

const API_BACKEND_URL = process.env.EXPO_PUBLIC_API_BACKEND_URL;

// A 401 from these routes is a real answer (wrong password, no session to refresh...), not an expired access token.
const AUTH_EXCLUDED = ['/api/auth/login', '/api/auth/refresh', '/api/auth/logout', '/api/auth/google'];

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
      .post('/api/auth/refresh')
      .then(() => undefined)
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
};

axiosInstance.interceptors.request.use(
  (config) => {

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
      !AUTH_EXCLUDED.some((path) => config.url?.includes(path))
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

    console.error('Response error:', {
      url: error.config?.url,
      status: error.response?.status,
      data: error.response?.data,
      platform: Platform.OS
    });
    return Promise.reject(error);
  }
);

export default axiosInstance;
