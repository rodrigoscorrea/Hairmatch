import { API_BACKEND_URL } from "@/app/_layout";
import axios from 'axios';
import { Platform} from "react-native";
import axiosInstance from "./axios-instance";

export const createReview = async (reviewData: FormData) => {
    try {
        if(Platform.OS==='web') {
            await axios.post(`${API_BACKEND_URL}/api/review/register`, reviewData, {withCredentials: true});
        } else {
            await axios.post(`${API_BACKEND_URL}/api/review/register`, reviewData, {
                withCredentials: true,
                headers: {
                    'Content-Type': 'multipart/form-data',
                }
            },
        );
        }
        return
    } catch (error) {
        console.error("Error in createReview:", error);
        throw error;
    }
}

export const deleteReview = async (reviewId: string | number) => {
    try {
        await axios.delete(`${API_BACKEND_URL}/api/review/remove/${reviewId}`, {withCredentials: true});
        return true;
    } catch (error) {
        console.error("Error in delete reserve:", error);
        throw error;
    }
}