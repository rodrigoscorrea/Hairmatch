import axios from 'axios'; 
import { API_BACKEND_URL } from '@/app/_layout';
import axiosInstance from './axios-instance';
export const getHairdresser = async (id: string | number) => {
    try {
        const response = await axiosInstance.get(`${API_BACKEND_URL}/api/hairdresser/${id}`);
        return response.data;
    } catch (error) {
        console.error("Error in getHairdresser:", error);
        throw error;
    }
}