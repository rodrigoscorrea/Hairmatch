import axios from 'axios'; 
import { API_BACKEND_URL } from '../index';

export const listServicesByHairdresser = async (hairdresserId: number | undefined) => {
    if(!hairdresserId) {
        console.error("hairdresser id not provided");
        return
    }
    
    try {
        const response = await axios.get(`${API_BACKEND_URL}/api/service/hairdresser/${hairdresserId}`);
        return response.data;
    } catch (error) {
        console.error("Error in list services by hairdresser:", error);
        throw error;
    }
}

export const createService = async (data: any) => {
    if(!data) {
        console.error("no data provided for service creation");
        return;
    }
    try {
        await axios.post(`${API_BACKEND_URL}/api/service/create`, data);
    } catch (error) {
        console.error("Error create service:", error);
        throw error;
    }
}

export const deleteService = async (serviceId: number) => {
    if(!serviceId) {
        console.error("no service id provided for deletion");
        return;
    }
    try {
        await axios.delete(`${API_BACKEND_URL}/api/service/delete`);
    } catch (error) {
        console.error("Error to delete service:", error);
        throw error;
    }
}