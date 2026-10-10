import { Platform } from 'react-native';
import axiosInstance from './axios-instance';

// The fields PATCH /api/users/me accepts. The phone is "55" + digits; postal code and documents are digits only.
export type AccountUpdate = {
  first_name: string;
  last_name: string;
  phone: string;
  address: string;
  number: string;
  complement: string;
  neighborhood: string;
  city: string;
  state: string;
  postal_code: string;
  cpf: string; // customer, 11 digits
  cnpj: string; // hairdresser, 14 digits
  resume: string; // hairdresser, at most 1000 characters
};

export type PickedImage = { uri: string; type: string; name: string };

// The callers read the failure with problemMessage, so no call here catches its error.

export const updateMe = async (fields: Partial<AccountUpdate>): Promise<void> => {
  await axiosInstance.patch('/api/users/me', fields);
};

export const deleteMe = async (): Promise<void> => {
  await axiosInstance.delete('/api/users/me');
};

export const uploadProfilePicture = async (picture: PickedImage): Promise<string> => {
  const formData = new FormData();
  if (Platform.OS === 'web') {
    const blob = await (await fetch(picture.uri)).blob();
    formData.append('profile_picture', blob, picture.name);
  } else {
    formData.append('profile_picture', { uri: picture.uri, name: picture.name, type: picture.type } as any);
  }
  // The instance defaults to JSON, and axios 1.x would turn the FormData into JSON with that header.
  const response = await axiosInstance.put('/api/users/me/profile-picture', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data.profile_picture;
};

export const removeProfilePicture = async (): Promise<void> => {
  await axiosInstance.delete('/api/users/me/profile-picture');
};

export const assignPreference = async (id: number): Promise<void> => {
  await axiosInstance.put(`/api/users/me/preferences/${id}`);
};

export const unassignPreference = async (id: number): Promise<void> => {
  await axiosInstance.delete(`/api/users/me/preferences/${id}`);
};
