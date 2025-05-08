export type RootStackParamList = {
  Home: undefined;
  Login: undefined;
  Register: undefined;
  Address: {
    personalData: {
      first_name: string;
      last_name: string;
      phone: string;
      email: string;
      cnpj?: string;
      cpf?: string;
      password: string;
      role: string;
    }
  };
  Preferences: {
    personalData: {
      first_name: string;
      last_name: string;
      phone: string;
      email: string;
      cnpj?: string;
      cpf?: string;
      password: string;
      role: string;
    },
    addressData: {
      address: string;
      number: string;
      complement: string;
      neighborhood: string;
      postal_code: string;
      city: string;
      state: string;
    }
  };
};