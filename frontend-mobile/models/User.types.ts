import { Customer } from "./Customer.types"
import { Hairdresser } from "./Hairdresser.types"

export enum UserRole {
    CUSTOMER = 'customer',
    HAIRDRESSER = 'hairdresser'
}

export interface User {
    id: number,
    first_name: string,
    last_name: string,
    email: string,
    phone: string,
    address: string
    number: string,
    postal_code: string,
    rating: number,
    role: string,
    complement: string,
    neighborhood: string,
    city: string,
    state: string
    profile_picture?: string
}

/* export interface CustomerHomeHairdresserData {
    id: number,
    first_name: string,
    last_name: string,
    email: string,
    phone: string,
    address: string,
    rating: number,
    city: string,
    state: string,
    neighborhood: string,
    number: string,
    postal_code: string
    resume: string
} */

export interface CustomerHomeInfoResponse {
    for_you: Hairdresser[]
    hairdressers_by_preferences: {
        coloracao: Hairdresser[]
        cachos: Hairdresser[]
        barbearia: Hairdresser[]
        trancas: Hairdresser[]
    }
}

export interface UserInfo {
    hairdresser?: Hairdresser
    customer?: Customer
}