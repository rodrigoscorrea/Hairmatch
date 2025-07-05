import axiosInstance from "./axios-instance";
import { API_BACKEND_URL } from "@/app/_layout";

export const createReview = async (reviewData: FormData) => {
    try {
        await axiosInstance.post(`${API_BACKEND_URL}/api/review/register`, reviewData);
        return
    } catch (error) {
        console.error("Error in createReview:", error);
        throw error;
    }
}