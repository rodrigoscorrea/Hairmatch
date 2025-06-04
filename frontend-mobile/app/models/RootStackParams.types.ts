import { ServiceResponse } from "./Service.types";
import { Hairdresser } from "./Hairdresser.types";
import { AvailabilityResponse, NonWorkingDays } from "./Availability.types";

export type RootStackParamList = {
  Home: undefined;
  Login: undefined;
  Register: undefined;
  HairdresserProfileReservation: {
    hairdresser : Hairdresser
    avatar: any //remover depois
  } 
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
    non_working_days: any;
    hairdresser: any;
  };
  CustomerHome: any,
  Search: any | undefined;
  Reserves: {
    customer: any;
  };
  Profile: any | undefined;
  Description: {
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
    preferences: number[]
    professionalStory: {
      experience_time: string, 
      experiences: string, 
      products: string
    }
  }
  ProfessionalStory:{ 
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
    preferences: number[]
  }
  HairdresserProfile: any | undefined
  HairdresserServiceManager: any | undefined
  HairdresserServiceCreation: any | undefined
  HairdresserServiceEdit: {
    service: ServiceResponse
  }
  AvailabilityManager: any | undefined
  AvailabilityCreate: any | undefined
  AvailabilityEdit: {
    availabilities: AvailabilityResponse[];
    nonWorkingDays: number[]
  };
};