export type RootStackParamList = {
    Home: any
    Login: any
    Register: any
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