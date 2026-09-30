import axios from 'axios'; 
import { API_BACKEND_URL } from '@/app/_layout';
import { HairdresserDescriptionAIRequest } from '../models/Hairdresser.types';
import axiosInstance from './axios-instance';
// The home of the logged customer: the backend takes the customer from the session.
export const getCustomerHomeInfo = async () => {
    try {
        const response = await axiosInstance.get(`${API_BACKEND_URL}/api/customers/me/home`);
        return response.data;
    } catch (error) {
        console.error("Error in get customer home info:", error);
        throw error;
    }
}

export const requestAiResume = async (data: HairdresserDescriptionAIRequest) => {
    try {
        const response: any = await axiosInstance.post(`${API_BACKEND_URL}/api/hairdressers/description-drafts`, data)
        return response.data.result
    } catch (error) {
        console.error("Error in request Ai resume:", error);
        throw error;
    }
}

export async function searchHairdressers(query: string) {
  try {
    const response = await axiosInstance.get(`${API_BACKEND_URL}/api/search`, {
      params: { q: query },
    });
    return response.data;
  } catch (error) {
    console.error("Search error:", error);
    throw error;
  }
}