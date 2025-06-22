import axios from 'axios';
import { Platform } from 'react-native';

const API_BACKEND_URL = process.env.EXPO_PUBLIC_API_BACKEND_URL;

const axiosInstance = axios.create({
  baseURL: API_BACKEND_URL,
  timeout: 10000,
  withCredentials: Platform.OS === 'web',
  headers: {
    'Content-Type': 'application/json',
    'ngrok-skip-browser-warning': 'true'
  }
});

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
  (error) => {
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