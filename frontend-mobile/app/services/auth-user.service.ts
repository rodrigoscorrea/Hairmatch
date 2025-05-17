import axios from 'axios'; 
import { API_BACKEND_URL } from '../index';

export const getCustomerHomeInfo = async (email: string | undefined) => {
    if(!email) {
        console.error("hairdresser id not provided");
        return
    }

    try {
        const response = await axios.get(`${API_BACKEND_URL}/api/customer/home/${email}`);
        return response.data;
    } catch (error) {
        console.error("Error in get customer home info:", error);
        throw error;
    }
}