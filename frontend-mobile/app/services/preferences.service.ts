import axios from 'axios'; 
import { API_BACKEND_URL } from '../index';

export const getPreferencesByUser = async (userID: string) => {
    try {
        const response = await axios.get(`${API_BACKEND_URL}/api/preferences/list/${userID}`);
        return response.data;
    } catch (error) {
        console.error("Error in getPreferencesByUser:", error);
        throw error;
    }
}