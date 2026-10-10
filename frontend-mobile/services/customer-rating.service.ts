import { API_BACKEND_URL } from '@/app/_layout';
import {
    CreatedCustomerRating,
    CustomerRatingRequest,
    CustomerRatingsSummary,
} from '../models/CustomerRating.types';
import axiosInstance from './axios-instance';

export const createCustomerRating = async (data: CustomerRatingRequest): Promise<{ data: CreatedCustomerRating }> => {
    try {
        const response = await axiosInstance.post(`${API_BACKEND_URL}/api/customer-ratings`, data);
        return response.data;
    } catch (error) {
        console.error("Error in create customer rating:", error);
        throw error;
    }
}

export const getCustomerRatings = async (customerId: number): Promise<{ data: CustomerRatingsSummary }> => {
    try {
        const response = await axiosInstance.get(`${API_BACKEND_URL}/api/customers/${customerId}/ratings`);
        return response.data;
    } catch (error) {
        console.error("Error in get customer ratings:", error);
        throw error;
    }
}
