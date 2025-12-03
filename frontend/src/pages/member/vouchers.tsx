import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { Badge } from '@/components/ui/badge';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog';
import { Pagination, PaginationContent, PaginationItem, PaginationLink, PaginationNext, PaginationPrevious } from '@/components/ui/pagination';
import { Textarea } from '@/components/ui/textarea';
import { Separator } from '@/components/ui/separator';
import { Receipt, Search, Filter, Eye, Check, X, Download, QrCode, User, Building, Plane, Hotel as HotelIcon, Car, MapPin } from 'lucide-react';
import { toast } from '@/hooks/use-toast';
import apiClient from '@/api/client';
import { format } from 'date-fns';

interface Voucher {
  id: number;
  voucher_code: string;
  booking_id: number;
  status: 'draft' | 'pending' | 'approved' | 'rejected';
  created_at: string;
  created_by?: {
    id: number;
    username: string;
    email: string;
  };
  booking?: {
    package_name: string;
    hotels: Array<{
      name: string;
      city: string;
      check_in: string;
      check_out: string;
      nights: number;
    }>;
    flights: Array<{
      airline: string;
      flight_number: string;
      departure: string;
      arrival: string;
      departure_time: string;
    }>;
    transports: Array<{
      vehicle_type: string;
      from_city: string;
      to_city: string;
    }>;
    mutamers: Array<{
      full_name: string;
      passport_number: string;
      visa_number: string;
      nationality: string;
      is_group_head: boolean;
    }>;
    contacts: Array<{
      city: string;
      phone: string;
      email: string;
    }>;
    instructions?: string;
  };
  qr_code?: string;
  pdf_url?: string;
  rejection_notes?: string;
}

export default function MemberVouchers() {
  const [vouchers, setVouchers] = useState<Voucher[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [selectedVoucher, setSelectedVoucher] = useState<Voucher | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [rejectDialogOpen, setRejectDialogOpen] = useState(false);
  const [rejectionNotes, setRejectionNotes] = useState('');
  const [actionLoading, setActionLoading] = useState(false);

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
      params.append('page', currentPage.toString());

      const response = await apiClient.get(`/api/v1/vouchers/vouchers/?${params.toString()}`);
      const vouchersData = Array.isArray(response.data) ? response.data : response.data.results || [];
      setVouchers(vouchersData);
      setTotalPages(Math.ceil((response.data.count || response.data.length) / 10));
    } catch (error) {
      console.error('Failed to fetch vouchers:', error);
      setVouchers([]); // Set empty array to prevent crashes
      toast({
        title: 'Error',
        description: 'Failed to fetch vouchers',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchVouchers();
  }, [currentPage, statusFilter]);

  const handleSearch = () => {
    setCurrentPage(1);
    fetchVouchers();
  };

  const handleViewVoucher = async (voucher: Voucher) => {
    try {
      const response = await apiClient.get(`/api/v1/vouchers/${voucher.id}/`);
      setSelectedVoucher(response.data);
      setDrawerOpen(true);
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to fetch voucher details',
        variant: 'destructive',
      });
    }
  };

  const handleApprove = async (voucherId: number) => {
    try {
      setActionLoading(true);
      await apiClient.patch(`/api/v1/vouchers/${voucherId}/`, {
        status: 'approved',
      });
      toast({
        title: 'Success',
        description: 'Voucher approved successfully',
      });
      fetchVouchers();
      setDrawerOpen(false);
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to approve voucher',
        variant: 'destructive',
      });
    } finally {
      setActionLoading(false);
    }
  };

  const handleRejectSubmit = async () => {
    if (!selectedVoucher) return;
    
    try {
      setActionLoading(true);
      await apiClient.patch(`/api/v1/vouchers/${selectedVoucher.id}/`, {
        status: 'rejected',
        rejection_notes: rejectionNotes,
      });
      toast({
        title: 'Voucher Rejected',
        description: 'Voucher rejected with notes',
        variant: 'destructive',
      });
      fetchVouchers();
      setRejectDialogOpen(false);
      setDrawerOpen(false);
      setRejectionNotes('');
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to reject voucher',
        variant: 'destructive',
      });
    } finally {
      setActionLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    const variants: Record<string, { variant: any; label: string }> = {
      draft: { variant: 'secondary', label: 'Draft' },
      pending: { variant: 'default', label: 'Pending' },
      approved: { variant: 'default', label: 'Approved' },
      rejected: { variant: 'destructive', label: 'Rejected' },
    };
    const config = variants[status] || variants.draft;
    return <Badge variant={config.variant} className={status === 'approved' ? 'bg-blue-500 hover:bg-blue-600' : ''}>{config.label}</Badge>;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-foreground">Voucher Management</h1>
        <p className="text-muted-foreground">View and approve travel vouchers</p>
      </div>

      {/* Filters Bar */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1 flex gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search by voucher code or agent name..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                  className="pl-10"
                />
              </div>
              <Button onClick={handleSearch} variant="secondary">
                <Search className="h-4 w-4" />
              </Button>
            </div>
            <div className="flex gap-2 items-center">
              <Filter className="h-4 w-4 text-muted-foreground" />
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="Filter by status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Vouchers</SelectItem>
                  <SelectItem value="pending">Pending</SelectItem>
                  <SelectItem value="approved">Approved</SelectItem>
                  <SelectItem value="rejected">Rejected</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Vouchers Table */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Receipt className="h-5 w-5" />
            Vouchers List
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8 text-muted-foreground">Loading vouchers...</div>
          ) : vouchers.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">No vouchers found</div>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Voucher Code</TableHead>
                    <TableHead>Booking ID</TableHead>
                    <TableHead>Created By</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Created Date</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(vouchers || []).map((voucher) => (
                    <TableRow key={voucher.id}>
                      <TableCell className="font-medium">{voucher.voucher_code}</TableCell>
                      <TableCell>#{voucher.booking_id}</TableCell>
                      <TableCell>{voucher.created_by?.username || 'N/A'}</TableCell>
                      <TableCell>{getStatusBadge(voucher.status)}</TableCell>
                      <TableCell>{format(new Date(voucher.created_at), 'MMM dd, yyyy')}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex gap-2 justify-end">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleViewVoucher(voucher)}
                          >
                            <Eye className="h-4 w-4 mr-1" />
                            View
                          </Button>
                          {voucher.status === 'pending' && (
                            <>
                              <Button
                                variant="default"
                                size="sm"
                                onClick={() => handleApprove(voucher.id)}
                                className="bg-blue-500 hover:bg-blue-600"
                              >
                                <Check className="h-4 w-4 mr-1" />
                                Approve
                              </Button>
                              <Button
                                variant="destructive"
                                size="sm"
                                onClick={() => {
                                  setSelectedVoucher(voucher);
                                  setRejectDialogOpen(true);
                                }}
                              >
                                <X className="h-4 w-4 mr-1" />
                                Reject
                              </Button>
                            </>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="mt-4">
                  <Pagination>
                    <PaginationContent>
                      <PaginationItem>
                        <PaginationPrevious
                          onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                          className={currentPage === 1 ? 'pointer-events-none opacity-50' : 'cursor-pointer'}
                        />
                      </PaginationItem>
                      {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
                        <PaginationItem key={page}>
                          <PaginationLink
                            onClick={() => setCurrentPage(page)}
                            isActive={currentPage === page}
                            className="cursor-pointer"
                          >
                            {page}
                          </PaginationLink>
                        </PaginationItem>
                      ))}
                      <PaginationItem>
                        <PaginationNext
                          onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                          className={currentPage === totalPages ? 'pointer-events-none opacity-50' : 'cursor-pointer'}
                        />
                      </PaginationItem>
                    </PaginationContent>
                  </Pagination>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* Voucher Detail Drawer */}
      <Sheet open={drawerOpen} onOpenChange={setDrawerOpen}>
        <SheetContent className="w-full sm:max-w-2xl overflow-y-auto">
          <SheetHeader>
            <SheetTitle className="flex items-center justify-between">
              <span className="flex items-center gap-2">
                <Receipt className="h-5 w-5" />
                Voucher Details
              </span>
              {selectedVoucher && getStatusBadge(selectedVoucher.status)}
            </SheetTitle>
          </SheetHeader>

          {selectedVoucher && (
            <div className="mt-6 space-y-6">
              {/* Voucher Code & QR */}
              <div className="bg-muted/50 p-4 rounded-lg space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Voucher Code</p>
                    <p className="text-xl font-bold">{selectedVoucher.voucher_code}</p>
                  </div>
                  {selectedVoucher.qr_code && (
                    <div className="bg-white p-2 rounded border">
                      <QrCode className="h-16 w-16" />
                    </div>
                  )}
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Booking ID</p>
                  <p className="font-medium">#{selectedVoucher.booking_id}</p>
                </div>
              </div>

              <Separator />

              {/* Hotels */}
              {selectedVoucher.booking?.hotels && selectedVoucher.booking.hotels.length > 0 && (
                <div>
                  <h3 className="font-semibold flex items-center gap-2 mb-3">
                    <HotelIcon className="h-4 w-4" />
                    Hotels
                  </h3>
                  <div className="space-y-2">
                    {selectedVoucher.booking.hotels.map((hotel, idx) => (
                      <div key={idx} className="bg-muted/30 p-3 rounded">
                        <p className="font-medium">{hotel.name}</p>
                        <p className="text-sm text-muted-foreground">{hotel.city}</p>
                        <p className="text-sm">
                          Check-in: {format(new Date(hotel.check_in), 'MMM dd, yyyy')} | 
                          Check-out: {format(new Date(hotel.check_out), 'MMM dd, yyyy')} 
                          ({hotel.nights} nights)
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Flights */}
              {selectedVoucher.booking?.flights && selectedVoucher.booking.flights.length > 0 && (
                <div>
                  <h3 className="font-semibold flex items-center gap-2 mb-3">
                    <Plane className="h-4 w-4" />
                    Flights
                  </h3>
                  <div className="space-y-2">
                    {selectedVoucher.booking.flights.map((flight, idx) => (
                      <div key={idx} className="bg-muted/30 p-3 rounded">
                        <p className="font-medium">{flight.airline} - {flight.flight_number}</p>
                        <p className="text-sm">{flight.departure} → {flight.arrival}</p>
                        <p className="text-sm text-muted-foreground">{flight.departure_time}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Transport */}
              {selectedVoucher.booking?.transports && selectedVoucher.booking.transports.length > 0 && (
                <div>
                  <h3 className="font-semibold flex items-center gap-2 mb-3">
                    <Car className="h-4 w-4" />
                    Transport
                  </h3>
                  <div className="space-y-2">
                    {selectedVoucher.booking.transports.map((transport, idx) => (
                      <div key={idx} className="bg-muted/30 p-3 rounded">
                        <p className="font-medium">{transport.vehicle_type}</p>
                        <p className="text-sm">{transport.from_city} → {transport.to_city}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Mutamers */}
              {selectedVoucher.booking?.mutamers && selectedVoucher.booking.mutamers.length > 0 && (
                <div>
                  <h3 className="font-semibold flex items-center gap-2 mb-3">
                    <User className="h-4 w-4" />
                    Mutamers
                  </h3>
                  <div className="space-y-2">
                    {selectedVoucher.booking.mutamers.map((mutamer, idx) => (
                      <div key={idx} className="bg-muted/30 p-3 rounded">
                        <div className="flex items-center justify-between">
                          <p className="font-medium">{mutamer.full_name}</p>
                          {mutamer.is_group_head && (
                            <Badge variant="secondary">Group Head</Badge>
                          )}
                        </div>
                        <p className="text-sm text-muted-foreground">
                          Passport: {mutamer.passport_number} | Visa: {mutamer.visa_number}
                        </p>
                        <p className="text-sm text-muted-foreground">Nationality: {mutamer.nationality}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Contacts */}
              {selectedVoucher.booking?.contacts && selectedVoucher.booking.contacts.length > 0 && (
                <div>
                  <h3 className="font-semibold flex items-center gap-2 mb-3">
                    <MapPin className="h-4 w-4" />
                    Contacts by City
                  </h3>
                  <div className="space-y-2">
                    {selectedVoucher.booking.contacts.map((contact, idx) => (
                      <div key={idx} className="bg-muted/30 p-3 rounded">
                        <p className="font-medium">{contact.city}</p>
                        <p className="text-sm">Phone: {contact.phone}</p>
                        <p className="text-sm">Email: {contact.email}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Instructions */}
              {selectedVoucher.booking?.instructions && (
                <div>
                  <h3 className="font-semibold mb-2">Special Instructions</h3>
                  <div className="bg-muted/30 p-3 rounded">
                    <p className="text-sm whitespace-pre-wrap">{selectedVoucher.booking.instructions}</p>
                  </div>
                </div>
              )}

              {/* Rejection Notes */}
              {selectedVoucher.status === 'rejected' && selectedVoucher.rejection_notes && (
                <div>
                  <h3 className="font-semibold mb-2 text-destructive">Rejection Notes</h3>
                  <div className="bg-destructive/10 p-3 rounded border border-destructive/20">
                    <p className="text-sm">{selectedVoucher.rejection_notes}</p>
                  </div>
                </div>
              )}

              <Separator />

              {/* Actions */}
              <div className="flex gap-3">
                {selectedVoucher.pdf_url && (
                  <Button variant="outline" className="flex-1" asChild>
                    <a href={selectedVoucher.pdf_url} download target="_blank" rel="noopener noreferrer">
                      <Download className="h-4 w-4 mr-2" />
                      Download PDF
                    </a>
                  </Button>
                )}
                {selectedVoucher.status === 'pending' && (
                  <>
                    <Button
                      variant="default"
                      className="flex-1 bg-blue-500 hover:bg-blue-600"
                      onClick={() => handleApprove(selectedVoucher.id)}
                      disabled={actionLoading}
                    >
                      <Check className="h-4 w-4 mr-2" />
                      Approve
                    </Button>
                    <Button
                      variant="destructive"
                      className="flex-1"
                      onClick={() => setRejectDialogOpen(true)}
                      disabled={actionLoading}
                    >
                      <X className="h-4 w-4 mr-2" />
                      Reject
                    </Button>
                  </>
                )}
              </div>
            </div>
          )}
        </SheetContent>
      </Sheet>

      {/* Rejection Dialog */}
      <AlertDialog open={rejectDialogOpen} onOpenChange={setRejectDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Reject Voucher</AlertDialogTitle>
            <AlertDialogDescription>
              Please provide a reason for rejecting this voucher. This will be visible to the agent.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <Textarea
            placeholder="Enter rejection reason..."
            value={rejectionNotes}
            onChange={(e) => setRejectionNotes(e.target.value)}
            rows={4}
          />
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setRejectionNotes('')}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleRejectSubmit}
              disabled={!rejectionNotes.trim() || actionLoading}
              className="bg-destructive hover:bg-destructive/90"
            >
              Confirm Rejection
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}