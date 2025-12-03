import apiClient from '@/api/client';

export type ContactType = 'customer' | 'supplier' | 'partner' | 'vendor' | 'other';

export interface Contact {
  id: number;
  name: string;
  contact_type: ContactType;
  company?: string;
  email: string;
  phone: string;
  alternate_phone?: string;
  address: string;
  city: string;
  state: string;
  country: string;
  postal_code: string;
  website?: string;
  notes?: string;
  is_active: boolean;
  agency: {
    id: number;
    name: string;
  };
  created_by: {
    id: number;
    username: string;
    full_name: string;
  };
  created_at: string;
  updated_at: string;
}

export interface CreateContactData {
  name: string;
  contact_type: ContactType;
  company?: string;
  email: string;
  phone: string;
  alternate_phone?: string;
  address: string;
  city: string;
  state: string;
  country: string;
  postal_code: string;
  website?: string;
  notes?: string;
}

export interface UpdateContactData {
  name?: string;
  contact_type?: ContactType;
  company?: string;
  email?: string;
  phone?: string;
  alternate_phone?: string;
  address?: string;
  city?: string;
  state?: string;
  country?: string;
  postal_code?: string;
  website?: string;
  notes?: string;
  is_active?: boolean;
}

export interface ContactListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: Contact[];
}

export interface ContactFilters {
  contact_type?: ContactType;
  is_active?: boolean;
  country?: string;
  city?: string;
  search?: string;
  page?: number;
  page_size?: number;
}

export const contactService = {
  /**
   * Get all contacts with optional filters
   */
  getContacts: async (filters?: ContactFilters): Promise<ContactListResponse> => {
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          params.append(key, String(value));
        }
      });
    }

    const response = await apiClient.get<ContactListResponse>(
      `/api/v1/contacts/?${params.toString()}`
    );
    return response.data;
  },

  /**
   * Get single contact by ID
   */
  getContactById: async (id: number): Promise<Contact> => {
    const response = await apiClient.get<Contact>(`/api/v1/contacts/${id}/`);
    return response.data;
  },

  /**
   * Create new contact
   */
  createContact: async (data: CreateContactData): Promise<Contact> => {
    const response = await apiClient.post<Contact>('/api/v1/contacts/', data);
    return response.data;
  },

  /**
   * Update existing contact
   */
  updateContact: async (id: number, data: UpdateContactData): Promise<Contact> => {
    const response = await apiClient.patch<Contact>(`/api/v1/contacts/${id}/`, data);
    return response.data;
  },

  /**
   * Delete contact
   */
  deleteContact: async (id: number): Promise<void> => {
    await apiClient.delete(`/api/v1/contacts/${id}/`);
  },

  /**
   * Import contacts from CSV
   */
  importContacts: async (file: File): Promise<any> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post('/api/v1/contacts/import/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  /**
   * Export contacts to CSV
   */
  exportContacts: async (filters?: ContactFilters): Promise<Blob> => {
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          params.append(key, String(value));
        }
      });
    }

    const response = await apiClient.get(
      `/api/v1/contacts/export/?${params.toString()}`,
      {
        responseType: 'blob',
      }
    );
    return response.data;
  },
};

export default contactService;

