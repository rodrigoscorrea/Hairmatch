import axios from 'axios'; 
import { API_BACKEND_URL } from '@/app/_layout';
import { ServiceRequest, ServiceResponse } from '../models/Service.types';
import axiosInstance from './axios-instance';
export const listServicesByHairdresser = async (hairdresserId: number | undefined) => {
    if(!hairdresserId) {
        console.error("hairdresser id not provided");
        return
    }
    
    try {
        const response = await axiosInstance.get(`${API_BACKEND_URL}/api/service/hairdresser/${hairdresserId}`);
        return response.data;
    } catch (error) {
        console.error("Error in list services by hairdresser:", error);
        throw error;
    }
}

export const getServiceById = async (serviceId: number | undefined) => {
    if(!serviceId) {
        console.error("service id not provided");
        return
    }
    
    try {
        const response = await axiosInstance.get(`${API_BACKEND_URL}/api/service/list/${serviceId}`);
        return response.data;
    } catch (error) {
        console.error("Error in get service by id:", error);
        throw error;
    }
}

export const createService = async (data: ServiceRequest) => {
    if(!data) {
        console.error("no data provided for service creation");
        return;
    }
    try {
        await axiosInstance.post(`${API_BACKEND_URL}/api/service/create`, data);
    } catch (error) {
        console.error("Error create service:", error);
        throw error;
    }
}

export const editService = async (data: ServiceRequest) => {
    if(!data) {
        console.error("no data provided for service edition");
        return;
    }
    try {
        await axiosInstance.put(`${API_BACKEND_URL}/api/service/update/${data.id}`, data);
    } catch (error) {
        console.error("Error in service edition:", error);
        throw error;
    }
}

export const deleteService = async (serviceId: number) => {
    if(!serviceId) {
        console.error("no service id provided for deletion");
        return;
    }
    try {
        await axiosInstance.delete(`${API_BACKEND_URL}/api/service/remove/${serviceId}`);
    } catch (error) {
        console.error("Error to delete service:", error);
        throw error;
    }
}