import axios from 'axios'; 
import { API_BACKEND_URL } from '@/app/_layout';
import axiosInstance from './axios-instance';

export const getPreferencesByUser = async (userID: number | undefined) => {
    if(!userID) {
        console.log("No userId provided to request preferences");
        return
    }
    try {
        const response = await axiosInstance.get(`${API_BACKEND_URL}/api/preferences/list/${userID}`);
        return response.data;
    } catch (error) {
        console.error("Error in getPreferencesByUser:", error);
        throw error;
    }
}

export const listPreferences = async () => {
    try {
        const response = await axiosInstance.get(`${API_BACKEND_URL}/api/preferences/list`);
        return response.data;
    } catch (error) {
        console.error("Error in getPreferencesByUser:", error);
        throw error;
    }
}