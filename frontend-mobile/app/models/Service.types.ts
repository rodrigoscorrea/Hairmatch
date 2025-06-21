interface Service {
    id: number,
    name: string,
    description: string
    price: string
    duration: number,
}

export interface ServiceResponse extends Service {
    hairdresser: number
}

export interface ServiceRequest {
    id?: string | number
    hairdresser:number | undefined,
    name: string,
    description: string
    price: string
    duration: number,
}

export interface ServiceWithHairdresserName extends Service {
    hairdresser: {
        id: number,
        user: {
            id: number,
            first_name: string,
            last_name: string
        }
    }
}

export interface ServiceInfo {
    id: number,
    name: string;
    rating: number;
    date: string;
    time: string;
    service: string;
    location: string;
    address: string;
    phone: string;
    status: string;
  }