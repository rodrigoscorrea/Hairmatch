import axios from 'axios'; 
import { API_BACKEND_URL } from '../index';
import { HairdresserDescriptionAIRequest } from '../models/Hairdresser.types';
import axiosInstance from './axios-instance';
export const getCustomerHomeInfo = async (email?: string | undefined) => {
    try {
        let response;
        if(!email) {
            response = await axiosInstance.get(`${API_BACKEND_URL}/api/customer/home`);
        } else {
            response = await axiosInstance.get(`${API_BACKEND_URL}/api/customer/home/${email}`);
        }
        return response.data;
    } catch (error) {
        console.error("Error in get customer home info:", error);
        throw error;
    }
}

export const requestAiResume = async (data: HairdresserDescriptionAIRequest) => {
    try {
        const response: any = await axiosInstance.post(`${API_BACKEND_URL}/api/hairdresser/gemini_completion`, data)
        return response.data.result
    } catch (error) {
        console.error("Error in request Ai resume:", error);
        throw error;
    }
}

export async function searchHairdressers(query: string) {
  try {
    const response = await axiosInstance.get(`${API_BACKEND_URL}/api/user/search`, {
      params: { search: query },
    });
    return response.data;
  } catch (error) {
    console.error("Search error:", error);
    throw error;
  }
}