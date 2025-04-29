export type RootStackParamList = {
    Home: undefined
    Login: undefined
    Register: undefined
    Address: {
        first_name: string 
        last_name: string 
        phone: string 
        email: string 
        cnpj?: string 
        cpf?: string 
        password: string 
        role: string
      }
}