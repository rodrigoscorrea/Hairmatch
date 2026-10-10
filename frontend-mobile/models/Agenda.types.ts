// An item of GET /api/hairdressers/{id}/agenda. The reservation fields are null when the slot has no reservation.
export interface AgendaItemResponse {
    id: number;
    start_time: string;
    end_time: string;
    service: { id: number; name: string };
    reservation_id: number | null;
    customer: {
        id: number;
        user: { first_name: string; last_name: string; rating: number | null };
        ratings_count: number;
    } | null;
    customer_rating: { rating: number; comment: string | null } | null;
}

export interface AgendaEvent {
    id: any;
    title: string;
    start: Date;
    end: Date;
    reservationId: number | null;
    customer: {
        id: number;
        name: string;
        rating: number | null;
        ratingsCount: number;
    } | null;
    // The hairdresser's rating of this reservation's customer, or null while it is not rated.
    customerRating: { rating: number; comment: string | null } | null;
}
  
export type CalendarMode = 'month' | 'week' | 'day' | 'agenda';

export interface AgendaViewProps {
    events: AgendaEvent[];
    onEventPress: (event: AgendaEvent) => void;
}