export interface AuthContextType {
  signIn?: (email: string, password: string) => Promise<void>;
  signUp?: (
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
    cnpj?: string
  ) => Promise<any>;
  signOut?: () => Promise<void>;
  userInfo?: any;
}