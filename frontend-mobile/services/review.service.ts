import axiosInstance from "./axios-instance";

export const createReview = async (reviewData: FormData) => {
    try {
        // The instance defaults to JSON, and axios 1.x would turn the FormData into JSON with that header.
        await axiosInstance.post('/api/review/register', reviewData, {
            withCredentials: true,
            headers: {
                'Content-Type': 'multipart/form-data',
            }
        });
        return
    } catch (error) {
        console.error("Error in createReview:", error);
        throw error;
    }
}

export const deleteReview = async (reviewId: string | number) => {
    try {
        await axiosInstance.delete(`/api/review/remove/${reviewId}`, {withCredentials: true});
        return true;
    } catch (error) {
        console.error("Error in delete reserve:", error);
        throw error;
    }
}
