import { Platform } from 'react-native';
import axiosInstance from './axios-instance';
import { GalleryPhoto } from '@/models/Gallery.types';
import { PickedImage } from './account.service';

// The callers read the failure with problemMessage, so no call here catches its error.

export const listGalleryPhotos = async (hairdresserId: number): Promise<GalleryPhoto[]> => {
  const response = await axiosInstance.get(`/api/hairdressers/${hairdresserId}/gallery-photos`);
  return response.data.data;
};

export const uploadGalleryPhoto = async (hairdresserId: number, picture: PickedImage): Promise<GalleryPhoto> => {
  const formData = new FormData();
  if (Platform.OS === 'web') {
    const blob = await (await fetch(picture.uri)).blob();
    formData.append('image', blob, picture.name);
  } else {
    formData.append('image', { uri: picture.uri, name: picture.name, type: picture.type } as any);
  }
  // The instance defaults to JSON, and axios 1.x would turn the FormData into JSON with that header.
  const response = await axiosInstance.post(`/api/hairdressers/${hairdresserId}/gallery-photos`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data.data;
};

export const removeGalleryPhoto = async (hairdresserId: number, photoId: number): Promise<void> => {
  await axiosInstance.delete(`/api/hairdressers/${hairdresserId}/gallery-photos/${photoId}`);
};
