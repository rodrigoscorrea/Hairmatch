import axios from 'axios'; 
import { API_URL } from '../index';

export const listServicesByHairdresser = async (hairdresserId: string | undefined) => {
    if(!hairdresserId) {
        console.error("hairdresser id not provided");
        return
    }
    
    try {
        const response = await axios.get(`${API_URL}/api/service/hairdresser/${hairdresserId}`);
        return response.data;
    } catch (error) {
        console.error("Error in list services by hairdresser:", error);
        throw error;
    }
}