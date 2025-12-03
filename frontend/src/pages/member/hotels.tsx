import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Hotel, Plus, Search, Eye, Pencil, Trash2, Building2, Phone, Mail } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import apiClient from '@/api/client';

interface Hotel {
  id: number;
  name: string;
  code: string;
  city: string;
  country: string;
  rating?: number;
  address: string;
  phone?: string;
  email?: string;
  description?: string;
  amenities: string[];
  sale_price: number;
  purchase_price: number;
  is_active: boolean;
  agency_name: string;
  created_by_name: string;
  room_count: number;
  primary_image: string | null;
  created_at: string;
  updated_at: string;
}

interface HotelFormData {
  name: string;
  code: string;
  address: string;
  city: string;
  country: string;
  phone: string;
  email: string;
  rating: number;
  description: string;
  amenities: string;
  sale_price: number;
  purchase_price: number;
}

const HOTEL_CATEGORIES = ['1', '2', '3', '4', '5'];

export default function MemberHotels() {
  const [hotels, setHotels] = useState<Hotel[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterCity, setFilterCity] = useState('all');
  const [filterCategory, setFilterCategory] = useState('all');
  
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isDetailSheetOpen, setIsDetailSheetOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  
  const [selectedHotel, setSelectedHotel] = useState<Hotel | null>(null);
  const [formData, setFormData] = useState<HotelFormData>({
    name: '',
    code: '',
    address: '',
    city: '',
    country: '',
    phone: '',
    email: '',
    rating: 3,
    description: '',
    amenities: '',
    sale_price: 0,
    purchase_price: 0,
  });

  const { toast } = useToast();

  useEffect(() => {
    fetchHotels();
  }, []);

  const fetchHotels = async () => {
    try {
      setLoading(true);
      const response = await apiClient.get('/api/v1/hotels/hotels/');
      // Handle both array response and paginated response
      const hotelsData = Array.isArray(response.data) ? response.data : response.data.results || [];
      setHotels(hotelsData);
    } catch (error) {
      console.error('Failed to fetch hotels:', error);
      toast({
        title: 'Error',
        description: 'Failed to load hotels',
        variant: 'destructive',
      });
      setHotels([]); // Set empty array on error
    } finally {
      setLoading(false);
    }
  };

  const handleCreateHotel = async () => {
    try {
      const payload = {
        name: formData.name.trim(),
        code: formData.code.trim() || `HTL-${Date.now()}`,
        address: formData.address.trim(),
        city: formData.city.trim(),
        country: formData.country.trim(),
        phone: formData.phone.trim() || null,
        email: formData.email.trim() || null,
        rating: formData.rating || null,
        description: formData.description.trim() || null,
        amenities: formData.amenities
          .split(',')
          .map(a => a.trim())
          .filter(a => a.length > 0),
        sale_price: formData.sale_price,
        purchase_price: formData.purchase_price,
        is_active: true,
      };
      
      await apiClient.post('/api/v1/hotels/hotels/', payload);
      toast({
        title: 'Success',
        description: 'Hotel created successfully',
      });
      setIsCreateModalOpen(false);
      resetForm();
      fetchHotels();
    } catch (error: any) {
      console.error('Failed to create hotel:', error);
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to create hotel',
        variant: 'destructive',
      });
    }
  };

  const handleUpdateHotel = async () => {
    if (!selectedHotel) return;
    
    try {
      const payload = {
        name: formData.name.trim(),
        code: formData.code.trim() || `HTL-${Date.now()}`,
        address: formData.address.trim(),
        city: formData.city.trim(),
        country: formData.country.trim(),
        phone: formData.phone.trim() || null,
        email: formData.email.trim() || null,
        rating: formData.rating || null,
        description: formData.description.trim() || null,
        amenities: formData.amenities
          .split(',')
          .map(a => a.trim())
          .filter(a => a.length > 0),
        sale_price: formData.sale_price,
        purchase_price: formData.purchase_price,
        is_active: true,
      };
      
      await apiClient.patch(`/api/v1/hotels/hotels/${selectedHotel.id}/`, payload);
      toast({
        title: 'Success',
        description: 'Hotel updated successfully',
      });
      setIsEditModalOpen(false);
      resetForm();
      fetchHotels();
    } catch (error: any) {
      console.error('Failed to update hotel:', error);
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to update hotel',
        variant: 'destructive',
      });
    }
  };

  const handleDeleteHotel = async () => {
    if (!selectedHotel) return;
    
    try {
      await apiClient.delete(`/api/v1/hotels/hotels/${selectedHotel.id}/`);
      toast({
        title: 'Success',
        description: 'Hotel deleted successfully',
      });
      setIsDeleteDialogOpen(false);
      setSelectedHotel(null);
      fetchHotels();
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to delete hotel',
        variant: 'destructive',
      });
    }
  };

  const openCreateModal = () => {
    resetForm();
    setIsCreateModalOpen(true);
  };

  const openEditModal = (hotel: Hotel) => {
    setSelectedHotel(hotel);
    setFormData({
      name: hotel.name,
      code: hotel.code,
      address: hotel.address,
      city: hotel.city,
      country: hotel.country,
      phone: hotel.phone || '',
      email: hotel.email || '',
      rating: hotel.rating || 3,
      description: hotel.description || '',
      amenities: hotel.amenities ? hotel.amenities.join(', ') : '',
      sale_price: hotel.sale_price,
      purchase_price: hotel.purchase_price,
    });
    setIsEditModalOpen(true);
  };

  const openDetailSheet = (hotel: Hotel) => {
    setSelectedHotel(hotel);
    setIsDetailSheetOpen(true);
  };

  const openDeleteDialog = (hotel: Hotel) => {
    setSelectedHotel(hotel);
    setIsDeleteDialogOpen(true);
  };

  const resetForm = () => {
    setFormData({
      name: '',
      code: '',
      address: '',
      city: '',
      country: '',
      phone: '',
      email: '',
      rating: 3,
      description: '',
      amenities: '',
      sale_price: 0,
      purchase_price: 0,
    });
    setSelectedHotel(null);
  };

  const filteredHotels = hotels.filter((hotel) => {
    const matchesSearch = hotel.name.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesCity = !filterCity || filterCity === 'all' || hotel.city === filterCity;
    const matchesCategory = !filterCategory || filterCategory === 'all' || hotel.rating?.toString() === filterCategory;
    return matchesSearch && matchesCity && matchesCategory;
  });

  const uniqueCities = Array.from(new Set(hotels.map(h => h.city))).sort();

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Hotels</h1>
          <p className="text-muted-foreground">Manage hotel partnerships and inventory</p>
        </div>
        <Button onClick={openCreateModal} className="gap-2">
          <Plus className="h-4 w-4" />
          Add New Hotel
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Hotel className="h-5 w-5" />
            Hotel List
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4 mb-6 flex-wrap">
            <div className="flex-1 min-w-[200px]">
              <div className="relative">
                <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search by hotel name..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-9"
                />
              </div>
            </div>
            <Select value={filterCity} onValueChange={setFilterCity}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Filter by City" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Cities</SelectItem>
                {uniqueCities.map((city) => (
                  <SelectItem key={city} value={city}>
                    {city}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={filterCategory} onValueChange={setFilterCategory}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Filter by Rating" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Ratings</SelectItem>
                {HOTEL_CATEGORIES.map((rating) => (
                  <SelectItem key={rating} value={rating}>
                    {rating} Star{rating !== '1' ? 's' : ''}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {loading ? (
            <div className="space-y-3">
              {[...Array(5)].map((_, i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          ) : (
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Hotel Name</TableHead>
                    <TableHead>City</TableHead>
                    <TableHead>Country</TableHead>
                    <TableHead>Sale Price</TableHead>
                    <TableHead>Purchase Price</TableHead>
                    <TableHead>Rating</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredHotels.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center text-muted-foreground">
                        No hotels found
                      </TableCell>
                    </TableRow>
                  ) : (
                    filteredHotels.map((hotel) => (
                      <TableRow key={hotel.id}>
                        <TableCell className="font-medium">{hotel.name}</TableCell>
                        <TableCell>
                          <Badge variant="outline">{hotel.city}</Badge>
                        </TableCell>
                        <TableCell>{hotel.country}</TableCell>
                        <TableCell className="font-medium">${hotel.sale_price}</TableCell>
                        <TableCell className="font-medium">${hotel.purchase_price}</TableCell>
                        <TableCell>
                          {hotel.rating ? (
                            <Badge>{hotel.rating} Star{hotel.rating > 1 ? 's' : ''}</Badge>
                          ) : (
                            <span className="text-muted-foreground">No rating</span>
                          )}
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex justify-end gap-2">
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => openDetailSheet(hotel)}
                            >
                              <Eye className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => openEditModal(hotel)}
                            >
                              <Pencil className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => openDeleteDialog(hotel)}
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
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create Hotel Modal */}
      <Dialog open={isCreateModalOpen} onOpenChange={setIsCreateModalOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Add New Hotel</DialogTitle>
            <DialogDescription>
              Enter the details of the new hotel partnership
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="name">Hotel Name *</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="Enter hotel name"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="city">City *</Label>
                <Input
                  id="city"
                  value={formData.city}
                  onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                  placeholder="Enter city"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="address">Address *</Label>
              <Input
                id="address"
                value={formData.address}
                onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                placeholder="Enter full address"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="country">Country *</Label>
              <Input
                id="country"
                value={formData.country}
                onChange={(e) => setFormData({ ...formData, country: e.target.value })}
                placeholder="Enter country"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="sale_price">Sale Price *</Label>
                <Input
                  id="sale_price"
                  type="number"
                  step="0.01"
                  value={formData.sale_price || ''}
                  onChange={(e) => setFormData({ ...formData, sale_price: parseFloat(e.target.value) || 0 })}
                  placeholder="Enter sale price"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="purchase_price">Purchase Price *</Label>
                <Input
                  id="purchase_price"
                  type="number"
                  step="0.01"
                  value={formData.purchase_price || ''}
                  onChange={(e) => setFormData({ ...formData, purchase_price: parseFloat(e.target.value) || 0 })}
                  placeholder="Enter purchase price"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="phone">Phone</Label>
              <Input
                id="phone"
                value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                placeholder="Enter phone number"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                placeholder="Enter email address"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="rating">Rating</Label>
              <Select
                value={formData.rating.toString()}
                onValueChange={(value) => setFormData({ ...formData, rating: parseInt(value) })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select rating" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="0">No rating</SelectItem>
                  {[1, 2, 3, 4, 5].map((rating) => (
                    <SelectItem key={rating} value={rating.toString()}>
                      {rating} Star{rating > 1 ? 's' : ''}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Hotel description"
                rows={3}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="amenities">Amenities (comma-separated)</Label>
              <Input
                id="amenities"
                value={formData.amenities}
                onChange={(e) => setFormData({ ...formData, amenities: e.target.value })}
                placeholder="Enter amenities separated by commas (e.g., WiFi, Pool, Gym, Restaurant)"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsCreateModalOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleCreateHotel}>Create Hotel</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Hotel Modal */}
      <Dialog open={isEditModalOpen} onOpenChange={setIsEditModalOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Edit Hotel</DialogTitle>
            <DialogDescription>
              Update the hotel details
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="edit_hotel_name">Hotel Name *</Label>
                <Input
                  id="edit_hotel_name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="Enter hotel name"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit_city">City *</Label>
                <Input
                  id="edit_city"
                  value={formData.city}
                  onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                  placeholder="Enter city"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit_address">Address *</Label>
              <Input
                id="edit_address"
                value={formData.address}
                onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                placeholder="Enter full address"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit_country">Country *</Label>
              <Input
                id="edit_country"
                value={formData.country}
                onChange={(e) => setFormData({ ...formData, country: e.target.value })}
                placeholder="Enter country"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="edit_sale_price">Sale Price *</Label>
                <Input
                  id="edit_sale_price"
                  type="number"
                  step="0.01"
                  value={formData.sale_price || ''}
                  onChange={(e) => setFormData({ ...formData, sale_price: parseFloat(e.target.value) || 0 })}
                  placeholder="Enter sale price"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit_purchase_price">Purchase Price *</Label>
                <Input
                  id="edit_purchase_price"
                  type="number"
                  step="0.01"
                  value={formData.purchase_price || ''}
                  onChange={(e) => setFormData({ ...formData, purchase_price: parseFloat(e.target.value) || 0 })}
                  placeholder="Enter purchase price"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit_phone">Phone</Label>
              <Input
                id="edit_phone"
                value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                placeholder="Enter phone number"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit_email">Email</Label>
              <Input
                id="edit_email"
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                placeholder="Enter email address"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit_rating">Rating</Label>
              <Select
                value={formData.rating.toString()}
                onValueChange={(value) => setFormData({ ...formData, rating: parseInt(value) })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select rating" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="0">No rating</SelectItem>
                  {[1, 2, 3, 4, 5].map((rating) => (
                    <SelectItem key={rating} value={rating.toString()}>
                      {rating} Star{rating > 1 ? 's' : ''}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit_description">Description</Label>
              <Textarea
                id="edit_description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Hotel description"
                rows={3}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit_amenities">Amenities (comma-separated)</Label>
              <Input
                id="edit_amenities"
                value={formData.amenities}
                onChange={(e) => setFormData({ ...formData, amenities: e.target.value })}
                placeholder="Enter amenities separated by commas (e.g., WiFi, Pool, Gym, Restaurant)"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsEditModalOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleUpdateHotel}>Save Changes</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Hotel Detail Sheet */}
      <Sheet open={isDetailSheetOpen} onOpenChange={setIsDetailSheetOpen}>
        <SheetContent className="overflow-y-auto">
          <SheetHeader>
            <SheetTitle className="flex items-center gap-2">
              <Building2 className="h-5 w-5" />
              Hotel Details
            </SheetTitle>
            <SheetDescription>
              Complete information about the hotel
            </SheetDescription>
          </SheetHeader>
          {selectedHotel && (
            <div className="mt-6 space-y-6">
              {/* Basic Information */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold text-xl">{selectedHotel.name}</h3>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">{selectedHotel.city}</Badge>
                    <Badge>{selectedHotel.rating} Star{selectedHotel.rating > 1 ? 's' : ''}</Badge>
                  </div>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-3">
                    <div>
                      <Label className="text-sm font-medium text-muted-foreground">Address</Label>
                      <p className="mt-1 text-sm">{selectedHotel.address}</p>
                    </div>
                    <div>
                      <Label className="text-sm font-medium text-muted-foreground">Location</Label>
                      <p className="mt-1 text-sm">{selectedHotel.city}, {selectedHotel.country}</p>
                    </div>
                  </div>
                  
                  <div className="space-y-3">
                    {(selectedHotel.phone || selectedHotel.email) && (
                      <div>
                        <Label className="text-sm font-medium text-muted-foreground">Contact Information</Label>
                        <div className="mt-2 space-y-2">
                          {selectedHotel.phone && (
                            <div className="flex items-center gap-2">
                              <Phone className="h-4 w-4 text-muted-foreground" />
                              <span className="text-sm">{selectedHotel.phone}</span>
                            </div>
                          )}
                          {selectedHotel.email && (
                            <div className="flex items-center gap-2">
                              <Mail className="h-4 w-4 text-muted-foreground" />
                              <span className="text-sm">{selectedHotel.email}</span>
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                    <div>
                      <Label className="text-sm font-medium text-muted-foreground">Pricing</Label>
                      <div className="mt-2 space-y-1">
                        <div className="flex justify-between">
                          <span className="text-sm text-muted-foreground">Sale Price:</span>
                          <span className="text-sm font-medium">${selectedHotel.sale_price}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-sm text-muted-foreground">Purchase Price:</span>
                          <span className="text-sm font-medium">${selectedHotel.purchase_price}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Description */}
              {selectedHotel.description && (
                <div className="pt-4 border-t">
                  <Label className="text-sm font-medium text-muted-foreground">Description</Label>
                  <p className="mt-2 text-sm leading-relaxed">{selectedHotel.description}</p>
                </div>
              )}

              {/* Amenities */}
              {selectedHotel.amenities && selectedHotel.amenities.length > 0 && (
                <div className="pt-4 border-t">
                  <Label className="text-sm font-medium text-muted-foreground">Amenities</Label>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {selectedHotel.amenities.map((amenity, index) => (
                      <Badge key={index} variant="outline" className="text-xs">
                        {amenity}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              
              {/* Audit Information */}
              <div className="pt-4 border-t">
                <h4 className="font-semibold mb-3 text-sm">Audit Information</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                  <div>
                    <Label className="text-xs text-muted-foreground">Created By</Label>
                    <p className="mt-1">{selectedHotel.created_by_name || 'N/A'}</p>
                  </div>
                  <div>
                    <Label className="text-xs text-muted-foreground">Agency</Label>
                    <p className="mt-1">{selectedHotel.agency_name || 'N/A'}</p>
                  </div>
                  <div>
                    <Label className="text-xs text-muted-foreground">Created At</Label>
                    <p className="mt-1">{new Date(selectedHotel.created_at).toLocaleString()}</p>
                  </div>
                  <div>
                    <Label className="text-xs text-muted-foreground">Last Updated</Label>
                    <p className="mt-1">{new Date(selectedHotel.updated_at).toLocaleString()}</p>
                  </div>
                </div>
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
              This action cannot be undone.               This will permanently delete the hotel
              "{selectedHotel?.name}" from your records.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDeleteHotel} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}