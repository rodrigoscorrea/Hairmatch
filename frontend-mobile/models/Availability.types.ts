export interface AvailabilityRequest {
    weekday: string,
    start_time: string,
    end_time: string,
    break_start?: string | null,
    break_end?: string | null
}

export interface AvailabilityResponse extends AvailabilityRequest{
    id: number,
}

export interface NonWorkingDays {
    non_working_days: number[]
}