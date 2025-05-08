import axios from 'axios'; 
import { API_URL } from '../index';

export const listAvailabilitiesByHairdresser = async (hairdresserId: string | undefined) => {
    if(!hairdresserId) {
        console.error("hairdresser id not provided");
        return
    }
    
    try {
        const response = await axios.get(`${API_URL}/api/availability/list/${hairdresserId}`);
        return response.data;
    } catch (error) {
        console.error("Error in list availabilities by hairdresser:", error);
        throw error;
    }
}