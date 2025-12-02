import apiClient from '@/api/client';

export interface Agency {
  id: number;
  name: string;
  code: string;
  email: string;
  phone: string;
  address: string;
  city: string;
  state: string;
  country: string;
  postal_code: string;
  is_active: boolean;
  member_count?: number;
  agent_count?: number;
  created_at: string;
  updated_at: string;
}

export interface CreateAgencyData {
  name: string;
  code: string;
  email: string;
  phone: string;
  address: string;
  city: string;
  state: string;
  country: string;
  postal_code: string;
  is_active?: boolean;
}

export interface UpdateAgencyData {
  name?: string;
  code?: string;
  email?: string;
  phone?: string;
  address?: string;
  city?: string;
  state?: string;
  country?: string;
  postal_code?: string;
  is_active?: boolean;
}

export interface AgencyListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: Agency[];
}

export interface AgencyFilters {
  is_active?: boolean;
  search?: string;
  country?: string;
  city?: string;
  page?: number;
  page_size?: number;
}

export const agencyService = {
  /**
   * Get all agencies with optional filters
   */
  getAgencies: async (filters?: AgencyFilters): Promise<AgencyListResponse> => {
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          params.append(key, String(value));
        }
      });
    }

    const response = await apiClient.get<AgencyListResponse>(
      `/api/v1/agencies/?${params.toString()}`
    );
    return response.data;
  },

  /**
   * Get single agency by ID
   */
  getAgencyById: async (id: number): Promise<Agency> => {
    const response = await apiClient.get<Agency>(`/api/v1/agencies/${id}/`);
    return response.data;
  },

  /**
   * Create new agency
   */
  createAgency: async (data: CreateAgencyData): Promise<Agency> => {
    const response = await apiClient.post<Agency>('/api/v1/agencies/', data);
    return response.data;
  },

  /**
   * Update existing agency
   */
  updateAgency: async (id: number, data: UpdateAgencyData): Promise<Agency> => {
    const response = await apiClient.patch<Agency>(`/api/v1/agencies/${id}/`, data);
    return response.data;
  },

  /**
   * Delete agency
   */
  deleteAgency: async (id: number): Promise<void> => {
    await apiClient.delete(`/api/v1/agencies/${id}/`);
  },

  /**
   * Get agency statistics
   */
  getAgencyStats: async (id: number): Promise<any> => {
    const response = await apiClient.get(`/api/v1/agencies/${id}/stats/`);
    return response.data;
  },

  /**
   * Get agency members
   */
  getAgencyMembers: async (id: number): Promise<any[]> => {
    const response = await apiClient.get(`/api/v1/agencies/${id}/members/`);
    return response.data;
  },

  /**
   * Get agency agents
   */
  getAgencyAgents: async (id: number): Promise<any[]> => {
    const response = await apiClient.get(`/api/v1/agencies/${id}/agents/`);
    return response.data;
  },
};

export default agencyService;

