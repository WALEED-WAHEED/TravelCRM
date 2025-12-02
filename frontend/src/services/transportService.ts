import apiClient from '@/api/client';

export type TransportType = 'bus' | 'car' | 'van' | 'coach' | 'train' | 'other';
export type TransportStatus = 'available' | 'booked' | 'in_service' | 'maintenance';

export interface Transport {
  id: number;
  name: string;
  transport_type: TransportType;
  vehicle_number: string;
  capacity: number;
  driver_name: string;
  driver_phone: string;
  price_per_km: number;
  price_per_day: number;
  currency: string;
  status: TransportStatus;
  from_location?: string;
  to_location?: string;
  pickup_time?: string;
  amenities: string[];
  notes?: string;
  is_active: boolean;
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

export interface CreateTransportData {
  name: string;
  transport_type: TransportType;
  vehicle_number: string;
  capacity: number;
  driver_name: string;
  driver_phone: string;
  price_per_km: number;
  price_per_day: number;
  currency?: string;
  status?: TransportStatus;
  from_location?: string;
  to_location?: string;
  pickup_time?: string;
  amenities?: string[];
  notes?: string;
  is_active?: boolean;
}

export interface UpdateTransportData {
  name?: string;
  transport_type?: TransportType;
  vehicle_number?: string;
  capacity?: number;
  driver_name?: string;
  driver_phone?: string;
  price_per_km?: number;
  price_per_day?: number;
  currency?: string;
  status?: TransportStatus;
  from_location?: string;
  to_location?: string;
  pickup_time?: string;
  amenities?: string[];
  notes?: string;
  is_active?: boolean;
}

export interface TransportListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: Transport[];
}

export interface TransportFilters {
  transport_type?: TransportType;
  status?: TransportStatus;
  min_capacity?: number;
  is_active?: boolean;
  search?: string;
  page?: number;
  page_size?: number;
}

export const transportService = {
  /**
   * Get all transports with optional filters
   */
  getTransports: async (filters?: TransportFilters): Promise<TransportListResponse> => {
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          params.append(key, String(value));
        }
      });
    }

    const response = await apiClient.get<TransportListResponse>(
      `/api/v1/transports/?${params.toString()}`
    );
    return response.data;
  },

  /**
   * Get single transport by ID
   */
  getTransportById: async (id: number): Promise<Transport> => {
    const response = await apiClient.get<Transport>(`/api/v1/transports/${id}/`);
    return response.data;
  },

  /**
   * Create new transport
   */
  createTransport: async (data: CreateTransportData): Promise<Transport> => {
    const response = await apiClient.post<Transport>('/api/v1/transports/', data);
    return response.data;
  },

  /**
   * Update existing transport
   */
  updateTransport: async (id: number, data: UpdateTransportData): Promise<Transport> => {
    const response = await apiClient.patch<Transport>(`/api/v1/transports/${id}/`, data);
    return response.data;
  },

  /**
   * Delete transport
   */
  deleteTransport: async (id: number): Promise<void> => {
    await apiClient.delete(`/api/v1/transports/${id}/`);
  },

  /**
   * Check transport availability
   */
  checkAvailability: async (
    id: number,
    date: string,
    passengers: number
  ): Promise<any> => {
    const response = await apiClient.get(`/api/v1/transports/${id}/availability/`, {
      params: {
        date,
        passengers,
      },
    });
    return response.data;
  },

  /**
   * Calculate transport cost
   */
  calculateCost: async (
    id: number,
    distance: number,
    days: number
  ): Promise<any> => {
    const response = await apiClient.post(`/api/v1/transports/${id}/calculate-cost/`, {
      distance,
      days,
    });
    return response.data;
  },
};

export default transportService;

