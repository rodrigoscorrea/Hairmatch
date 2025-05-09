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