import { Hairdresser } from "./Hairdresser.types"

interface Service {
    id: number,
    name: string,
    description: string
    price: string
    duration: number,
}

export interface ServiceResponse extends Service {
    hairdresser: number
}

export interface ServiceResponseWithHairdresser extends Service {
    hairdresser: Hairdresser
}

export interface ServiceRequest {
    id?: string | number
    hairdresser:number | undefined,
    name: string,
    description: string
    price: string
    duration: number,
}

export interface ServiceWithHairdresserName extends Service {
    hairdresser: {
        id: number,
        user: {
            id: number,
            first_name: string,
            last_name: string
        }
    }
}

export interface ServiceWithHairdresserFullInfo extends Service {
    hairdresser: Hairdresser
}