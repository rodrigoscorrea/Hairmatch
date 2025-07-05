import { API_BACKEND_URL } from "@/app/_layout";
import axios from 'axios';
import { Platform } from "react-native";
import axiosInstance from "./axios-instance";

export const createReview = async (reviewData: FormData) => {
    try {
        await axios.post(`${API_BACKEND_URL}/api/review/register`, reviewData, {withCredentials: Platform.OS === 'web'});
        return
    } catch (error) {
        console.error("Error in createReview:", error);
        throw error;
    }
}

export const deleteReview = async (reviewId: string | number) => {
    try {
        await axiosInstance.delete(`${API_BACKEND_URL}/api/review/remove/${reviewId}`);
        return true;
    } catch (error) {
        console.error("Error in delete reserve:", error);
        throw error;
    }
}