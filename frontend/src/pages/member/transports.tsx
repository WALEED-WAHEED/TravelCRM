import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog';
import { Skeleton } from '@/components/ui/skeleton';
import { useToast } from '@/hooks/use-toast';
import { Car, Plus, Search, Eye, Pencil, Trash2, Filter } from 'lucide-react';
import apiClient from '@/api/client';
import { format } from 'date-fns';

interface Transport {
  id: number;
  name: string;
  transport_type: string;
  capacity: number;
  amenities: string[];
  notes?: string;
  purchase_price?: number | string;
  sale_price?: number | string;
  is_active: boolean;
  agency_name?: string;
  created_by_name?: string;
  created_at?: string;
  updated_at?: string;
}

interface TransportFormData {
  name: string;
  transport_type: string;
  capacity: string;
  amenities: string;
  notes: string;
  purchase_price: string;
  sale_price: string;
}

const initialFormData: TransportFormData = {
  name: '',
  transport_type: '',
  capacity: '',
  amenities: '',
  notes: '',
  purchase_price: '',
  sale_price: '',
};

const vehicleTypes = [
  { value: 'bus', label: 'Bus' },
  { value: 'car', label: 'Car' },
  { value: 'van', label: 'Van' },
  { value: 'coach', label: 'Coach' },
  { value: 'train', label: 'Train' },
  { value: 'other', label: 'Other' },
];

const statusOptions = [
  { value: 'available', label: 'Available' },
  { value: 'booked', label: 'Booked' },
  { value: 'in_service', label: 'In Service' },
  { value: 'maintenance', label: 'Maintenance' },
];


export default function MemberTransports() {
  const [transports, setTransports] = useState<Transport[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState('all');
  const [filterPriceRange, setFilterPriceRange] = useState('all');
  
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isDetailSheetOpen, setIsDetailSheetOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  
  const [formData, setFormData] = useState<TransportFormData>(initialFormData);
  const [selectedTransport, setSelectedTransport] = useState<Transport | null>(null);
  const [transportToDelete, setTransportToDelete] = useState<Transport | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const { toast } = useToast();

  useEffect(() => {
    fetchTransports();
  }, []);

  const fetchTransports = async () => {
    try {
      setLoading(true);
      const response = await apiClient.get('/api/v1/transports/transports/');
      // Handle both array response and paginated response
      const transportsData = Array.isArray(response.data) ? response.data : response.data.results || [];
      setTransports(transportsData);
    } catch (error) {
      console.error('Failed to fetch transports:', error);
      toast({
        title: 'Error',
        description: 'Failed to fetch transports',
        variant: 'destructive',
      });
      setTransports([]); // Set empty array on error
    } finally {
      setLoading(false);
    }
  };

  const handleCreateTransport = async () => {
    try {
      setSubmitting(true);
      const payload = {
        name: formData.name,
        transport_type: formData.transport_type,
        capacity: parseInt(formData.capacity),
        purchase_price: formData.purchase_price ? parseFloat(formData.purchase_price) : null,
        sale_price: formData.sale_price ? parseFloat(formData.sale_price) : null,
        amenities: formData.amenities ? formData.amenities.split(',').map(a => a.trim()) : [],
        notes: formData.notes,
        is_active: true,
      };
      await apiClient.post('/api/v1/transports/transports/', payload);
      toast({
        title: 'Success',
        description: 'Transport created successfully',
      });
      setIsCreateModalOpen(false);
      setFormData(initialFormData);
      fetchTransports();
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to create transport',
        variant: 'destructive',
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleUpdateTransport = async () => {
    if (!selectedTransport) return;
    try {
      setSubmitting(true);
      const payload = {
        name: formData.name,
        transport_type: formData.transport_type,
        capacity: parseInt(formData.capacity),
        purchase_price: formData.purchase_price ? parseFloat(formData.purchase_price) : null,
        sale_price: formData.sale_price ? parseFloat(formData.sale_price) : null,
        amenities: formData.amenities ? formData.amenities.split(',').map(a => a.trim()) : [],
        notes: formData.notes,
      };
      await apiClient.patch(`/api/v1/transports/transports/${selectedTransport.id}/`, payload);
      toast({
        title: 'Success',
        description: 'Transport updated successfully',
      });
      setIsEditModalOpen(false);
      setSelectedTransport(null);
      setFormData(initialFormData);
      fetchTransports();
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to update transport',
        variant: 'destructive',
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteTransport = async () => {
    if (!transportToDelete) return;
    try {
      await apiClient.delete(`/api/v1/transports/transports/${transportToDelete.id}/`);
      toast({
        title: 'Success',
        description: 'Transport deleted successfully',
      });
      setIsDeleteDialogOpen(false);
      setTransportToDelete(null);
      fetchTransports();
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to delete transport',
        variant: 'destructive',
      });
    }
  };

  const openCreateModal = () => {
    setFormData(initialFormData);
    setIsCreateModalOpen(true);
  };

  const openEditModal = (transport: Transport) => {
    setSelectedTransport(transport);
    setFormData({
      name: transport.name,
      transport_type: transport.transport_type,
      capacity: transport.capacity.toString(),
      amenities: transport.amenities ? transport.amenities.join(', ') : '',
      notes: transport.notes || '',
      purchase_price: transport.purchase_price ? transport.purchase_price.toString() : '',
      sale_price: transport.sale_price ? transport.sale_price.toString() : '',
    });
    setIsEditModalOpen(true);
  };

  const openDetailSheet = (transport: Transport) => {
    setSelectedTransport(transport);
    setIsDetailSheetOpen(true);
  };

  const openDeleteDialog = (transport: Transport) => {
    setTransportToDelete(transport);
    setIsDeleteDialogOpen(true);
  };

  const filteredTransports = transports.filter(transport => {
    const matchesSearch = 
      transport.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      transport.transport_type.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesType = filterType === 'all' || transport.transport_type === filterType;
    
    const matchesPriceRange = (() => {
      if (filterPriceRange === 'all') return true;
      const price = transport.sale_price ? parseFloat(transport.sale_price.toString()) : 0;
      switch (filterPriceRange) {
        case 'low': return price < 100;
        case 'medium': return price >= 100 && price < 500;
        case 'high': return price >= 500;
        default: return true;
      }
    })();

    return matchesSearch && matchesType && matchesPriceRange;
  });

  const uniqueTypes = Array.from(new Set(transports.map(t => t.transport_type))).sort();

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'N/A';
    try {
      return format(new Date(dateString), 'MMM dd, yyyy HH:mm');
    } catch {
      return dateString;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Transports</h1>
          <p className="text-muted-foreground">Manage ground transportation and logistics</p>
        </div>
        <Button onClick={openCreateModal} className="gap-2">
          <Plus className="h-4 w-4" />
          Add New Transport
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Car className="h-5 w-5" />
            Transport List
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4 mb-6 flex-wrap">
            <div className="flex-1 min-w-[200px]">
              <div className="relative">
                <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search by transport name or type..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-9"
                />
              </div>
            </div>
            <Select value={filterType} onValueChange={setFilterType}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Filter by Type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                {uniqueTypes.map((type) => (
                  <SelectItem key={type} value={type}>
                    {type.charAt(0).toUpperCase() + type.slice(1)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={filterPriceRange} onValueChange={setFilterPriceRange}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Filter by Price" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Prices</SelectItem>
                <SelectItem value="low">Under $100</SelectItem>
                <SelectItem value="medium">$100 - $500</SelectItem>
                <SelectItem value="high">Over $500</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Transports Table */}
          {loading ? (
            <div className="space-y-2">
              {[...Array(5)].map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Transport Type</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead>Capacity</TableHead>
                  <TableHead>Purchase Price</TableHead>
                  <TableHead>Sale Price</TableHead>
                  <TableHead>Amenities</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredTransports.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-muted-foreground py-8">
                      No transports found
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredTransports.map((transport) => (
                    <TableRow key={transport.id}>
                      <TableCell className="font-medium">{transport.transport_type}</TableCell>
                      <TableCell>{transport.name}</TableCell>
                      <TableCell>{transport.capacity}</TableCell>
                      <TableCell>
                        {transport.purchase_price ? parseFloat(transport.purchase_price).toFixed(2) : 'N/A'}
                      </TableCell>
                      <TableCell>
                        {transport.sale_price ? parseFloat(transport.sale_price).toFixed(2) : 'N/A'}
                      </TableCell>
                      <TableCell>
                        {transport.amenities && transport.amenities.length > 0 ? (
                          <div className="flex flex-wrap gap-1">
                            {transport.amenities.slice(0, 2).map((amenity, index) => (
                              <span key={index} className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded">
                                {amenity}
                              </span>
                            ))}
                            {transport.amenities.length > 2 && (
                              <span className="text-xs text-muted-foreground">+{transport.amenities.length - 2} more</span>
                            )}
                          </div>
                        ) : (
                          'None'
                        )}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-2">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => openDetailSheet(transport)}
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => openEditModal(transport)}
                          >
                            <Pencil className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => openDeleteDialog(transport)}
                          >
                            <Trash2 className="h-4 w-4 text-destructive" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Create Modal */}
      <Dialog open={isCreateModalOpen} onOpenChange={setIsCreateModalOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Add New Transport</DialogTitle>
          </DialogHeader>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="create-transport-type">Transport Type *</Label>
              <Select
                value={formData.transport_type}
                onValueChange={(value) => setFormData({ ...formData, transport_type: value })}
              >
                <SelectTrigger id="create-transport-type">
                  <SelectValue placeholder="Select transport type" />
                </SelectTrigger>
                <SelectContent>
                  {vehicleTypes.map((type) => (
                    <SelectItem key={type.value} value={type.value}>
                      {type.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="create-name">Transport Name *</Label>
              <Input
                id="create-name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="e.g., Al Safa Transport Bus #001"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="create-capacity">Capacity *</Label>
              <Input
                id="create-capacity"
                type="number"
                value={formData.capacity}
                onChange={(e) => setFormData({ ...formData, capacity: e.target.value })}
                placeholder="Number of passengers"
              />
            </div>


            <div className="space-y-2">
              <Label htmlFor="create-purchase-price">Purchase Price</Label>
              <Input
                id="create-purchase-price"
                type="number"
                step="0.01"
                value={formData.purchase_price}
                onChange={(e) => setFormData({ ...formData, purchase_price: e.target.value })}
                placeholder="0.00"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="create-sale-price">Sale Price</Label>
              <Input
                id="create-sale-price"
                type="number"
                step="0.01"
                value={formData.sale_price}
                onChange={(e) => setFormData({ ...formData, sale_price: e.target.value })}
                placeholder="0.00"
              />
            </div>

            <div className="space-y-2 md:col-span-2">
              <Label htmlFor="create-amenities">Amenities</Label>
              <Input
                id="create-amenities"
                value={formData.amenities}
                onChange={(e) => setFormData({ ...formData, amenities: e.target.value })}
                placeholder="WiFi, AC, TV, etc. (comma-separated)"
              />
            </div>

            <div className="space-y-2 md:col-span-2">
              <Label htmlFor="create-notes">Notes</Label>
              <Textarea
                id="create-notes"
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                placeholder="Additional notes..."
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsCreateModalOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleCreateTransport} disabled={submitting}>
              {submitting ? 'Creating...' : 'Create Transport'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Modal */}
      <Dialog open={isEditModalOpen} onOpenChange={setIsEditModalOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Edit Transport</DialogTitle>
          </DialogHeader>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="edit-transport-type">Transport Type *</Label>
              <Select
                value={formData.transport_type}
                onValueChange={(value) => setFormData({ ...formData, transport_type: value })}
              >
                <SelectTrigger id="edit-transport-type">
                  <SelectValue placeholder="Select transport type" />
                </SelectTrigger>
                <SelectContent>
                  {vehicleTypes.map((type) => (
                    <SelectItem key={type.value} value={type.value}>
                      {type.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="edit-name">Transport Name *</Label>
              <Input
                id="edit-name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="e.g., Al Safa Transport Bus #001"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="edit-capacity">Capacity *</Label>
              <Input
                id="edit-capacity"
                type="number"
                value={formData.capacity}
                onChange={(e) => setFormData({ ...formData, capacity: e.target.value })}
                placeholder="Number of passengers"
              />
            </div>


            <div className="space-y-2">
              <Label htmlFor="edit-purchase-price">Purchase Price</Label>
              <Input
                id="edit-purchase-price"
                type="number"
                step="0.01"
                value={formData.purchase_price}
                onChange={(e) => setFormData({ ...formData, purchase_price: e.target.value })}
                placeholder="0.00"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="edit-sale-price">Sale Price</Label>
              <Input
                id="edit-sale-price"
                type="number"
                step="0.01"
                value={formData.sale_price}
                onChange={(e) => setFormData({ ...formData, sale_price: e.target.value })}
                placeholder="0.00"
              />
            </div>

            <div className="space-y-2 md:col-span-2">
              <Label htmlFor="edit-amenities">Amenities</Label>
              <Input
                id="edit-amenities"
                value={formData.amenities}
                onChange={(e) => setFormData({ ...formData, amenities: e.target.value })}
                placeholder="WiFi, AC, TV, etc. (comma-separated)"
              />
            </div>

            <div className="space-y-2 md:col-span-2">
              <Label htmlFor="edit-notes">Notes</Label>
              <Textarea
                id="edit-notes"
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                placeholder="Additional notes..."
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsEditModalOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleUpdateTransport} disabled={submitting}>
              {submitting ? 'Updating...' : 'Update Transport'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Detail Sheet */}
      <Sheet open={isDetailSheetOpen} onOpenChange={setIsDetailSheetOpen}>
        <SheetContent className="overflow-y-auto">
          <SheetHeader>
            <SheetTitle>Transport Details</SheetTitle>
          </SheetHeader>
          {selectedTransport && (
            <div className="space-y-6 py-6">
              <div className="space-y-4">
                <div>
                  <Label className="text-muted-foreground">Transport Type</Label>
                  <p className="text-lg font-semibold">{selectedTransport.transport_type}</p>
                </div>

                <div>
                  <Label className="text-muted-foreground">Transport Name</Label>
                  <p className="text-lg font-semibold">{selectedTransport.name}</p>
                </div>

                <div>
                  <Label className="text-muted-foreground">Capacity</Label>
                  <p className="font-medium">{selectedTransport.capacity} passengers</p>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label className="text-muted-foreground">Purchase Price</Label>
                    <p className="text-lg font-semibold text-primary">
                      {selectedTransport.purchase_price ? 
                        parseFloat(selectedTransport.purchase_price).toFixed(2) : 
                        'N/A'
                      }
                    </p>
                  </div>
                  <div>
                    <Label className="text-muted-foreground">Sale Price</Label>
                    <p className="text-lg font-semibold text-primary">
                      {selectedTransport.sale_price ? 
                        parseFloat(selectedTransport.sale_price).toFixed(2) : 
                        'N/A'
                      }
                    </p>
                  </div>
                </div>

                {selectedTransport.amenities && selectedTransport.amenities.length > 0 && (
                  <div>
                    <Label className="text-muted-foreground">Amenities</Label>
                    <div className="flex flex-wrap gap-2 mt-2">
                      {selectedTransport.amenities.map((amenity, index) => (
                        <span key={index} className="px-2 py-1 bg-blue-100 text-blue-800 text-sm rounded">
                          {amenity}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {selectedTransport.notes && (
                  <div>
                    <Label className="text-muted-foreground">Notes</Label>
                    <p className="text-sm whitespace-pre-wrap">{selectedTransport.notes}</p>
                  </div>
                )}
              </div>

              <div className="pt-4 border-t space-y-2">
                {selectedTransport.created_by && (
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Created By:</span>
                    <span className="font-medium">{selectedTransport.created_by}</span>
                  </div>
                )}
                {selectedTransport.created_at && (
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Created At:</span>
                    <span className="font-medium">{formatDate(selectedTransport.created_at)}</span>
                  </div>
                )}
                {selectedTransport.updated_at && (
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Last Updated:</span>
                    <span className="font-medium">{formatDate(selectedTransport.updated_at)}</span>
                  </div>
                )}
              </div>
            </div>
          )}
        </SheetContent>
      </Sheet>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Are you sure?</AlertDialogTitle>
            <AlertDialogDescription>
              This action cannot be undone. This will permanently delete the transport
              <strong> {transportToDelete?.name}</strong> from the system.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDeleteTransport} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

