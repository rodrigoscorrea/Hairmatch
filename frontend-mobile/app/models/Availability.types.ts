export interface AvailabilityResponse {
    id: number,
    weekday: string,
    start_time: string,
    end_time: string,
    break_start: string | null,
    break_end: string | null
}