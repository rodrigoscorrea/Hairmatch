// A hairdresser's rating of the customer of a reservation (RT-86 and RT-87).

export interface CustomerRatingRequest {
    reservation: number;
    rating: number;
    comment?: string | null;
}

export interface CustomerRating {
    id: number;
    rating: number;
    comment: string | null;
    created_at: string;
    // Null once the reservation was deleted.
    service_name: string | null;
    // Null once the author's account was deleted.
    hairdresser_name: string | null;
}

// The rating a POST creates.
export interface CreatedCustomerRating {
    id: number;
    reservation: number | null;
    rating: number;
    comment: string | null;
    created_at: string;
}

export interface CustomerRatingsSummary {
    // Null while the customer has no rating.
    average: number | null;
    count: number;
    // All of them for the customer; only the hairdresser's own for a hairdresser.
    ratings: CustomerRating[];
}
