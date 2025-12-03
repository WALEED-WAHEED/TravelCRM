import apiClient from '@/api/client';

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface LoginResponse {
  access: string;
  refresh: string;
}

export interface UserProfile {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: 'developer' | 'member' | 'agent';
  is_active: boolean;
  agency?: {
    id: number;
    name: string;
  };
}

export interface PasswordResetRequest {
  email: string;
}

export interface PasswordResetConfirm {
  token: string;
  password: string;
  password_confirm: string;
}

export const authService = {
  /**
   * Login user and get JWT tokens
   */
  login: async (credentials: LoginCredentials): Promise<LoginResponse> => {
    const response = await apiClient.post<LoginResponse>('/api/v1/auth/login/', credentials);
    return response.data;
  },

  /**
   * Refresh access token using refresh token
   */
  refreshToken: async (refreshToken: string): Promise<{ access: string }> => {
    const response = await apiClient.post('/api/v1/auth/refresh/', {
      refresh: refreshToken,
    });
    return response.data;
  },

  /**
   * Get current user profile
   */
  getUserProfile: async (): Promise<UserProfile> => {
    const response = await apiClient.get<UserProfile>('/api/v1/auth/user/');
    return response.data;
  },

  /**
   * Update user profile
   */
  updateProfile: async (data: Partial<UserProfile>): Promise<UserProfile> => {
    const response = await apiClient.patch<UserProfile>('/api/v1/auth/user/', data);
    return response.data;
  },

  /**
   * Request password reset
   */
  requestPasswordReset: async (data: PasswordResetRequest): Promise<void> => {
    await apiClient.post('/api/v1/auth/password/reset/', data);
  },

  /**
   * Confirm password reset
   */
  confirmPasswordReset: async (data: PasswordResetConfirm): Promise<void> => {
    await apiClient.post('/api/v1/auth/password/reset/confirm/', data);
  },

  /**
   * Change password
   */
  changePassword: async (oldPassword: string, newPassword: string): Promise<void> => {
    await apiClient.post('/api/v1/auth/password/change/', {
      old_password: oldPassword,
      new_password: newPassword,
    });
  },

  /**
   * Logout (client-side cleanup)
   */
  logout: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user_profile');
  },
};

export default authService;

