import axios from 'axios'; 
import { API_BACKEND_URL } from '../index';

export const getHairdresser = async (email: string) => {
    try {
        const response = await axios.get(`${API_BACKEND_URL}/api/user/${email}`);
        return response.data;
    } catch (error) {
        console.error("Error in getHairdresser:", error);
        throw error;
    }
}