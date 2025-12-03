import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import apiClient from '@/api/client';
import { toast } from '@/hooks/use-toast';

export interface User {
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

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  
  // Actions
  login: (username: string, password: string) => Promise<boolean>;
  logout: () => void;
  refreshUser: () => Promise<void>;
  setLoading: (loading: boolean) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      isAuthenticated: false,
      isLoading: false,

      login: async (username: string, password: string) => {
        set({ isLoading: true });
        
        try {
          // Login request
          const response = await apiClient.post('/api/v1/auth/login/', {
            username,
            password,
          });

          const { access, refresh } = response.data;
          
          // Store tokens
          localStorage.setItem('access_token', access);
          localStorage.setItem('refresh_token', refresh);

          // Fetch user profile
          const profileResponse = await apiClient.get('/api/v1/auth/user/');
          const userData = profileResponse.data;

          set({
            user: userData,
            isAuthenticated: true,
            isLoading: false,
          });

          return true;
        } catch (error: any) {
          set({ isLoading: false });
          
          // Handle specific error messages
          if (error.response?.status === 401) {
            toast({
              title: "Login Failed",
              description: "Invalid username or password.",
              variant: "destructive",
            });
          } else if (error.response?.data?.detail) {
            toast({
              title: "Login Failed",
              description: error.response.data.detail,
              variant: "destructive",
            });
          } else {
            toast({
              title: "Login Failed",
              description: "An error occurred. Please try again.",
              variant: "destructive",
            });
          }
          
          return false;
        }
      },

      logout: () => {
        // Clear auth state first
        set({
          user: null,
          isAuthenticated: false,
          isLoading: false,
        });

        // Use safe logout utility
        import('@/utils/logout').then(({ safeLogout }) => {
          safeLogout();
        });
      },

      refreshUser: async () => {
        try {
          const response = await apiClient.get('/api/v1/auth/user/');
          set({ user: response.data });
        } catch (error) {
          console.error('Failed to refresh user:', error);
          get().logout();
        }
      },

      setLoading: (loading: boolean) => {
        set({ isLoading: loading });
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({ 
        user: state.user, 
        isAuthenticated: state.isAuthenticated 
      }),
    }
  )
);

// Initialize auth state from stored tokens
export const initializeAuth = async () => {
  const token = localStorage.getItem('access_token');
  const refreshToken = localStorage.getItem('refresh_token');
  
  if (token && refreshToken) {
    try {
      const response = await apiClient.get('/api/v1/auth/user/');
      useAuthStore.setState({
        user: response.data,
        isAuthenticated: true,
      });
    } catch (error) {
      // Token invalid, clear storage
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      useAuthStore.setState({
        user: null,
        isAuthenticated: false,
      });
    }
  }
};