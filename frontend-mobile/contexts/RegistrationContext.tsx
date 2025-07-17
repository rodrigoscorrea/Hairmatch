// contexts/RegistrationContext.tsx
import React, { createContext, useState, useContext, Dispatch, SetStateAction } from 'react';

// Define the shape of all the data we'll collect
interface IRegistrationData {
  // From step 1
  first_name?: string;
  last_name?: string;
  cpf?: string;
  cnpj?: string;
  email?: string;
  phone?: string;
  confirmPassword?: string;
  password?: string;
  role?: string;
  profile_picture: any;
  // From step 2 (address)
  address?: string;
  number?: string;
  complement?: string;
  neighborhood?: string;
  postal_code?: string;
  city?: string;
  state?: string;
  // From future steps
  preferences?: number[]

  experience_time?: string;
  experiences?: string;
  products?: string;
  resume?: string;
}

// Define what our context will provide
interface IRegistrationContext {
  registrationData: IRegistrationData;
  setRegistrationData: Dispatch<SetStateAction<IRegistrationData>>;
}

// Create the context with a default value
const RegistrationContext = createContext<IRegistrationContext | undefined>(undefined);

// Create the Provider component
export const RegistrationProvider = ({ children }: { children: React.ReactNode }) => {
  const [registrationData, setRegistrationData] = useState<IRegistrationData>({
    // Step 1 fields
    first_name: '',
    last_name: '',
    cpf: '',
    cnpj: '',
    email: '',
    phone: '',
    confirmPassword: '',
    password: '',
    role: '', // Or set a default like UserRole.CUSTOMER
    profile_picture: null,
    
    // Step 2 fields
    address: '',
    number: '',
    complement: '',
    neighborhood: '',
    postal_code: '',
    city: '',
    state: '',

    // Future step fields
    preferences: [], // An empty array is a valid, defined value

    experience_time: '',
    experiences: '',
    products: '',
    resume: '',
  });

  return (
    <RegistrationContext.Provider value={{ registrationData, setRegistrationData }}>
      {children}
    </RegistrationContext.Provider>
  );
};

// Create a custom hook for easy access to the context
export const useRegistration = () => {
  const context = useContext(RegistrationContext);
  if (!context) {
    throw new Error('useRegistration must be used within a RegistrationProvider');
  }
  return context;
};