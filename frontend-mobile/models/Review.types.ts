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

/** A review as `GET /api/hairdressers/{id}/reviews` returns it: the customer comes nested with the name. */
export interface ReceivedReview extends Omit<Review, 'customer'> {
    customer: {
        id: number;
        user: { id: number; first_name: string; last_name: string };
    };
}
