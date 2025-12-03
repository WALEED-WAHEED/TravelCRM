import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from '@/hooks/use-toast';
import { CheckCircle, XCircle, Clock, FileText, Search, Filter, Eye, Check, X, User, DollarSign } from 'lucide-react';
import { format } from 'date-fns';
import apiClient from '@/api/client';

interface Voucher {
  id: number;
  voucher_number: string;
  agent: {
    id: number;
    username: string;
    email: string;
  };
  mutamer: {
    id: number;
    full_name: string;
    passport_number: string;
    nationality: string;
  };
  status: 'draft' | 'pending' | 'approved' | 'rejected' | 'cancelled';
  total_amount: number;
  paid_amount: number;
  notes: string;
  approved_by?: {
    id: number;
    username: string;
  };
  approved_at?: string;
  created_at: string;
  updated_at: string;
}

interface VoucherService {
  id: number;
  service_type: string;
  service_name: string;
  description: string;
  amount: number;
  quantity: number;
  total: number;
}

interface VoucherStats {
  total_vouchers: number;
  pending_vouchers: number;
  approved_vouchers: number;
  rejected_vouchers: number;
  total_amount: number;
  paid_amount: number;
  pending_amount: number;
  recent_vouchers: number;
}

export default function MemberApprovals() {
  const [vouchers, setVouchers] = useState<Voucher[]>([]);
  const [pendingVouchers, setPendingVouchers] = useState<Voucher[]>([]);
  const [approvedVouchers, setApprovedVouchers] = useState<Voucher[]>([]);
  const [stats, setStats] = useState<VoucherStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  
  // Modal states
  const [isViewModalOpen, setIsViewModalOpen] = useState(false);
  const [isApproveDialogOpen, setIsApproveDialogOpen] = useState(false);
  const [isRejectDialogOpen, setIsRejectDialogOpen] = useState(false);
  const [selectedVoucher, setSelectedVoucher] = useState<Voucher | null>(null);
  const [voucherServices, setVoucherServices] = useState<VoucherService[]>([]);
  const [rejectionNotes, setRejectionNotes] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);

  // Fetch all vouchers
  const fetchVouchers = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      
      if (statusFilter !== 'all') {
        params.append('status', statusFilter);
      }
      if (searchQuery) {
        params.append('search', searchQuery);
      }

      const response = await apiClient.get(`/api/v1/vouchers/vouchers/?${params.toString()}`);
      const vouchersData = Array.isArray(response.data) ? response.data : response.data.results || [];
      setVouchers(vouchersData);
    } catch (error) {
      console.error('Failed to fetch vouchers:', error);
      setVouchers([]);
      toast({
        title: 'Error',
        description: 'Failed to load vouchers',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  // Fetch pending vouchers
  const fetchPendingVouchers = async () => {
    try {
      const response = await apiClient.get('/api/v1/vouchers/vouchers/pending/');
      setPendingVouchers(response.data);
    } catch (error) {
      console.error('Failed to fetch pending vouchers:', error);
      setPendingVouchers([]);
    }
  };

  // Fetch approved vouchers
  const fetchApprovedVouchers = async () => {
    try {
      const response = await apiClient.get('/api/v1/vouchers/vouchers/approved/');
      setApprovedVouchers(response.data);
    } catch (error) {
      console.error('Failed to fetch approved vouchers:', error);
      setApprovedVouchers([]);
    }
  };

  // Fetch voucher statistics
  const fetchStats = async () => {
    try {
      const response = await apiClient.get('/api/v1/vouchers/vouchers/stats/');
      setStats(response.data);
    } catch (error) {
      console.error('Failed to load stats:', error);
    }
  };

  // Fetch voucher services
  const fetchVoucherServices = async (voucherId: number) => {
    try {
      const response = await apiClient.get(`/api/v1/vouchers/vouchers/${voucherId}/get_services/`);
      setVoucherServices(response.data);
    } catch (error) {
      console.error('Failed to fetch voucher services:', error);
      setVoucherServices([]);
    }
  };

  useEffect(() => {
    fetchVouchers();
    fetchPendingVouchers();
    fetchApprovedVouchers();
    fetchStats();
  }, [statusFilter, searchQuery]);

  // Handle approval
  const handleApprove = async () => {
    if (!selectedVoucher) return;

    try {
      setIsProcessing(true);
      await apiClient.post(`/api/v1/vouchers/vouchers/${selectedVoucher.id}/approve/`);
      toast({
        title: 'Success',
        description: 'Voucher approved successfully',
      });
      setIsApproveDialogOpen(false);
      setSelectedVoucher(null);
      fetchVouchers();
      fetchPendingVouchers();
      fetchApprovedVouchers();
      fetchStats();
    } catch (error: any) {
      console.error('Failed to approve voucher:', error);
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to approve voucher',
        variant: 'destructive',
      });
    } finally {
      setIsProcessing(false);
    }
  };

  // Handle rejection
  const handleReject = async () => {
    if (!selectedVoucher) return;

    try {
      setIsProcessing(true);
      await apiClient.post(`/api/v1/vouchers/vouchers/${selectedVoucher.id}/reject/`, {
        notes: rejectionNotes,
      });
      toast({
        title: 'Success',
        description: 'Voucher rejected successfully',
      });
      setIsRejectDialogOpen(false);
      setSelectedVoucher(null);
      setRejectionNotes('');
      fetchVouchers();
      fetchPendingVouchers();
      fetchApprovedVouchers();
      fetchStats();
    } catch (error: any) {
      console.error('Failed to reject voucher:', error);
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to reject voucher',
        variant: 'destructive',
      });
    } finally {
      setIsProcessing(false);
    }
  };

  // Open view modal
  const openViewModal = async (voucher: Voucher) => {
    setSelectedVoucher(voucher);
    await fetchVoucherServices(voucher.id);
    setIsViewModalOpen(true);
  };

  // Open approve dialog
  const openApproveDialog = (voucher: Voucher) => {
    setSelectedVoucher(voucher);
    setIsApproveDialogOpen(true);
  };

  // Open reject dialog
  const openRejectDialog = (voucher: Voucher) => {
    setSelectedVoucher(voucher);
    setIsRejectDialogOpen(true);
  };

  // Get status badge
  const getStatusBadge = (status: string) => {
    const variants = {
      draft: 'secondary',
      pending: 'default',
      approved: 'default',
      rejected: 'destructive',
      cancelled: 'outline',
    } as const;
    
    const labels = {
      draft: 'Draft',
      pending: 'Pending',
      approved: 'Approved',
      rejected: 'Rejected',
      cancelled: 'Cancelled',
    };

    return (
      <Badge variant={variants[status as keyof typeof variants] || 'default'}>
        {labels[status as keyof typeof labels] || status}
      </Badge>
    );
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Approval Management</h1>
          <p className="text-muted-foreground">Review and approve pending requests</p>
        </div>
      </div>

      {/* Summary Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Vouchers</CardTitle>
              <FileText className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.total_vouchers}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Pending Approval</CardTitle>
              <Clock className="h-4 w-4 text-yellow-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-yellow-600">{stats.pending_vouchers}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Approved</CardTitle>
              <CheckCircle className="h-4 w-4 text-green-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">{stats.approved_vouchers}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Amount</CardTitle>
              <DollarSign className="h-4 w-4 text-blue-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-blue-600">${stats.total_amount}</div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Filter className="w-5 h-5" />
            Filters
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label>Search</Label>
              <div className="relative">
                <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search vouchers..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Status</Label>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger>
                  <SelectValue placeholder="All Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="pending">Pending</SelectItem>
                  <SelectItem value="approved">Approved</SelectItem>
                  <SelectItem value="rejected">Rejected</SelectItem>
                  <SelectItem value="cancelled">Cancelled</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>&nbsp;</Label>
              <Button 
                variant="outline" 
                onClick={() => {
                  setSearchQuery('');
                  setStatusFilter('all');
                }}
                className="w-full"
              >
                Clear Filters
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Tabs for different views */}
      <Tabs defaultValue="pending" className="space-y-4">
        <TabsList>
          <TabsTrigger value="pending">Pending Approval ({pendingVouchers.length})</TabsTrigger>
          <TabsTrigger value="approved">Approved ({approvedVouchers.length})</TabsTrigger>
          <TabsTrigger value="all">All Vouchers ({vouchers.length})</TabsTrigger>
        </TabsList>

        <TabsContent value="pending">
          <Card>
            <CardHeader>
              <CardTitle>Pending Approval</CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="space-y-4">
                  {[...Array(3)].map((_, i) => (
                    <Skeleton key={i} className="h-16 w-full" />
                  ))}
                </div>
              ) : pendingVouchers.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  No pending vouchers for approval.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Voucher Number</TableHead>
                        <TableHead>Mutamer</TableHead>
                        <TableHead>Agent</TableHead>
                        <TableHead>Amount</TableHead>
                        <TableHead>Created At</TableHead>
                        <TableHead className="text-right">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {pendingVouchers.map((voucher) => (
                        <TableRow key={voucher.id}>
                          <TableCell className="font-medium">{voucher.voucher_number}</TableCell>
                          <TableCell>
                            <div>
                              <div className="font-medium">{voucher.mutamer.full_name}</div>
                              <div className="text-sm text-muted-foreground">
                                {voucher.mutamer.passport_number}
                              </div>
                            </div>
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center gap-2">
                              <User className="w-4 h-4" />
                              {voucher.agent.username}
                            </div>
                          </TableCell>
                          <TableCell className="font-medium">${voucher.total_amount}</TableCell>
                          <TableCell>{format(new Date(voucher.created_at), 'PPP')}</TableCell>
                          <TableCell className="text-right">
                            <div className="flex justify-end gap-2">
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => openViewModal(voucher)}
                              >
                                <Eye className="w-4 h-4" />
                              </Button>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => openApproveDialog(voucher)}
                                className="text-green-600 hover:text-green-700"
                              >
                                <Check className="w-4 h-4" />
                              </Button>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => openRejectDialog(voucher)}
                                className="text-red-600 hover:text-red-700"
                              >
                                <X className="w-4 h-4" />
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="approved">
          <Card>
            <CardHeader>
              <CardTitle>Approved Vouchers</CardTitle>
            </CardHeader>
            <CardContent>
              {approvedVouchers.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  No approved vouchers yet.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Voucher Number</TableHead>
                        <TableHead>Mutamer</TableHead>
                        <TableHead>Agent</TableHead>
                        <TableHead>Amount</TableHead>
                        <TableHead>Approved By</TableHead>
                        <TableHead>Approved At</TableHead>
                        <TableHead className="text-right">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {approvedVouchers.map((voucher) => (
                        <TableRow key={voucher.id}>
                          <TableCell className="font-medium">{voucher.voucher_number}</TableCell>
                          <TableCell>
                            <div>
                              <div className="font-medium">{voucher.mutamer.full_name}</div>
                              <div className="text-sm text-muted-foreground">
                                {voucher.mutamer.passport_number}
                              </div>
                            </div>
                          </TableCell>
                          <TableCell>{voucher.agent.username}</TableCell>
                          <TableCell className="font-medium">${voucher.total_amount}</TableCell>
                          <TableCell>{voucher.approved_by?.username || '-'}</TableCell>
                          <TableCell>
                            {voucher.approved_at ? format(new Date(voucher.approved_at), 'PPP') : '-'}
                          </TableCell>
                          <TableCell className="text-right">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => openViewModal(voucher)}
                            >
                              <Eye className="w-4 h-4" />
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="all">
          <Card>
            <CardHeader>
              <CardTitle>All Vouchers</CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="space-y-4">
                  {[...Array(5)].map((_, i) => (
                    <Skeleton key={i} className="h-16 w-full" />
                  ))}
                </div>
              ) : vouchers.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  No vouchers found.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Voucher Number</TableHead>
                        <TableHead>Mutamer</TableHead>
                        <TableHead>Agent</TableHead>
                        <TableHead>Amount</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Created At</TableHead>
                        <TableHead className="text-right">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {vouchers.map((voucher) => (
                        <TableRow key={voucher.id}>
                          <TableCell className="font-medium">{voucher.voucher_number}</TableCell>
                          <TableCell>
                            <div>
                              <div className="font-medium">{voucher.mutamer.full_name}</div>
                              <div className="text-sm text-muted-foreground">
                                {voucher.mutamer.passport_number}
                              </div>
                            </div>
                          </TableCell>
                          <TableCell>{voucher.agent.username}</TableCell>
                          <TableCell className="font-medium">${voucher.total_amount}</TableCell>
                          <TableCell>{getStatusBadge(voucher.status)}</TableCell>
                          <TableCell>{format(new Date(voucher.created_at), 'PPP')}</TableCell>
                          <TableCell className="text-right">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => openViewModal(voucher)}
                            >
                              <Eye className="w-4 h-4" />
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* View Voucher Modal */}
      <Dialog open={isViewModalOpen} onOpenChange={setIsViewModalOpen}>
        <DialogContent className="max-w-4xl">
          <DialogHeader>
            <DialogTitle>Voucher Details</DialogTitle>
          </DialogHeader>
          
          {selectedVoucher && (
            <div className="space-y-6">
              {/* Voucher Info */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label className="text-sm font-medium">Voucher Number</Label>
                  <p className="text-lg font-bold">{selectedVoucher.voucher_number}</p>
                </div>
                <div>
                  <Label className="text-sm font-medium">Status</Label>
                  <div className="mt-1">{getStatusBadge(selectedVoucher.status)}</div>
                </div>
                <div>
                  <Label className="text-sm font-medium">Total Amount</Label>
                  <p className="text-lg font-bold">${selectedVoucher.total_amount}</p>
                </div>
                <div>
                  <Label className="text-sm font-medium">Paid Amount</Label>
                  <p className="text-lg">${selectedVoucher.paid_amount}</p>
                </div>
              </div>

              {/* Mutamer Info */}
              <div>
                <Label className="text-sm font-medium">Mutamer Information</Label>
                <div className="mt-2 p-4 bg-muted rounded-lg">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <p className="font-medium">{selectedVoucher.mutamer.full_name}</p>
                      <p className="text-sm text-muted-foreground">
                        Passport: {selectedVoucher.mutamer.passport_number}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        Nationality: {selectedVoucher.mutamer.nationality}
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Services */}
              {voucherServices.length > 0 && (
                <div>
                  <Label className="text-sm font-medium">Services</Label>
                  <div className="mt-2 space-y-2">
                    {voucherServices.map((service) => (
                      <div key={service.id} className="p-4 bg-muted rounded-lg">
                        <div className="flex justify-between items-start">
                          <div>
                            <p className="font-medium">{service.service_name}</p>
                            <p className="text-sm text-muted-foreground">{service.service_type}</p>
                            {service.description && (
                              <p className="text-sm mt-1">{service.description}</p>
                            )}
                          </div>
                          <div className="text-right">
                            <p className="font-medium">${service.total}</p>
                            <p className="text-sm text-muted-foreground">
                              ${service.amount} × {service.quantity}
                            </p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Notes */}
              {selectedVoucher.notes && (
                <div>
                  <Label className="text-sm font-medium">Notes</Label>
                  <p className="mt-2 p-4 bg-muted rounded-lg">{selectedVoucher.notes}</p>
                </div>
              )}
            </div>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={() => setIsViewModalOpen(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Approve Confirmation Dialog */}
      <AlertDialog open={isApproveDialogOpen} onOpenChange={setIsApproveDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Approve Voucher</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to approve this voucher? This action cannot be undone.
              {selectedVoucher && (
                <div className="mt-2 p-2 bg-muted rounded">
                  <p className="font-medium">{selectedVoucher.voucher_number}</p>
                  <p className="text-sm">Amount: ${selectedVoucher.total_amount}</p>
                </div>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleApprove} disabled={isProcessing}>
              {isProcessing ? 'Approving...' : 'Approve'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Reject Confirmation Dialog */}
      <AlertDialog open={isRejectDialogOpen} onOpenChange={setIsRejectDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Reject Voucher</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to reject this voucher? Please provide a reason for rejection.
              {selectedVoucher && (
                <div className="mt-2 p-2 bg-muted rounded">
                  <p className="font-medium">{selectedVoucher.voucher_number}</p>
                  <p className="text-sm">Amount: ${selectedVoucher.total_amount}</p>
                </div>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <div className="py-4">
            <Label htmlFor="rejection-notes">Rejection Notes</Label>
            <Textarea
              id="rejection-notes"
              value={rejectionNotes}
              onChange={(e) => setRejectionNotes(e.target.value)}
              placeholder="Please provide a reason for rejection..."
              rows={3}
            />
          </div>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleReject} disabled={isProcessing || !rejectionNotes.trim()}>
              {isProcessing ? 'Rejecting...' : 'Reject'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}