/**
 * An item of `GET /api/hairdressers/{id}/agenda`. An external block has `service`, `customer` and `reservation_id`
 * set to null. The reservation fields are also null when the slot has no reservation.
 */
export interface AgendaEntryResponse {
    id: number;
    start_time: string;
    end_time: string;
    title: string;
    service: { id: number; name: string } | null;
    reservation_id: number | null;
    customer: {
        id: number;
        user: { first_name: string; last_name: string; rating: number | null };
        ratings_count: number;
    } | null;
    customer_rating: { id: number; rating: number; comment: string | null } | null;
}

/** The body of `POST /api/agenda`. Without `service`, `title` and `end_time` are required. */
export interface CreateAgendaRequest {
    start_time: string; // YYYY-MM-DDTHH:mm:00, read as Manaus time
    end_time: string;
    title?: string;
    service?: number;
}

export interface AgendaEvent {
    id: number;
    title: string;
    start: Date;
    end: Date;
    isExternal: boolean;
    reservationId: number | null;
    customer: {
        id: number;
        name: string;
        rating: number | null;
        ratingsCount: number;
    } | null;
    // The hairdresser's rating of this reservation's customer, or null while it is not rated.
    customerRating: { id: number; rating: number; comment: string | null } | null;
}
  
export type CalendarMode = 'month' | 'week' | 'day' | 'agenda';

export interface AgendaViewProps {
    events: AgendaEvent[];
    onEventPress: (event: AgendaEvent) => void;
}