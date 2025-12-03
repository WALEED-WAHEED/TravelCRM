import apiClient from '@/api/client';

export type RoomType = 'single' | 'double' | 'triple' | 'quad' | 'suite';

export interface Hotel {
  id: number;
  name: string;
  code: string;
  address: string;
  city: string;
  state: string;
  country: string;
  postal_code: string;
  phone: string;
  email: string;
  rating: number;
  description: string;
  amenities: string[];
  rooms: HotelRoom[];
  images: string[];
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

export interface HotelRoom {
  id: number;
  room_type: RoomType;
  price_per_night: number;
  capacity: number;
  available_rooms: number;
  amenities: string[];
}

export interface CreateHotelData {
  name: string;
  code: string;
  address: string;
  city: string;
  state: string;
  country: string;
  postal_code: string;
  phone: string;
  email: string;
  rating: number;
  description: string;
  amenities?: string[];
  is_active?: boolean;
}

export interface UpdateHotelData {
  name?: string;
  code?: string;
  address?: string;
  city?: string;
  state?: string;
  country?: string;
  postal_code?: string;
  phone?: string;
  email?: string;
  rating?: number;
  description?: string;
  amenities?: string[];
  is_active?: boolean;
}

export interface HotelListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: Hotel[];
}

export interface HotelFilters {
  city?: string;
  country?: string;
  min_rating?: number;
  is_active?: boolean;
  search?: string;
  page?: number;
  page_size?: number;
}

export const hotelService = {
  /**
   * Get all hotels with optional filters
   */
  getHotels: async (filters?: HotelFilters): Promise<HotelListResponse> => {
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          params.append(key, String(value));
        }
      });
    }

    const response = await apiClient.get<HotelListResponse>(
      `/api/v1/hotels/?${params.toString()}`
    );
    return response.data;
  },

  /**
   * Get single hotel by ID
   */
  getHotelById: async (id: number): Promise<Hotel> => {
    const response = await apiClient.get<Hotel>(`/api/v1/hotels/${id}/`);
    return response.data;
  },

  /**
   * Create new hotel
   */
  createHotel: async (data: CreateHotelData): Promise<Hotel> => {
    const response = await apiClient.post<Hotel>('/api/v1/hotels/', data);
    return response.data;
  },

  /**
   * Update existing hotel
   */
  updateHotel: async (id: number, data: UpdateHotelData): Promise<Hotel> => {
    const response = await apiClient.patch<Hotel>(`/api/v1/hotels/${id}/`, data);
    return response.data;
  },

  /**
   * Delete hotel
   */
  deleteHotel: async (id: number): Promise<void> => {
    await apiClient.delete(`/api/v1/hotels/${id}/`);
  },

  /**
   * Get hotel availability
   */
  checkAvailability: async (
    id: number,
    checkIn: string,
    checkOut: string,
    roomType?: RoomType
  ): Promise<any> => {
    const response = await apiClient.get(`/api/v1/hotels/${id}/availability/`, {
      params: {
        check_in: checkIn,
        check_out: checkOut,
        room_type: roomType,
      },
    });
    return response.data;
  },

  /**
   * Upload hotel images
   */
  uploadImages: async (id: number, files: File[]): Promise<Hotel> => {
    const formData = new FormData();
    files.forEach((file, index) => {
      formData.append(`image_${index}`, file);
    });

    const response = await apiClient.post<Hotel>(
      `/api/v1/hotels/${id}/upload-images/`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return response.data;
  },
};

export default hotelService;

