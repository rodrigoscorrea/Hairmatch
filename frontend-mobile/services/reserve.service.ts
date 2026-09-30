 import { API_BACKEND_URL } from '@/app/_layout';
import axiosInstance from './axios-instance';

export const getReserveById = async (id:string | number) => {
    try {
        const response = await axiosInstance.get(`${API_BACKEND_URL}/api/reservations/${id}`);
        return response.data;
    } catch (error) {
        console.error("Error in getAvailableResearchSlots:", error);
        throw error;
    }
}

export const getAvailableResearchSlots = async (hairdresser_id: string | number, serviceId: number | string | undefined, selectedDate: string) => {
    try {
        const response = await axiosInstance.get(`${API_BACKEND_URL}/api/hairdressers/${hairdresser_id}/available-slots`, {params: {service: serviceId, date: selectedDate}});
        return response.data;
    } catch (error) {
        console.error("Error in getAvailableResearchSlots:", error);
        throw error;
    }
}

export const createReserve = async (reserveData: any) => {
    try {
        await axiosInstance.post(`${API_BACKEND_URL}/api/reservations`, reserveData);
        return
    } catch (error) {
        console.error("Error in createReserve:", error);
        throw error;
    }
}

export const getCustomerReserves = async (customerId: string | number) => {
    try {
        const response = await axiosInstance.get(`${API_BACKEND_URL}/api/customers/${customerId}/reservations`);
        return response.data;
    } catch (error) {
        console.error("Error in get Reserve by customer:", error);
        throw error;
    }
}