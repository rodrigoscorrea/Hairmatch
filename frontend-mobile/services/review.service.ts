import { Platform } from 'react-native';
import { ReviewPicture } from '@/models/Review.types';
import axiosInstance from "./axios-instance";
import { PickedImage } from './account.service';

export type NewReview = {
    rating: number;
    comment: string;
    hairdresser: number;
    reserve: number;
    pictures: PickedImage[];
};

// The instance defaults to JSON, and axios 1.x would turn the FormData into JSON with that header.
const MULTIPART = { headers: { 'Content-Type': 'multipart/form-data' } };

// The web needs a Blob for a file field; the native FormData takes the {uri, name, type} object.
const appendPicture = async (formData: FormData, picture: PickedImage) => {
    if (Platform.OS === 'web') {
        const blob = await (await fetch(picture.uri)).blob();
        formData.append('pictures', blob, picture.name);
    } else {
        formData.append('pictures', { uri: picture.uri, name: picture.name, type: picture.type } as any);
    }
};

// The callers read the failure with problemMessage, so no call here catches its error.

/** POST /api/reviews: the review and up to 5 pictures, in the repeated `pictures` field. */
export const createReview = async (review: NewReview): Promise<void> => {
    const formData = new FormData();
    formData.append('rating', review.rating.toString());
    formData.append('comment', review.comment);
    formData.append('hairdresser', review.hairdresser.toString());
    formData.append('reserve', review.reserve.toString());
    for (const picture of review.pictures) {
        await appendPicture(formData, picture);
    }
    await axiosInstance.post('/api/reviews', formData, { withCredentials: true, ...MULTIPART });
};

/** PUT /api/reviews/{id}: the rating and the comment. It never touches the pictures. */
export const updateReview = async (id: number, review: { rating: number; comment: string }): Promise<void> => {
    await axiosInstance.put(`/api/reviews/${id}`, review, { withCredentials: true });
};

/** POST /api/reviews/{id}/pictures: adds pictures and returns every picture of the review. */
export const addReviewPictures = async (id: number, pictures: PickedImage[]): Promise<ReviewPicture[]> => {
    const formData = new FormData();
    for (const picture of pictures) {
        await appendPicture(formData, picture);
    }
    const response = await axiosInstance.post(`/api/reviews/${id}/pictures`, formData, {
        withCredentials: true,
        ...MULTIPART,
    });
    return response.data.data;
};

/** DELETE /api/reviews/{id}/pictures/{pictureId} */
export const deleteReviewPicture = async (id: number, pictureId: number): Promise<void> => {
    await axiosInstance.delete(`/api/reviews/${id}/pictures/${pictureId}`, { withCredentials: true });
};

export const deleteReview = async (reviewId: string | number) => {
    try {
        await axiosInstance.delete(`/api/reviews/${reviewId}`, {withCredentials: true});
        return true;
    } catch (error) {
        console.error("Error in delete reserve:", error);
        throw error;
    }
}
