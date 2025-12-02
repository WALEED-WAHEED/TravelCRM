import apiClient from '@/api/client';

export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: 'developer' | 'member' | 'agent';
  is_active: boolean;
  agency_id?: number;
  agency?: {
    id: number;
    name: string;
  };
  created_at?: string;
  updated_at?: string;
}

export interface CreateUserData {
  username: string;
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  role: 'developer' | 'member' | 'agent';
  agency_id?: number;
  is_active?: boolean;
}

export interface UpdateUserData {
  email?: string;
  first_name?: string;
  last_name?: string;
  role?: 'developer' | 'member' | 'agent';
  agency_id?: number;
  is_active?: boolean;
}

export interface UserListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: User[];
}

export interface UserFilters {
  role?: string;
  agency_id?: number;
  is_active?: boolean;
  search?: string;
  page?: number;
  page_size?: number;
}

export const userService = {
  /**
   * Get all users with optional filters
   */
  getUsers: async (filters?: UserFilters): Promise<UserListResponse> => {
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          params.append(key, String(value));
        }
      });
    }

    const response = await apiClient.get<UserListResponse>(
      `/api/v1/users/?${params.toString()}`
    );
    return response.data;
  },

  /**
   * Get single user by ID
   */
  getUserById: async (id: number): Promise<User> => {
    const response = await apiClient.get<User>(`/api/v1/users/${id}/`);
    return response.data;
  },

  /**
   * Create new user
   */
  createUser: async (data: CreateUserData): Promise<User> => {
    const response = await apiClient.post<User>('/api/v1/users/', data);
    return response.data;
  },

  /**
   * Update existing user
   */
  updateUser: async (id: number, data: UpdateUserData): Promise<User> => {
    const response = await apiClient.patch<User>(`/api/v1/users/${id}/`, data);
    return response.data;
  },

  /**
   * Delete user
   */
  deleteUser: async (id: number): Promise<void> => {
    await apiClient.delete(`/api/v1/users/${id}/`);
  },

  /**
   * Activate/deactivate user
   */
  toggleUserStatus: async (id: number, isActive: boolean): Promise<User> => {
    const response = await apiClient.patch<User>(`/api/v1/users/${id}/`, {
      is_active: isActive,
    });
    return response.data;
  },

  /**
   * Reset user password (admin action)
   */
  resetUserPassword: async (id: number, newPassword: string): Promise<void> => {
    await apiClient.post(`/api/v1/users/${id}/reset-password/`, {
      new_password: newPassword,
    });
  },
};

export default userService;

