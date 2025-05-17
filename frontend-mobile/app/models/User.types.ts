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
}

interface customerHomeHairdresserData {
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
}

export interface CustomerHomeInfoResponse {
    for_you: customerHomeHairdresserData[]
    hairdressers_by_preferences: {
        coloracao: customerHomeHairdresserData[]
        cachos: customerHomeHairdresserData[]
        barbearia: customerHomeHairdresserData[]
        trancas: customerHomeHairdresserData[]
    }
}