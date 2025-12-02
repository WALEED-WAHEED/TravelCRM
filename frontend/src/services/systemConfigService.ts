import apiClient from '@/api/client';

export interface SystemConfiguration {
  id: number;
  key: string;
  value: string;
  description: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AgencyBranding {
  id: number;
  agency: {
    id: number;
    name: string;
  };
  logo?: string;
  favicon?: string;
  primary_color: string;
  secondary_color: string;
  company_name: string;
  tagline: string;
  address: string;
  phone: string;
  email: string;
  website: string;
  social_facebook: string;
  social_twitter: string;
  social_instagram: string;
  social_linkedin: string;
  booking_confirmation_template: string;
  payment_receipt_template: string;
  voucher_template: string;
  custom_fields: Record<string, any>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface EmailTemplate {
  id: number;
  name: string;
  template_type: string;
  subject: string;
  html_content: string;
  text_content: string;
  variables: string[];
  agency?: {
    id: number;
    name: string;
  };
  is_active: boolean;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export interface NotificationSettings {
  id: number;
  agency: {
    id: number;
    name: string;
  };
  email_booking_confirmation: boolean;
  email_payment_received: boolean;
  email_voucher_generated: boolean;
  email_booking_cancelled: boolean;
  email_daily_summary: boolean;
  email_weekly_report: boolean;
  sms_booking_confirmation: boolean;
  sms_payment_received: boolean;
  sms_voucher_generated: boolean;
  admin_new_booking: boolean;
  admin_payment_received: boolean;
  admin_cancellation: boolean;
  created_at: string;
  updated_at: string;
}

export interface APIKey {
  id: number;
  name: string;
  key_type: string;
  api_key_masked: string;
  endpoint_url: string;
  description: string;
  agency?: {
    id: number;
    name: string;
  };
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface SystemConfigSummary {
  total_configurations: number;
  total_agencies: number;
  agencies_with_branding: number;
  total_email_templates: number;
  total_api_keys: number;
  recent_changes: number;
}

export const systemConfigService = {
  // System Configuration
  getConfigurations: async (): Promise<SystemConfiguration[]> => {
    const response = await apiClient.get<SystemConfiguration[]>('/api/v1/system-config/configurations/');
    return response.data;
  },

  getConfigurationById: async (id: number): Promise<SystemConfiguration> => {
    const response = await apiClient.get<SystemConfiguration>(`/api/v1/system-config/configurations/${id}/`);
    return response.data;
  },

  createConfiguration: async (data: Partial<SystemConfiguration>): Promise<SystemConfiguration> => {
    const response = await apiClient.post<SystemConfiguration>('/api/v1/system-config/configurations/', data);
    return response.data;
  },

  updateConfiguration: async (id: number, data: Partial<SystemConfiguration>): Promise<SystemConfiguration> => {
    const response = await apiClient.patch<SystemConfiguration>(`/api/v1/system-config/configurations/${id}/`, data);
    return response.data;
  },

  deleteConfiguration: async (id: number): Promise<void> => {
    await apiClient.delete(`/api/v1/system-config/configurations/${id}/`);
  },

  getConfigurationsByCategory: async (): Promise<any> => {
    const response = await apiClient.get('/api/v1/system-config/configurations/by_category/');
    return response.data;
  },

  getPublicConfigurations: async (): Promise<SystemConfiguration[]> => {
    const response = await apiClient.get<SystemConfiguration[]>('/api/v1/system-config/configurations/public_configs/');
    return response.data;
  },

  // Agency Branding
  getAgencyBrandings: async (): Promise<AgencyBranding[]> => {
    const response = await apiClient.get<AgencyBranding[]>('/api/v1/system-config/agency-branding/');
    return response.data;
  },

  getAgencyBrandingById: async (id: number): Promise<AgencyBranding> => {
    const response = await apiClient.get<AgencyBranding>(`/api/v1/system-config/agency-branding/${id}/`);
    return response.data;
  },

  createAgencyBranding: async (data: Partial<AgencyBranding>): Promise<AgencyBranding> => {
    const response = await apiClient.post<AgencyBranding>('/api/v1/system-config/agency-branding/', data);
    return response.data;
  },

  updateAgencyBranding: async (id: number, data: Partial<AgencyBranding>): Promise<AgencyBranding> => {
    const response = await apiClient.patch<AgencyBranding>(`/api/v1/system-config/agency-branding/${id}/`, data);
    return response.data;
  },

  deleteAgencyBranding: async (id: number): Promise<void> => {
    await apiClient.delete(`/api/v1/system-config/agency-branding/${id}/`);
  },

  getAgencyBrandingSummary: async (): Promise<any> => {
    const response = await apiClient.get('/api/v1/system-config/agency-branding/summary/');
    return response.data;
  },

  uploadLogo: async (id: number, logoFile: File): Promise<AgencyBranding> => {
    const formData = new FormData();
    formData.append('logo', logoFile);
    
    const response = await apiClient.post<AgencyBranding>(
      `/api/v1/system-config/agency-branding/${id}/upload_logo/`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return response.data;
  },

  // Email Templates
  getEmailTemplates: async (): Promise<EmailTemplate[]> => {
    const response = await apiClient.get<EmailTemplate[]>('/api/v1/system-config/email-templates/');
    return response.data;
  },

  getEmailTemplateById: async (id: number): Promise<EmailTemplate> => {
    const response = await apiClient.get<EmailTemplate>(`/api/v1/system-config/email-templates/${id}/`);
    return response.data;
  },

  createEmailTemplate: async (data: Partial<EmailTemplate>): Promise<EmailTemplate> => {
    const response = await apiClient.post<EmailTemplate>('/api/v1/system-config/email-templates/', data);
    return response.data;
  },

  updateEmailTemplate: async (id: number, data: Partial<EmailTemplate>): Promise<EmailTemplate> => {
    const response = await apiClient.patch<EmailTemplate>(`/api/v1/system-config/email-templates/${id}/`, data);
    return response.data;
  },

  deleteEmailTemplate: async (id: number): Promise<void> => {
    await apiClient.delete(`/api/v1/system-config/email-templates/${id}/`);
  },

  getEmailTemplatesByType: async (): Promise<any> => {
    const response = await apiClient.get('/api/v1/system-config/email-templates/by_type/');
    return response.data;
  },

  previewEmailTemplate: async (id: number, sampleData: Record<string, any>): Promise<any> => {
    const response = await apiClient.post(`/api/v1/system-config/email-templates/${id}/preview/`, {
      sample_data: sampleData,
    });
    return response.data;
  },

  // Notification Settings
  getNotificationSettings: async (): Promise<NotificationSettings[]> => {
    const response = await apiClient.get<NotificationSettings[]>('/api/v1/system-config/notification-settings/');
    return response.data;
  },

  getNotificationSettingsById: async (id: number): Promise<NotificationSettings> => {
    const response = await apiClient.get<NotificationSettings>(`/api/v1/system-config/notification-settings/${id}/`);
    return response.data;
  },

  createNotificationSettings: async (data: Partial<NotificationSettings>): Promise<NotificationSettings> => {
    const response = await apiClient.post<NotificationSettings>('/api/v1/system-config/notification-settings/', data);
    return response.data;
  },

  updateNotificationSettings: async (id: number, data: Partial<NotificationSettings>): Promise<NotificationSettings> => {
    const response = await apiClient.patch<NotificationSettings>(`/api/v1/system-config/notification-settings/${id}/`, data);
    return response.data;
  },

  deleteNotificationSettings: async (id: number): Promise<void> => {
    await apiClient.delete(`/api/v1/system-config/notification-settings/${id}/`);
  },

  // API Keys
  getAPIKeys: async (): Promise<APIKey[]> => {
    const response = await apiClient.get<APIKey[]>('/api/v1/system-config/api-keys/');
    return response.data;
  },

  getAPIKeyById: async (id: number): Promise<APIKey> => {
    const response = await apiClient.get<APIKey>(`/api/v1/system-config/api-keys/${id}/`);
    return response.data;
  },

  createAPIKey: async (data: Partial<APIKey>): Promise<APIKey> => {
    const response = await apiClient.post<APIKey>('/api/v1/system-config/api-keys/', data);
    return response.data;
  },

  updateAPIKey: async (id: number, data: Partial<APIKey>): Promise<APIKey> => {
    const response = await apiClient.patch<APIKey>(`/api/v1/system-config/api-keys/${id}/`, data);
    return response.data;
  },

  deleteAPIKey: async (id: number): Promise<void> => {
    await apiClient.delete(`/api/v1/system-config/api-keys/${id}/`);
  },

  getAPIKeysByType: async (): Promise<any> => {
    const response = await apiClient.get('/api/v1/system-config/api-keys/by_type/');
    return response.data;
  },

  testAPIKeyConnection: async (id: number): Promise<any> => {
    const response = await apiClient.post(`/api/v1/system-config/api-keys/${id}/test_connection/`);
    return response.data;
  },

  // Dashboard
  getSystemConfigSummary: async (): Promise<SystemConfigSummary> => {
    const response = await apiClient.get<SystemConfigSummary>('/api/v1/system-config/dashboard/summary/');
    return response.data;
  },

  getHealthCheck: async (): Promise<any> => {
    const response = await apiClient.get('/api/v1/system-config/dashboard/health_check/');
    return response.data;
  },
};

export default systemConfigService;
