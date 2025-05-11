import axios from 'axios'; 
import { API_BACKEND_URL } from '../index';

export const getAvailableResearchSlots = async (hairdresser_id: string | number, serviceId: number, selectedDate: string) => {
    try {
        const response = await axios.post(`${API_BACKEND_URL}/api/reserve/slots/${hairdresser_id}`, {service: serviceId, date: selectedDate});
        return response.data;
    } catch (error) {
        console.error("Error in getAvailableResearchSlots:", error);
        throw error;
    }
}

export const createReserve = async (reserveData: any) => {
    try {
        await axios.post(`${API_BACKEND_URL}/api/reserve/create`, reserveData);
        return
    } catch (error) {
        console.error("Error in createReserve:", error);
        throw error;
    }
}