import axios from 'axios'; 
import { API_BACKEND_URL } from '../index';

export const listAgendaByHairdresser = async (hairdresserId: number | undefined) => {
    if(!hairdresserId) {
        console.error("hairdresser id not provided");
        return
    }
    
    try {
        const response = await axios.get(`${API_BACKEND_URL}/api/agenda/list/${hairdresserId}`);
        return response.data;
    } catch (error) {
        console.error("Error in list agenda by hairdresser:", error);
        throw error;
    }
}

export const createAgendaApointment = async (data: any) => {
    if(!data){
        console.error("no data provided for agenda apointment creation");
        return;
    }
    
    try {
        await axios.post(`${API_BACKEND_URL}/api/agenda/create`, data);
    } catch (error) {
        console.error("Error create agenda:", error);
        throw error;
    }
}
/*
export const updateAvailability = async (data: AvailabilityRequest[], hairdresserId: number | undefined) => {
    if(!hairdresserId){
        console.error("no hairdresser id provided for availability edition");
        return;
    }
    
    if(!data) {
        console.error("no data provided for availability edition");
        return;
    }
    try {
        await axios.put(`${API_BACKEND_URL}/api/availability/update/multiple/${hairdresserId}`, {availabilities: data});
    } catch (error) {
        console.error("Error updating availability:", error);
        throw error;
    }
} */