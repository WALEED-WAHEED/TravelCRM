import apiClient from '@/api/client';

export type VoucherStatus = 'draft' | 'pending' | 'approved' | 'rejected' | 'cancelled';

export interface Voucher {
  id: number;
  voucher_number: string;
  agent: {
    id: number;
    username: string;
    full_name: string;
  };
  mutamer: {
    id: number;
    name: string;
    passport_number: string;
  };
  status: VoucherStatus;
  total_amount: number;
  paid_amount: number;
  balance_amount: number;
  services: VoucherService[];
  created_at: string;
  updated_at: string;
  approved_by?: {
    id: number;
    username: string;
    full_name: string;
  };
  approved_at?: string;
  notes?: string;
}

export interface VoucherService {
  id: number;
  service_type: 'package' | 'hotel' | 'flight' | 'transport' | 'other';
  service_name: string;
  description: string;
  amount: number;
  quantity: number;
  total: number;
}

export interface CreateVoucherData {
  mutamer_id: number;
  services: Omit<VoucherService, 'id'>[];
  notes?: string;
  status?: VoucherStatus;
}

export interface UpdateVoucherData {
  mutamer_id?: number;
  services?: Omit<VoucherService, 'id'>[];
  status?: VoucherStatus;
  notes?: string;
}

export interface VoucherListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: Voucher[];
}

export interface VoucherFilters {
  status?: VoucherStatus;
  agent_id?: number;
  mutamer_id?: number;
  date_from?: string;
  date_to?: string;
  search?: string;
  page?: number;
  page_size?: number;
}

export const voucherService = {
  /**
   * Get all vouchers with optional filters
   */
  getVouchers: async (filters?: VoucherFilters): Promise<VoucherListResponse> => {
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          params.append(key, String(value));
        }
      });
    }

    const response = await apiClient.get<VoucherListResponse>(
      `/api/v1/vouchers/?${params.toString()}`
    );
    return response.data;
  },

  /**
   * Get single voucher by ID
   */
  getVoucherById: async (id: number): Promise<Voucher> => {
    const response = await apiClient.get<Voucher>(`/api/v1/vouchers/${id}/`);
    return response.data;
  },

  /**
   * Get public voucher by token (no auth required)
   */
  getPublicVoucher: async (token: string): Promise<Voucher> => {
    const response = await apiClient.get<Voucher>(`/api/v1/vouchers/public/${token}/`);
    return response.data;
  },

  /**
   * Create new voucher
   */
  createVoucher: async (data: CreateVoucherData): Promise<Voucher> => {
    const response = await apiClient.post<Voucher>('/api/v1/vouchers/', data);
    return response.data;
  },

  /**
   * Update existing voucher
   */
  updateVoucher: async (id: number, data: UpdateVoucherData): Promise<Voucher> => {
    const response = await apiClient.patch<Voucher>(`/api/v1/vouchers/${id}/`, data);
    return response.data;
  },

  /**
   * Delete voucher
   */
  deleteVoucher: async (id: number): Promise<void> => {
    await apiClient.delete(`/api/v1/vouchers/${id}/`);
  },

  /**
   * Approve voucher (member only)
   */
  approveVoucher: async (id: number, notes?: string): Promise<Voucher> => {
    const response = await apiClient.post<Voucher>(`/api/v1/vouchers/${id}/approve/`, {
      notes,
    });
    return response.data;
  },

  /**
   * Reject voucher (member only)
   */
  rejectVoucher: async (id: number, reason: string): Promise<Voucher> => {
    const response = await apiClient.post<Voucher>(`/api/v1/vouchers/${id}/reject/`, {
      reason,
    });
    return response.data;
  },

  /**
   * Get voucher statistics
   */
  getVoucherStats: async (): Promise<any> => {
    const response = await apiClient.get('/api/v1/vouchers/stats/');
    return response.data;
  },

  /**
   * Download voucher PDF
   */
  downloadVoucherPDF: async (id: number): Promise<Blob> => {
    const response = await apiClient.get(`/api/v1/vouchers/${id}/pdf/`, {
      responseType: 'blob',
    });
    return response.data;
  },

  /**
   * Send voucher email
   */
  sendVoucherEmail: async (id: number, email: string): Promise<void> => {
    await apiClient.post(`/api/v1/vouchers/${id}/send-email/`, { email });
  },
};

export default voucherService;

