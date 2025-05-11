import { ServiceResponse } from "./Service.types";

export type RootStackParamList = {
  Home: undefined;
  Login: undefined;
  Register: undefined;
  MockedHairdresserProfile: any;
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
  ServiceBooking: {
    service: ServiceResponse
    customer_id: string | number
    non_working_days: any
  }
};