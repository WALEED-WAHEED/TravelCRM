import apiClient from '@/api/client';

export type MutamerGender = 'male' | 'female';

export interface Mutamer {
  id: number;
  name: string;
  passport_number: string;
  nationality: string;
  gender: MutamerGender;
  date_of_birth: string;
  phone: string;
  email: string;
  emergency_contact: string;
  emergency_phone: string;
  address: string;
  city: string;
  state: string;
  country: string;
  postal_code: string;
  agent: {
    id: number;
    username: string;
    full_name: string;
  };
  agency: {
    id: number;
    name: string;
  };
  photo?: string;
  passport_copy?: string;
  visa_copy?: string;
  notes?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CreateMutamerData {
  name: string;
  passport_number: string;
  nationality: string;
  gender: MutamerGender;
  date_of_birth: string;
  phone: string;
  email: string;
  emergency_contact: string;
  emergency_phone: string;
  address: string;
  city: string;
  state: string;
  country: string;
  postal_code: string;
  photo?: File | string;
  passport_copy?: File | string;
  visa_copy?: File | string;
  notes?: string;
}

export interface UpdateMutamerData {
  name?: string;
  passport_number?: string;
  nationality?: string;
  gender?: MutamerGender;
  date_of_birth?: string;
  phone?: string;
  email?: string;
  emergency_contact?: string;
  emergency_phone?: string;
  address?: string;
  city?: string;
  state?: string;
  country?: string;
  postal_code?: string;
  photo?: File | string;
  passport_copy?: File | string;
  visa_copy?: File | string;
  notes?: string;
  is_active?: boolean;
}

export interface MutamerListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: Mutamer[];
}

export interface MutamerFilters {
  agent_id?: number;
  agency_id?: number;
  nationality?: string;
  gender?: MutamerGender;
  is_active?: boolean;
  search?: string;
  page?: number;
  page_size?: number;
}

export const mutamerService = {
  /**
   * Get all mutamers with optional filters
   */
  getMutamers: async (filters?: MutamerFilters): Promise<MutamerListResponse> => {
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          params.append(key, String(value));
        }
      });
    }

    const response = await apiClient.get<MutamerListResponse>(
      `/api/v1/mutamers/?${params.toString()}`
    );
    return response.data;
  },

  /**
   * Get single mutamer by ID
   */
  getMutamerById: async (id: number): Promise<Mutamer> => {
    const response = await apiClient.get<Mutamer>(`/api/v1/mutamers/${id}/`);
    return response.data;
  },

  /**
   * Create new mutamer
   */
  createMutamer: async (data: CreateMutamerData): Promise<Mutamer> => {
    const formData = new FormData();
    
    Object.entries(data).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        if (value instanceof File) {
          formData.append(key, value);
        } else {
          formData.append(key, String(value));
        }
      }
    });

    const response = await apiClient.post<Mutamer>('/api/v1/mutamers/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  /**
   * Update existing mutamer
   */
  updateMutamer: async (id: number, data: UpdateMutamerData): Promise<Mutamer> => {
    const formData = new FormData();
    
    Object.entries(data).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        if (value instanceof File) {
          formData.append(key, value);
        } else {
          formData.append(key, String(value));
        }
      }
    });

    const response = await apiClient.patch<Mutamer>(`/api/v1/mutamers/${id}/`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  /**
   * Delete mutamer
   */
  deleteMutamer: async (id: number): Promise<void> => {
    await apiClient.delete(`/api/v1/mutamers/${id}/`);
  },

  /**
   * Get mutamer travel history
   */
  getMutamerHistory: async (id: number): Promise<any[]> => {
    const response = await apiClient.get(`/api/v1/mutamers/${id}/history/`);
    return response.data;
  },

  /**
   * Get mutamer documents
   */
  getMutamerDocuments: async (id: number): Promise<any[]> => {
    const response = await apiClient.get(`/api/v1/mutamers/${id}/documents/`);
    return response.data;
  },

  /**
   * Upload mutamer document
   */
  uploadDocument: async (id: number, file: File, documentType: string): Promise<any> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_type', documentType);

    const response = await apiClient.post(`/api/v1/mutamers/${id}/documents/`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },
};

export default mutamerService;

