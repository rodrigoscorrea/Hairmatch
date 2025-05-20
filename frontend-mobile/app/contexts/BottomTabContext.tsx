
import React, { createContext, useContext, ReactNode } from 'react';
import { Customer } from '../models/Customer.types';
import { AuthContext } from '../index';
import { UserRole } from '../models/User.types';

// Define the context type
type BottomTabContextType = {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  customer: Customer | null;
};

// Create the context with default values
export const BottomTabContext = createContext<BottomTabContextType>({
  activeTab: 'CustomerHome',
  setActiveTab: () => {},
  customer: null,
});

// Create a provider component
type BottomTabProviderProps = {
  children: ReactNode;
};

export const BottomTabProvider: React.FC<BottomTabProviderProps> = ({ children }) => {
  const [activeTab, setActiveTab] = React.useState<string>('CustomerHome');
  const { userInfo } = useContext(AuthContext);
  
  // We're assuming userInfo is a Customer if they're logged in as a customer

  const customer = userInfo?.customer.user.role === UserRole.CUSTOMER ? userInfo.customer : null;

  return (
    <BottomTabContext.Provider value={{ activeTab, setActiveTab, customer }}>
      {children}
    </BottomTabContext.Provider>
  );
};

// Create a custom hook for easy context usage
export const useBottomTab = () => useContext(BottomTabContext);
