import { User } from "./User.types"

interface HairdresserBase {
    id?: number | undefined
    cnpj: string,
    experience_years?: number,
    resume: string
}

export interface Hairdresser extends HairdresserBase{
    user: User
    result_type?: string
}

export interface HairdresserResponse extends HairdresserBase{
    id: number,
    user: User
}

export interface HairdresserDescriptionAIRequest {
    first_name: string, 
    last_name: string,
    experience_time: string, 
    experiences: string, 
    products: string, 
    preferences: number[]
}