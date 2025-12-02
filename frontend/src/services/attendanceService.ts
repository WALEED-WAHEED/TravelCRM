import apiClient from '@/api/client';

export type AttendanceStatus = 'present' | 'absent' | 'late' | 'leave';

export interface Attendance {
  id: number;
  user: {
    id: number;
    username: string;
    full_name: string;
    role: string;
  };
  date: string;
  status: AttendanceStatus;
  check_in_time?: string;
  check_out_time?: string;
  work_hours?: number;
  notes?: string;
  location?: string;
  created_at: string;
  updated_at: string;
}

export interface CreateAttendanceData {
  user_id: number;
  date: string;
  status: AttendanceStatus;
  check_in_time?: string;
  check_out_time?: string;
  notes?: string;
  location?: string;
}

export interface UpdateAttendanceData {
  status?: AttendanceStatus;
  check_in_time?: string;
  check_out_time?: string;
  notes?: string;
  location?: string;
}

export interface AttendanceListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: Attendance[];
}

export interface AttendanceFilters {
  user_id?: number;
  status?: AttendanceStatus;
  date_from?: string;
  date_to?: string;
  page?: number;
  page_size?: number;
}

export interface AttendanceSummary {
  user: {
    id: number;
    username: string;
    full_name: string;
  };
  total_days: number;
  present_days: number;
  absent_days: number;
  late_days: number;
  leave_days: number;
  total_hours: number;
  average_hours: number;
}

export const attendanceService = {
  /**
   * Get all attendance records with optional filters
   */
  getAttendance: async (filters?: AttendanceFilters): Promise<AttendanceListResponse> => {
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          params.append(key, String(value));
        }
      });
    }

    const response = await apiClient.get<AttendanceListResponse>(
      `/api/v1/attendance/?${params.toString()}`
    );
    return response.data;
  },

  /**
   * Get single attendance record by ID
   */
  getAttendanceById: async (id: number): Promise<Attendance> => {
    const response = await apiClient.get<Attendance>(`/api/v1/attendance/${id}/`);
    return response.data;
  },

  /**
   * Create new attendance record
   */
  createAttendance: async (data: CreateAttendanceData): Promise<Attendance> => {
    const response = await apiClient.post<Attendance>('/api/v1/attendance/', data);
    return response.data;
  },

  /**
   * Update existing attendance record
   */
  updateAttendance: async (id: number, data: UpdateAttendanceData): Promise<Attendance> => {
    const response = await apiClient.patch<Attendance>(`/api/v1/attendance/${id}/`, data);
    return response.data;
  },

  /**
   * Delete attendance record
   */
  deleteAttendance: async (id: number): Promise<void> => {
    await apiClient.delete(`/api/v1/attendance/${id}/`);
  },

  /**
   * Check in (mark arrival)
   */
  checkIn: async (location?: string): Promise<Attendance> => {
    const response = await apiClient.post<Attendance>('/api/v1/attendance/check-in/', {
      location,
    });
    return response.data;
  },

  /**
   * Check out (mark departure)
   */
  checkOut: async (): Promise<Attendance> => {
    const response = await apiClient.post<Attendance>('/api/v1/attendance/check-out/');
    return response.data;
  },

  /**
   * Get attendance summary for user
   */
  getAttendanceSummary: async (
    userId: number,
    dateFrom: string,
    dateTo: string
  ): Promise<AttendanceSummary> => {
    const response = await apiClient.get<AttendanceSummary>(
      `/api/v1/attendance/summary/?user_id=${userId}&date_from=${dateFrom}&date_to=${dateTo}`
    );
    return response.data;
  },

  /**
   * Get today's attendance status
   */
  getTodayAttendance: async (): Promise<Attendance | null> => {
    try {
      const response = await apiClient.get<Attendance>('/api/v1/attendance/today/');
      return response.data;
    } catch (error: any) {
      if (error.response?.status === 404) {
        return null;
      }
      throw error;
    }
  },

  /**
   * Bulk create attendance records
   */
  bulkCreateAttendance: async (records: CreateAttendanceData[]): Promise<Attendance[]> => {
    const response = await apiClient.post<Attendance[]>('/api/v1/attendance/bulk/', {
      records,
    });
    return response.data;
  },

  /**
   * Export attendance report
   */
  exportAttendance: async (filters: AttendanceFilters): Promise<Blob> => {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        params.append(key, String(value));
      }
    });

    const response = await apiClient.get(
      `/api/v1/attendance/export/?${params.toString()}`,
      {
        responseType: 'blob',
      }
    );
    return response.data;
  },
};

export default attendanceService;

