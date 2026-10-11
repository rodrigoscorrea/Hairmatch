import axiosInstance from './axios-instance';
import { FavoriteHairdresser } from '@/models/FavoriteHairdresser.types';

// The callers read the failure with problemMessage, so no call here catches its error.

/** The favorites of the logged customer, the most recently favorited first. */
export const listFavoriteHairdressers = async (): Promise<FavoriteHairdresser[]> => {
  const response = await axiosInstance.get('/api/customers/me/favorite-hairdressers');
  return response.data.data;
};

export const addFavoriteHairdresser = async (hairdresserId: number): Promise<void> => {
  await axiosInstance.put(`/api/customers/me/favorite-hairdressers/${hairdresserId}`);
};

export const removeFavoriteHairdresser = async (hairdresserId: number): Promise<void> => {
  await axiosInstance.delete(`/api/customers/me/favorite-hairdressers/${hairdresserId}`);
};
