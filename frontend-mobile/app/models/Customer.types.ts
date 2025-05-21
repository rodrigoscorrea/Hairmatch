import { User } from "./User.types"

export interface Customer {
    id: number | string
    cpf: string,
    user: User
}