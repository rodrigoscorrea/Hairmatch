import { API_BACKEND_URL } from '@/app/_layout';
import { AgendaEntryResponse, CreateAgendaRequest } from '@/models/Agenda.types';
import axiosInstance from './axios-instance';
export const listAgendaByHairdresser = async (
    hairdresserId: number | undefined,
): Promise<{ data: AgendaEntryResponse[] } | undefined> => {
    if(!hairdresserId) {
        console.error("hairdresser id not provided");
        return
    }
    
    try {
        const response = await axiosInstance.get<{ data: AgendaEntryResponse[] }>(`${API_BACKEND_URL}/api/hairdressers/${hairdresserId}/agenda`);
        return response.data;
    } catch (error) {
        console.error("Error in list agenda by hairdresser:", error);
        throw error;
    }
}

export const createAgendaApointment = async (data: CreateAgendaRequest): Promise<void> => {
    if(!data){
        console.error("no data provided for agenda apointment creation");
        return;
    }
    
    try {
        await axiosInstance.post(`${API_BACKEND_URL}/api/agenda`, data);
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
        await axios.put(`${API_BACKEND_URL}/api/hairdressers/${hairdresserId}/availabilities`, {availabilities: data});
    } catch (error) {
        console.error("Error updating availability:", error);
        throw error;
    }
} */