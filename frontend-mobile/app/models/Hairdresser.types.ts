import { User } from "./User.types"

interface HairdresserBase {
    id?: number | undefined
    cnpj: string,
    experience_years: number,
    resume: string
}

export interface Hairdresser extends HairdresserBase{
    user: User
}

export interface HairdresserResponse extends HairdresserBase{
    id: number,
    user: User
}