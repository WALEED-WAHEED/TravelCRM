import apiClient from '@/api/client';

export interface LedgerEntry {
  id: number;
  date: string;
  entry_type: 'income' | 'expense' | 'supplier_payment';
  description: string;
  amount: string;
  agent?: {
    id: number;
    username: string;
  };
  booking?: number;
  created_by?: {
    id: number;
    username: string;
  };
  created_at: string;
}

export interface LedgerListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: LedgerEntry[];
}

export interface LedgerSummary {
  income: string;
  expense: string;
  supplier_payments: string;
  net: string;
}

export interface LedgerFilters {
  page?: number;
  start_date?: string;
  end_date?: string;
  type?: string;
  agent?: number;
  search?: string;
}

export interface CreateLedgerEntry {
  entry_type: 'income' | 'expense' | 'supplier_payment';
  description: string;
  amount: string;
  date: string;
  booking?: number;
  agent?: number;
}

// Fetch ledger entries with filters
export const fetchLedgerEntries = async (filters: LedgerFilters = {}): Promise<LedgerListResponse> => {
  const params = new URLSearchParams();
  
  if (filters.page) params.append('page', filters.page.toString());
  if (filters.start_date) params.append('start_date', filters.start_date);
  if (filters.end_date) params.append('end_date', filters.end_date);
  if (filters.type) params.append('type', filters.type);
  if (filters.agent) params.append('agent', filters.agent.toString());
  if (filters.search) params.append('search', filters.search);

  const response = await apiClient.get(`/api/v1/ledger/ledger/?${params.toString()}`);
  return response.data;
};

// Fetch monthly summary
export const fetchMonthlySummary = async (year: number, month: number): Promise<LedgerSummary> => {
  const response = await apiClient.get(`/api/v1/ledger/ledger/summary/?year=${year}&month=${month}`);
  return response.data;
};

// Create ledger entry
export const createLedgerEntry = async (data: CreateLedgerEntry): Promise<LedgerEntry> => {
  const response = await apiClient.post('/api/v1/ledger/ledger/', data);
  return response.data;
};

// Update ledger entry
export const updateLedgerEntry = async (id: number, data: Partial<CreateLedgerEntry>): Promise<LedgerEntry> => {
  const response = await apiClient.patch(`/api/v1/ledger/ledger/${id}/`, data);
  return response.data;
};

// Delete ledger entry
export const deleteLedgerEntry = async (id: number): Promise<void> => {
  await apiClient.delete(`/api/v1/ledger/ledger/${id}/`);
};

// Export ledger data
export const exportLedger = async (format: 'csv' | 'xlsx' | 'pdf', filters: LedgerFilters = {}): Promise<Blob> => {
  const params = new URLSearchParams();
  params.append('format', format);
  
  if (filters.start_date) params.append('start_date', filters.start_date);
  if (filters.end_date) params.append('end_date', filters.end_date);
  if (filters.type) params.append('type', filters.type);
  if (filters.agent) params.append('agent', filters.agent.toString());

  const response = await apiClient.get(`/api/v1/ledger/ledger/export/?${params.toString()}`, {
    responseType: 'blob',
  });
  return response.data;
};

// Default export
const ledgerService = {
  fetchLedgerEntries,
  fetchMonthlySummary,
  createLedgerEntry,
  updateLedgerEntry,
  deleteLedgerEntry,
  exportLedger,
};

export default ledgerService;