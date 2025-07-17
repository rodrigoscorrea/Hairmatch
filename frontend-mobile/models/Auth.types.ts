import { Preference } from "./Preferences.types";

export interface AuthContextType {
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (
    first_name: string,
    last_name: string,
    phone: string,
    email: string,
    password: string,
    address: string,
    number: string,
    neighborhood: string,
    complement: string,
    postal_code: string,
    state: string,
    city: string,
    role: string,
    rating: number,
    cpf?: string,
    cnpj?: string,
    preferences?: Preference[],
    experience_time?: string,
    experiences?: string,
    products?: string,
    resume?: string
  ) => Promise<any>;
  signOut: () => Promise<void>;
  getUserInfo: () => Promise<any>; 
  userInfo?: any;
}