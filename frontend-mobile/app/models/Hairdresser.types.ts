import { User } from "./User.types"

interface HairdresserBase {
    cnpj: string,
    experience_years: number,
    resume: string
}

export interface Hairdresser extends HairdresserBase{
    first_name: string, 
    last_name: string, 
    email: string, 
    password: string,
    phone: string,
    state: string,
    complement?: string,
    neighborhood: string,
    address: string,
    number?: string,
    postal_code: string,
    rating: number,
    role: string,
}

export interface HairdresserResponse extends HairdresserBase{
    id: string,
    user: User
}