 import { API_BACKEND_URL } from '../index';
import axiosInstance from './axios-instance';

export const getReserveById = async (id:string | number) => {
    try {
        const response = await axiosInstance.get(`${API_BACKEND_URL}/api/reserve/${id}`);
        return response.data;
    } catch (error) {
        console.error("Error in getAvailableResearchSlots:", error);
        throw error;
    }
}

export const getAvailableResearchSlots = async (hairdresser_id: string | number, serviceId: number | string | undefined, selectedDate: string) => {
    try {
        const response = await axiosInstance.post(`${API_BACKEND_URL}/api/reserve/slots/${hairdresser_id}`, {service: serviceId, date: selectedDate});
        return response.data;
    } catch (error) {
        console.error("Error in getAvailableResearchSlots:", error);
        throw error;
    }
}

export const createReserve = async (reserveData: any) => {
    try {
        await axiosInstance.post(`${API_BACKEND_URL}/api/reserve/create`, reserveData);
        return
    } catch (error) {
        console.error("Error in createReserve:", error);
        throw error;
    }
}

export const getCustomerReserves = async (customerId: string | number) => {
    try {
        const response = await axiosInstance.get(`${API_BACKEND_URL}/api/reserve/list/${customerId}`);
        return response.data;
    } catch (error) {
        console.error("Error in get Reserve by customer:", error);
        throw error;
    }
}