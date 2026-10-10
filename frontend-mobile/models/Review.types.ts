export interface ReviewPicture {
    id: number;
    url: string;
}

/** A review as `GET /api/reservations/{id}` and the review lists return it. Its pictures come by ascending id. */
export interface Review {
    id: number;
    rating: number;
    comment: string | null;
    created_at: string;
    customer: number;
    hairdresser: number;
    pictures: ReviewPicture[];
}
