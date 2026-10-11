import axiosInstance from './axios-instance';

// A failure is the caller's to ignore: push is never worth an error screen.

/** Registers the phone for the logged user and returns the id that removes it again. 201 for a new phone, 200 for a known one. */
export const registerPushDevice = async (token: string): Promise<number> => {
  const response = await axiosInstance.post('/api/users/me/push-devices', { token });
  return response.data.data.id;
};

export const deletePushDevice = async (id: number): Promise<void> => {
  await axiosInstance.delete(`/api/users/me/push-devices/${id}`);
};
