import apiClient from '@/api/client';

export interface DashboardKPIs {
  pending_vouchers?: number;
  monthly_revenue?: number;
  active_agents?: number;
  total_mutamers?: number;
  total_bookings?: number;
  total_agencies?: number;
  total_users?: number;
  pending_vouchers_change?: string;
  revenue_change?: string;
  agents_change?: string;
  mutamers_change?: string;
  bookings_change?: string;
}

export interface RevenueData {
  month: string;
  revenue: number;
  bookings?: number;
}

export interface VoucherStatusData {
  status: string;
  count: number;
  percent?: number;
}

export interface ActivityItem {
  id: number;
  description: string;
  timestamp: string;
  type: string;
  user?: {
    id: number;
    username: string;
    full_name: string;
  };
}

export interface ActivityListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: ActivityItem[];
}

export const dashboardService = {
  /**
   * Get developer dashboard data
   */
  getDeveloperDashboard: async (): Promise<DashboardKPIs> => {
    const response = await apiClient.get<DashboardKPIs>('/api/v1/dashboard/developer/');
    return response.data;
  },

  /**
   * Get member dashboard data
   */
  getMemberDashboard: async (): Promise<DashboardKPIs> => {
    const response = await apiClient.get<DashboardKPIs>('/api/v1/dashboard/member/');
    return response.data;
  },

  /**
   * Get agent dashboard data
   */
  getAgentDashboard: async (): Promise<DashboardKPIs> => {
    const response = await apiClient.get<DashboardKPIs>('/api/v1/dashboard/agent/');
    return response.data;
  },

  /**
   * Get revenue analytics
   */
  getRevenueAnalytics: async (
    dateFrom?: string,
    dateTo?: string
  ): Promise<RevenueData[]> => {
    const params: any = {};
    if (dateFrom) params.date_from = dateFrom;
    if (dateTo) params.date_to = dateTo;

    const response = await apiClient.get<RevenueData[]>('/api/v1/analytics/revenue/', {
      params,
    });
    return response.data;
  },

  /**
   * Get voucher statistics
   */
  getVoucherStats: async (): Promise<VoucherStatusData[]> => {
    const response = await apiClient.get<VoucherStatusData[]>('/api/v1/vouchers/stats/');
    return response.data;
  },

  /**
   * Get booking statistics
   */
  getBookingStats: async (): Promise<any> => {
    const response = await apiClient.get('/api/v1/bookings/stats/');
    return response.data;
  },

  /**
   * Get recent activity
   */
  getRecentActivity: async (limit: number = 10): Promise<ActivityListResponse> => {
    const response = await apiClient.get<ActivityListResponse>(
      `/api/v1/activity/?limit=${limit}`
    );
    return response.data;
  },

  /**
   * Get agency performance
   */
  getAgencyPerformance: async (agencyId?: number): Promise<any> => {
    const url = agencyId
      ? `/api/v1/analytics/agency/${agencyId}/performance/`
      : '/api/v1/analytics/agency/performance/';
    
    const response = await apiClient.get(url);
    return response.data;
  },

  /**
   * Get agent performance
   */
  getAgentPerformance: async (agentId?: number): Promise<any> => {
    const url = agentId
      ? `/api/v1/analytics/agent/${agentId}/performance/`
      : '/api/v1/analytics/agent/performance/';
    
    const response = await apiClient.get(url);
    return response.data;
  },

  /**
   * Get monthly statistics
   */
  getMonthlyStats: async (year: number, month: number): Promise<any> => {
    const response = await apiClient.get('/api/v1/analytics/monthly/', {
      params: { year, month },
    });
    return response.data;
  },

  /**
   * Export dashboard data
   */
  exportDashboardData: async (role: 'developer' | 'member' | 'agent'): Promise<Blob> => {
    const response = await apiClient.get(`/api/v1/dashboard/${role}/export/`, {
      responseType: 'blob',
    });
    return response.data;
  },
};

export default dashboardService;

