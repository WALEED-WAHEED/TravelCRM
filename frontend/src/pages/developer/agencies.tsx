import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from '@/components/ui/alert-dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Pagination, PaginationContent, PaginationItem, PaginationLink, PaginationNext, PaginationPrevious } from '@/components/ui/pagination';
import { Spinner } from '@/components/ui/spinner';
import { Building2, Plus, Search, Edit, Trash2, Upload, X, ChevronUp, ChevronDown } from 'lucide-react';
import { format } from 'date-fns';
import apiClient from '@/api/client';
import { useToast } from '@/hooks/use-toast';

interface Agency {
  id: number;
  name: string;
  contact_email: string;
  contact_phone: string;
  address: string;
  website: string;
  logo: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface AgencyForm {
  name: string;
  code: string;
  email: string;
  phone: string;
  address: string;
  city: string;
  state: string;
  country: string;
  postal_code: string;
  website: string;
  logo: File | null;
  is_active: boolean;
}

export default function DeveloperAgencies() {
  const { toast } = useToast();
  const [agencies, setAgencies] = useState<Agency[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [activeFilter, setActiveFilter] = useState<string>('all');
  const [sortBy, setSortBy] = useState<'name' | 'created_at' | 'updated_at'>('created_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editingAgency, setEditingAgency] = useState<Agency | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [logoPreview, setLogoPreview] = useState<string | null>(null);
  
  const [formData, setFormData] = useState<AgencyForm>({
    name: '',
    code: '',
    email: '',
    phone: '',
    address: '',
    city: '',
    state: '',
    country: '',
    postal_code: '',
    website: '',
    logo: null,
    is_active: true,
  });

  const fetchAgencies = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams({
        page: currentPage.toString(),
        search: searchTerm,
        ordering: sortOrder === 'desc' ? `-${sortBy}` : sortBy,
        ...(activeFilter !== 'all' && { is_active: activeFilter === 'active' ? 'true' : 'false' }),
      });

      const response = await apiClient.get(`/api/v1/agencies/?${params}`);
      setAgencies(response.data.results || response.data);
      
      if (response.data.count) {
        setTotalPages(Math.ceil(response.data.count / 10));
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to fetch agencies",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAgencies();
  }, [currentPage, searchTerm, activeFilter, sortBy, sortOrder]);

  const handleSort = (field: 'name' | 'created_at' | 'updated_at') => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortOrder('asc');
    }
    setCurrentPage(1);
  };

  const resetForm = () => {
    setFormData({
      name: '',
      code: '',
      email: '',
      phone: '',
      address: '',
      city: '',
      state: '',
      country: '',
      postal_code: '',
      website: '',
      logo: null,
      is_active: true,
    });
    setLogoPreview(null);
  };

  const handleCreateAgency = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);

    try {
      const formDataToSend = new FormData();
      formDataToSend.append('name', formData.name);
      formDataToSend.append('code', formData.code);
      formDataToSend.append('email', formData.email);
      formDataToSend.append('phone', formData.phone);
      formDataToSend.append('address', formData.address);
      formDataToSend.append('city', formData.city);
      formDataToSend.append('state', formData.state);
      formDataToSend.append('country', formData.country);
      formDataToSend.append('postal_code', formData.postal_code);
      formDataToSend.append('website', formData.website);
      formDataToSend.append('is_active', formData.is_active.toString());
      
      if (formData.logo) {
        formDataToSend.append('logo', formData.logo);
      }

      await apiClient.post('/api/v1/agencies/', formDataToSend, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      toast({
        title: "Success",
        description: "Agency created successfully",
      });

      setIsCreateModalOpen(false);
      resetForm();
      fetchAgencies();
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to create agency",
        variant: "destructive",
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleEditAgency = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingAgency) return;
    
    setSubmitting(true);

    try {
      const formDataToSend = new FormData();
      formDataToSend.append('name', formData.name);
      formDataToSend.append('code', formData.code);
      formDataToSend.append('email', formData.email);
      formDataToSend.append('phone', formData.phone);
      formDataToSend.append('address', formData.address);
      formDataToSend.append('city', formData.city);
      formDataToSend.append('state', formData.state);
      formDataToSend.append('country', formData.country);
      formDataToSend.append('postal_code', formData.postal_code);
      formDataToSend.append('website', formData.website);
      formDataToSend.append('is_active', formData.is_active.toString());
      
      if (formData.logo) {
        formDataToSend.append('logo', formData.logo);
      }

      await apiClient.put(`/api/v1/agencies/${editingAgency.id}/`, formDataToSend, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      toast({
        title: "Success",
        description: "Agency updated successfully",
      });

      setIsEditModalOpen(false);
      setEditingAgency(null);
      resetForm();
      fetchAgencies();
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to update agency",
        variant: "destructive",
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleToggleAgencyStatus = async (agency: Agency) => {
    try {
      const newStatus = !agency.is_active;
      await apiClient.patch(`/api/v1/agencies/${agency.id}/`, {
        is_active: newStatus
      });
      
      toast({
        title: "Success",
        description: `Agency ${newStatus ? 'activated' : 'deactivated'} successfully`,
      });
      
      fetchAgencies();
    } catch (error: any) {
      console.error('Toggle agency status error:', error);
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to update agency status",
        variant: "destructive",
      });
    }
  };

  const handleDeleteAgency = async (agency: Agency) => {
    try {
      const response = await apiClient.delete(`/api/v1/agencies/${agency.id}/`);
      
      // Check if it was a soft delete (deactivation)
      if (response.data?.detail?.includes('deactivated')) {
        toast({
          title: "Agency Deactivated",
          description: "Agency has been deactivated successfully",
        });
      } else {
        toast({
          title: "Success",
          description: "Agency deleted successfully",
        });
      }
      
      fetchAgencies();
    } catch (error: any) {
      console.error('Delete agency error:', error);
      
      let errorMessage = "Failed to delete agency";
      
      if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
        
        // Handle specific error cases
        if (error.response.data.related_counts) {
          const counts = error.response.data.related_counts;
          const relatedItems = Object.entries(counts)
            .map(([key, count]) => `${key}: ${count}`)
            .join(', ');
          errorMessage = `Cannot delete agency. It has associated data: ${relatedItems}`;
        }
      }
      
      toast({
        title: "Cannot Delete Agency",
        description: errorMessage,
        variant: "destructive",
      });
    }
  };

  const openEditModal = (agency: Agency) => {
    setEditingAgency(agency);
    setFormData({
      name: agency.name,
      code: agency.code,
      email: agency.email,
      phone: agency.phone,
      address: agency.address,
      city: agency.city,
      state: agency.state,
      country: agency.country,
      postal_code: agency.postal_code,
      website: agency.website,
      logo: null,
      is_active: agency.is_active,
    });
    setLogoPreview(agency.logo);
    setIsEditModalOpen(true);
  };

  const handleLogoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setFormData(prev => ({ ...prev, logo: file }));
      const reader = new FileReader();
      reader.onloadend = () => {
        setLogoPreview(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const SortButton = ({ field, children }: { field: 'name' | 'created_at' | 'updated_at'; children: React.ReactNode }) => (
    <button
      onClick={() => handleSort(field)}
      className="flex items-center gap-1 hover:text-primary transition-colors"
    >
      {children}
      {sortBy === field && (
        sortOrder === 'asc' ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />
      )}
    </button>
  );

  return (
    <div className="space-y-6 p-4 md:p-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold text-foreground">Agencies Management</h1>
          <p className="text-muted-foreground">Manage travel agencies in the system</p>
        </div>
        
        <Dialog open={isCreateModalOpen} onOpenChange={setIsCreateModalOpen}>
          <DialogTrigger asChild>
            <Button variant="gradient" className="gap-2">
              <Plus className="h-4 w-4" />
              Create Agency
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
            <form onSubmit={handleCreateAgency}>
              <DialogHeader>
                <DialogTitle>Create New Agency</DialogTitle>
                <DialogDescription>
                  Add a new travel agency to the system
                </DialogDescription>
              </DialogHeader>
              
              <div className="space-y-4 py-4 max-h-[70vh] overflow-y-auto">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="name">Agency Name *</Label>
                    <Input
                      id="name"
                      value={formData.name}
                      onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                      required
                    />
                  </div>
                  
                  <div className="space-y-2">
                    <Label htmlFor="code">Agency Code *</Label>
                    <Input
                      id="code"
                      value={formData.code}
                      onChange={(e) => setFormData(prev => ({ ...prev, code: e.target.value.toUpperCase() }))}
                      placeholder="e.g., NAHD001"
                      required
                    />
                  </div>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="email">Contact Email *</Label>
                    <Input
                      id="email"
                      type="email"
                      value={formData.email}
                      onChange={(e) => setFormData(prev => ({ ...prev, email: e.target.value }))}
                      required
                    />
                  </div>
                  
                  <div className="space-y-2">
                    <Label htmlFor="phone">Contact Phone *</Label>
                    <Input
                      id="phone"
                      value={formData.phone}
                      onChange={(e) => setFormData(prev => ({ ...prev, phone: e.target.value }))}
                      required
                    />
                  </div>
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="address">Address *</Label>
                  <Input
                    id="address"
                    value={formData.address}
                    onChange={(e) => setFormData(prev => ({ ...prev, address: e.target.value }))}
                    required
                  />
                </div>
                
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="city">City *</Label>
                    <Input
                      id="city"
                      value={formData.city}
                      onChange={(e) => setFormData(prev => ({ ...prev, city: e.target.value }))}
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="state">State/Province *</Label>
                    <Input
                      id="state"
                      value={formData.state}
                      onChange={(e) => setFormData(prev => ({ ...prev, state: e.target.value }))}
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="postal_code">Postal Code *</Label>
                    <Input
                      id="postal_code"
                      value={formData.postal_code}
                      onChange={(e) => setFormData(prev => ({ ...prev, postal_code: e.target.value }))}
                      required
                    />
                  </div>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="country">Country *</Label>
                    <Input
                      id="country"
                      value={formData.country}
                      onChange={(e) => setFormData(prev => ({ ...prev, country: e.target.value }))}
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="website">Website (Optional)</Label>
                    <Input
                      id="website"
                      type="url"
                      value={formData.website || ''}
                      onChange={(e) => setFormData(prev => ({ ...prev, website: e.target.value }))}
                      placeholder="https://example.com"
                    />
                  </div>
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="logo">Logo</Label>
                  <div className="flex items-center gap-4">
                    <Input
                      id="logo"
                      type="file"
                      accept="image/*"
                      onChange={handleLogoChange}
                      className="flex-1"
                    />
                    {logoPreview && (
                      <div className="relative">
                        <img
                          src={logoPreview}
                          alt="Logo preview"
                          className="h-12 w-12 object-cover rounded border"
                        />
                        <button
                          type="button"
                          onClick={() => {
                            setLogoPreview(null);
                            setFormData(prev => ({ ...prev, logo: null }));
                          }}
                          className="absolute -top-1 -right-1 h-4 w-4 bg-destructive text-destructive-foreground rounded-full flex items-center justify-center text-xs"
                        >
                          <X className="h-2 w-2" />
                        </button>
                      </div>
                    )}
                  </div>
                </div>
                
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="is_active"
                    checked={formData.is_active}
                    onChange={(e) => setFormData(prev => ({ ...prev, is_active: e.target.checked }))}
                    className="rounded border-gray-300"
                  />
                  <Label htmlFor="is_active">Active</Label>
                </div>
              </div>
              
              <DialogFooter>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => {
                    setIsCreateModalOpen(false);
                    resetForm();
                  }}
                >
                  Cancel
                </Button>
                <Button type="submit" disabled={submitting}>
                  {submitting && <Spinner size="sm" className="mr-2" />}
                  Create Agency
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Search and Filters */}
      <Card>
        <CardContent className="p-6">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search agencies..."
                  value={searchTerm}
                  onChange={(e) => {
                    setSearchTerm(e.target.value);
                    setCurrentPage(1);
                  }}
                  className="pl-10"
                />
              </div>
            </div>
            
            <Select value={activeFilter} onValueChange={(value) => {
              setActiveFilter(value);
              setCurrentPage(1);
            }}>
              <SelectTrigger className="w-40">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Agencies</SelectItem>
                <SelectItem value="active">Active Only</SelectItem>
                <SelectItem value="inactive">Inactive Only</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Agencies Table */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Building2 className="h-5 w-5" />
            Agencies ({agencies.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex justify-center py-8">
              <Spinner size="lg" />
            </div>
          ) : (
            <>
              <div className="rounded-md border overflow-x-auto">
                <Table className="min-w-full">
                  <TableHeader>
                    <TableRow>
                      <TableHead className="hidden md:table-cell">Logo</TableHead>
                      <TableHead>
                        <SortButton field="name">Name</SortButton>
                      </TableHead>
                      <TableHead className="hidden lg:table-cell">Contact Email</TableHead>
                      <TableHead className="hidden xl:table-cell">Phone</TableHead>
                      <TableHead className="hidden lg:table-cell">Website</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="hidden md:table-cell">
                        <SortButton field="created_at">Created</SortButton>
                      </TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {agencies.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                          No agencies found
                        </TableCell>
                      </TableRow>
                    ) : (
                      agencies.map((agency) => (
                        <TableRow key={agency.id}>
                          <TableCell className="hidden md:table-cell">
                            {agency.logo ? (
                              <img
                                src={agency.logo}
                                alt={`${agency.name} logo`}
                                className="h-8 w-8 object-cover rounded border"
                              />
                            ) : (
                              <div className="h-8 w-8 bg-muted rounded border flex items-center justify-center">
                                <Building2 className="h-4 w-4 text-muted-foreground" />
                              </div>
                            )}
                          </TableCell>
                          <TableCell className="font-medium">{agency.name}</TableCell>
                          <TableCell className="hidden lg:table-cell">{agency.email}</TableCell>
                          <TableCell className="hidden xl:table-cell">{agency.phone}</TableCell>
                          <TableCell className="hidden lg:table-cell">
                            {agency.website && (
                              <a
                                href={agency.website}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-primary hover:underline"
                              >
                                Visit
                              </a>
                            )}
                          </TableCell>
                          <TableCell>
                            <Badge variant={agency.is_active ? "default" : "secondary"}>
                              {agency.is_active ? "Active" : "Inactive"}
                            </Badge>
                          </TableCell>
                          <TableCell className="hidden md:table-cell">
                            {format(new Date(agency.created_at), 'MMM d, yyyy')}
                          </TableCell>
                          <TableCell className="text-right">
                            <div className="flex items-center justify-end gap-2">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleToggleAgencyStatus(agency)}
                                className={agency.is_active ? "text-orange-600 hover:text-orange-700" : "text-green-600 hover:text-green-700"}
                              >
                                {agency.is_active ? "Deactivate" : "Activate"}
                              </Button>
                              
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => openEditModal(agency)}
                              >
                                <Edit className="h-4 w-4" />
                              </Button>
                              
                              <AlertDialog>
                                <AlertDialogTrigger asChild>
                                  <Button variant="ghost" size="sm">
                                    <Trash2 className="h-4 w-4" />
                                  </Button>
                                </AlertDialogTrigger>
                                <AlertDialogContent>
                                  <AlertDialogHeader>
                                    <AlertDialogTitle>Delete Agency</AlertDialogTitle>
                                    <AlertDialogDescription>
                                      Are you sure you want to delete "{agency.name}"? If the agency has associated data, it will be deactivated instead of deleted. This action cannot be undone.
                                    </AlertDialogDescription>
                                  </AlertDialogHeader>
                                  <AlertDialogFooter>
                                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                                    <AlertDialogAction
                                      onClick={() => handleDeleteAgency(agency)}
                                      className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                                    >
                                      Delete
                                    </AlertDialogAction>
                                  </AlertDialogFooter>
                                </AlertDialogContent>
                              </AlertDialog>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="mt-6">
                  <Pagination>
                    <PaginationContent>
                      <PaginationItem>
                        <PaginationPrevious
                          href="#"
                          onClick={(e) => {
                            e.preventDefault();
                            if (currentPage > 1) setCurrentPage(currentPage - 1);
                          }}
                          className={currentPage <= 1 ? 'pointer-events-none opacity-50' : ''}
                        />
                      </PaginationItem>
                      
                      {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
                        <PaginationItem key={page}>
                          <PaginationLink
                            href="#"
                            onClick={(e) => {
                              e.preventDefault();
                              setCurrentPage(page);
                            }}
                            isActive={currentPage === page}
                          >
                            {page}
                          </PaginationLink>
                        </PaginationItem>
                      ))}
                      
                      <PaginationItem>
                        <PaginationNext
                          href="#"
                          onClick={(e) => {
                            e.preventDefault();
                            if (currentPage < totalPages) setCurrentPage(currentPage + 1);
                          }}
                          className={currentPage >= totalPages ? 'pointer-events-none opacity-50' : ''}
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

      {/* Edit Modal */}
      <Dialog open={isEditModalOpen} onOpenChange={setIsEditModalOpen}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <form onSubmit={handleEditAgency}>
            <DialogHeader>
              <DialogTitle>Edit Agency</DialogTitle>
              <DialogDescription>
                Update agency information
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="edit_name">Agency Name</Label>
                <Input
                  id="edit_name"
                  value={formData.name}
                  onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                  required
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="edit_code">Agency Code</Label>
                <Input
                  id="edit_code"
                  value={formData.code}
                  onChange={(e) => setFormData(prev => ({ ...prev, code: e.target.value.toUpperCase() }))}
                  placeholder="e.g., NAHD001"
                  required
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="edit_email">Contact Email</Label>
                <Input
                  id="edit_email"
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData(prev => ({ ...prev, email: e.target.value }))}
                  required
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="edit_phone">Contact Phone</Label>
                <Input
                  id="edit_phone"
                  value={formData.phone}
                  onChange={(e) => setFormData(prev => ({ ...prev, phone: e.target.value }))}
                  required
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="edit_address">Address</Label>
                <Input
                  id="edit_address"
                  value={formData.address}
                  onChange={(e) => setFormData(prev => ({ ...prev, address: e.target.value }))}
                  required
                />
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="edit_city">City</Label>
                  <Input
                    id="edit_city"
                    value={formData.city}
                    onChange={(e) => setFormData(prev => ({ ...prev, city: e.target.value }))}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="edit_state">State/Province</Label>
                  <Input
                    id="edit_state"
                    value={formData.state}
                    onChange={(e) => setFormData(prev => ({ ...prev, state: e.target.value }))}
                    required
                  />
                </div>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="edit_country">Country</Label>
                  <Input
                    id="edit_country"
                    value={formData.country}
                    onChange={(e) => setFormData(prev => ({ ...prev, country: e.target.value }))}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="edit_postal_code">Postal Code</Label>
                  <Input
                    id="edit_postal_code"
                    value={formData.postal_code}
                    onChange={(e) => setFormData(prev => ({ ...prev, postal_code: e.target.value }))}
                    required
                  />
                </div>
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="edit_website">Website</Label>
                <Input
                  id="edit_website"
                  type="url"
                  value={formData.website}
                  onChange={(e) => setFormData(prev => ({ ...prev, website: e.target.value }))}
                  placeholder="https://"
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="edit_logo">Logo</Label>
                <div className="flex items-center gap-4">
                  <Input
                    id="edit_logo"
                    type="file"
                    accept="image/*"
                    onChange={handleLogoChange}
                    className="flex-1"
                  />
                  {logoPreview && (
                    <div className="relative">
                      <img
                        src={logoPreview}
                        alt="Logo preview"
                        className="h-12 w-12 object-cover rounded border"
                      />
                      <button
                        type="button"
                        onClick={() => {
                          setLogoPreview(null);
                          setFormData(prev => ({ ...prev, logo: null }));
                        }}
                        className="absolute -top-1 -right-1 h-4 w-4 bg-destructive text-destructive-foreground rounded-full flex items-center justify-center text-xs"
                      >
                        <X className="h-2 w-2" />
                      </button>
                    </div>
                  )}
                </div>
              </div>
              
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="edit_is_active"
                  checked={formData.is_active}
                  onChange={(e) => setFormData(prev => ({ ...prev, is_active: e.target.checked }))}
                  className="rounded border-gray-300"
                />
                <Label htmlFor="edit_is_active">Active</Label>
              </div>
            </div>
            
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setIsEditModalOpen(false);
                  setEditingAgency(null);
                  resetForm();
                }}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={submitting}>
                {submitting && <Spinner size="sm" className="mr-2" />}
                Update Agency
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}