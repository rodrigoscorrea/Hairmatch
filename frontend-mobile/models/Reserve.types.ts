import { Review } from "./Review.types";
import { ServiceWithHairdresserFullInfo } from "./Service.types";

export interface ReserveSlots {
    available_slots: string[]
}

export interface ReserveWithService {
    id: number;
    customer: number;
    review: Review | null;
    service: ServiceWithHairdresserFullInfo;
    start_time: string;
}