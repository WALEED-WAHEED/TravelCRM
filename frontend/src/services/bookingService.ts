import apiClient from '@/api/client';

export type BookingStatus = 'draft' | 'confirmed' | 'cancelled' | 'completed';
export type PaymentStatus = 'pending' | 'partial' | 'paid' | 'refunded';

export interface Booking {
  id: number;
  booking_number: string;
  package?: {
    id: number;
    name: string;
    code: string;
  };
  mutamer: {
    id: number;
    name: string;
    passport_number: string;
  };
  agent: {
    id: number;
    username: string;
    full_name: string;
  };
  agency: {
    id: number;
    name: string;
  };
  booking_date: string;
  travel_date: string;
  return_date?: string;
  status: BookingStatus;
  payment_status: PaymentStatus;
  total_amount: number;
  paid_amount: number;
  balance_amount: number;
  currency: string;
  services: BookingService[];
  special_requests?: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface BookingService {
  id: number;
  service_type: 'package' | 'hotel' | 'flight' | 'transport' | 'other';
  service_id?: number;
  service_name: string;
  description?: string;
  start_date: string;
  end_date?: string;
  amount: number;
  quantity: number;
  total: number;
}

export interface CreateBookingData {
  package_id?: number;
  mutamer_id: number;
  travel_date: string;
  return_date?: string;
  services: Omit<BookingService, 'id'>[];
  special_requests?: string;
  notes?: string;
  status?: BookingStatus;
}

export interface UpdateBookingData {
  package_id?: number;
  mutamer_id?: number;
  travel_date?: string;
  return_date?: string;
  services?: Omit<BookingService, 'id'>[];
  status?: BookingStatus;
  payment_status?: PaymentStatus;
  special_requests?: string;
  notes?: string;
}

export interface BookingListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: Booking[];
}

export interface BookingFilters {
  status?: BookingStatus;
  payment_status?: PaymentStatus;
  agent_id?: number;
  mutamer_id?: number;
  package_id?: number;
  date_from?: string;
  date_to?: string;
  search?: string;
  page?: number;
  page_size?: number;
}

export const bookingService = {
  /**
   * Get all bookings with optional filters
   */
  getBookings: async (filters?: BookingFilters): Promise<BookingListResponse> => {
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          params.append(key, String(value));
        }
      });
    }

    const response = await apiClient.get<BookingListResponse>(
      `/api/v1/bookings/?${params.toString()}`
    );
    return response.data;
  },

  /**
   * Get single booking by ID
   */
  getBookingById: async (id: number): Promise<Booking> => {
    const response = await apiClient.get<Booking>(`/api/v1/bookings/${id}/`);
    return response.data;
  },

  /**
   * Create new booking
   */
  createBooking: async (data: CreateBookingData): Promise<Booking> => {
    const response = await apiClient.post<Booking>('/api/v1/bookings/', data);
    return response.data;
  },

  /**
   * Update existing booking
   */
  updateBooking: async (id: number, data: UpdateBookingData): Promise<Booking> => {
    const response = await apiClient.patch<Booking>(`/api/v1/bookings/${id}/`, data);
    return response.data;
  },

  /**
   * Delete booking
   */
  deleteBooking: async (id: number): Promise<void> => {
    await apiClient.delete(`/api/v1/bookings/${id}/`);
  },

  /**
   * Cancel booking
   */
  cancelBooking: async (id: number, reason: string): Promise<Booking> => {
    const response = await apiClient.post<Booking>(`/api/v1/bookings/${id}/cancel/`, {
      reason,
    });
    return response.data;
  },

  /**
   * Confirm booking
   */
  confirmBooking: async (id: number): Promise<Booking> => {
    const response = await apiClient.post<Booking>(`/api/v1/bookings/${id}/confirm/`);
    return response.data;
  },

  /**
   * Add payment to booking
   */
  addPayment: async (
    id: number,
    amount: number,
    paymentMethod: string,
    notes?: string
  ): Promise<Booking> => {
    const response = await apiClient.post<Booking>(`/api/v1/bookings/${id}/add-payment/`, {
      amount,
      payment_method: paymentMethod,
      notes,
    });
    return response.data;
  },

  /**
   * Get booking invoice
   */
  getInvoice: async (id: number): Promise<Blob> => {
    const response = await apiClient.get(`/api/v1/bookings/${id}/invoice/`, {
      responseType: 'blob',
    });
    return response.data;
  },

  /**
   * Get booking itinerary
   */
  getItinerary: async (id: number): Promise<any> => {
    const response = await apiClient.get(`/api/v1/bookings/${id}/itinerary/`);
    return response.data;
  },

  /**
   * Send booking confirmation email
   */
  sendConfirmationEmail: async (id: number, email: string): Promise<void> => {
    await apiClient.post(`/api/v1/bookings/${id}/send-confirmation/`, { email });
  },
};

export default bookingService;

