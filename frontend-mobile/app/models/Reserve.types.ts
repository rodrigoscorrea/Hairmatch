import { ServiceWithHairdresserName } from "./Service.types";

export interface ReserveSlots {
    available_slots: string[]
}

export interface ReserveWithService {
    id: number;
    customer: number;
    review: any | null;
    service: ServiceWithHairdresserName;
    start_time: string;
}