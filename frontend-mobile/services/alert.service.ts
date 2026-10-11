import axiosInstance from './axios-instance';
import { Alert, AlertList } from '@/models/Alert.types';

// The callers read the failure with problemMessage, so no call here catches its error.

/** The 50 newest alerts of the logged user, newest first, and how many of all of them are unread. */
export const getAlerts = async (): Promise<AlertList> => {
  const response = await axiosInstance.get('/api/users/me/alerts');
  return { alerts: response.data.data.alerts, unreadCount: response.data.data.unread_count };
};

export const markAlertRead = async (id: number, read: boolean): Promise<Alert> => {
  const response = await axiosInstance.patch(`/api/users/me/alerts/${id}`, { read });
  return response.data.data;
};

export const markAllAlertsRead = async (): Promise<void> => {
  await axiosInstance.patch('/api/users/me/alerts', { read: true });
};
