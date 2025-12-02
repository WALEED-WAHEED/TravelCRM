import apiClient from '@/api/client';

export type FlightClass = 'economy' | 'business' | 'first';
export type FlightStatus = 'scheduled' | 'delayed' | 'cancelled' | 'completed';

export interface Flight {
  id: number;
  airline: string;
  flight_number: string;
  departure_airport: string;
  arrival_airport: string;
  departure_city: string;
  arrival_city: string;
  departure_country: string;
  arrival_country: string;
  departure_time: string;
  arrival_time: string;
  duration_minutes: number;
  flight_class: FlightClass;
  price: number;
  currency: string;
  available_seats: number;
  total_seats: number;
  status: FlightStatus;
  baggage_allowance: string;
  meal_included: boolean;
  notes?: string;
  created_by: {
    id: number;
    username: string;
    full_name: string;
  };
  agency: {
    id: number;
    name: string;
  };
  created_at: string;
  updated_at: string;
}

export interface CreateFlightData {
  airline: string;
  flight_number: string;
  departure_airport: string;
  arrival_airport: string;
  departure_city: string;
  arrival_city: string;
  departure_country: string;
  arrival_country: string;
  departure_time: string;
  arrival_time: string;
  flight_class: FlightClass;
  price: number;
  currency?: string;
  available_seats: number;
  total_seats: number;
  status?: FlightStatus;
  baggage_allowance: string;
  meal_included?: boolean;
  notes?: string;
}

export interface UpdateFlightData {
  airline?: string;
  flight_number?: string;
  departure_airport?: string;
  arrival_airport?: string;
  departure_city?: string;
  arrival_city?: string;
  departure_country?: string;
  arrival_country?: string;
  departure_time?: string;
  arrival_time?: string;
  flight_class?: FlightClass;
  price?: number;
  currency?: string;
  available_seats?: number;
  total_seats?: number;
  status?: FlightStatus;
  baggage_allowance?: string;
  meal_included?: boolean;
  notes?: string;
}

export interface FlightListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: Flight[];
}

export interface FlightFilters {
  departure_city?: string;
  arrival_city?: string;
  departure_country?: string;
  arrival_country?: string;
  departure_date?: string;
  flight_class?: FlightClass;
  status?: FlightStatus;
  min_price?: number;
  max_price?: number;
  search?: string;
  page?: number;
  page_size?: number;
}

export const flightService = {
  /**
   * Get all flights with optional filters
   */
  getFlights: async (filters?: FlightFilters): Promise<FlightListResponse> => {
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          params.append(key, String(value));
        }
      });
    }

    const response = await apiClient.get<FlightListResponse>(
      `/api/v1/flights/?${params.toString()}`
    );
    return response.data;
  },

  /**
   * Get single flight by ID
   */
  getFlightById: async (id: number): Promise<Flight> => {
    const response = await apiClient.get<Flight>(`/api/v1/flights/${id}/`);
    return response.data;
  },

  /**
   * Create new flight
   */
  createFlight: async (data: CreateFlightData): Promise<Flight> => {
    const response = await apiClient.post<Flight>('/api/v1/flights/', data);
    return response.data;
  },

  /**
   * Update existing flight
   */
  updateFlight: async (id: number, data: UpdateFlightData): Promise<Flight> => {
    const response = await apiClient.patch<Flight>(`/api/v1/flights/${id}/`, data);
    return response.data;
  },

  /**
   * Delete flight
   */
  deleteFlight: async (id: number): Promise<void> => {
    await apiClient.delete(`/api/v1/flights/${id}/`);
  },

  /**
   * Search flights
   */
  searchFlights: async (
    departureCity: string,
    arrivalCity: string,
    departureDate: string,
    flightClass?: FlightClass
  ): Promise<Flight[]> => {
    const params: any = {
      departure_city: departureCity,
      arrival_city: arrivalCity,
      departure_date: departureDate,
    };
    
    if (flightClass) {
      params.flight_class = flightClass;
    }

    const response = await apiClient.get<Flight[]>('/api/v1/flights/search/', {
      params,
    });
    return response.data;
  },

  /**
   * Check seat availability
   */
  checkAvailability: async (id: number, seats: number): Promise<boolean> => {
    const response = await apiClient.get<{ available: boolean }>(
      `/api/v1/flights/${id}/availability/`,
      {
        params: { seats },
      }
    );
    return response.data.available;
  },
};

export default flightService;

