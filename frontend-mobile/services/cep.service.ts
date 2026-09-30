import axiosInstance from './axios-instance';

export type CepAddress = {
  postal_code: string;
  address: string;
  neighborhood: string;
  city: string;
  state: string;
};

export const lookupCep = async (cep: string): Promise<CepAddress> => {
  const response = await axiosInstance.get<CepAddress>(`/api/postal-codes/${cep}`);
  return response.data;
};
