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
import { Plane, Plus, Search, Eye, Pencil, Trash2, Filter } from 'lucide-react';
import apiClient from '@/api/client';

interface Flight {
  id: number;
  flight_type: string;
  airline: string;
  flight_number?: string;
  pnr_number?: string;
  departure_city: string;
  arrival_city: string;
  sale_price: number;
  purchase_price: number;
  notes?: string;
  created_by?: string;
  created_at?: string;
  updated_at?: string;
  segments?: FlightSegment[];
}

interface FlightFormData {
  flight_type: string;
  airline: string;
  flight_number: string;
  pnr_number: string;
  departure_city: string;
  arrival_city: string;
  sale_price: string;
  purchase_price: string;
  notes: string;
}

interface FlightSegment {
  segment_number: number;
  departure_city: string;
  arrival_city: string;
  departure_airport: string;
  arrival_airport: string;
  departure_country: string;
  arrival_country: string;
  flight_number: string;
  airline: string;
  notes: string;
}

const initialFormData: FlightFormData = {
  flight_type: 'one_way',
  airline: '',
  flight_number: '',
  pnr_number: '',
  departure_city: '',
  arrival_city: '',
  sale_price: '',
  purchase_price: '',
  notes: '',
};

const airlines = [
  'Emirates', 'Qatar Airways', 'Etihad Airways', 'Saudi Arabian Airlines', 
  'Gulf Air', 'Oman Air', 'Kuwait Airways', 'Royal Jordanian', 
  'EgyptAir', 'Turkish Airlines', 'Lufthansa', 'British Airways', 'Air France',
  'KLM Royal Dutch Airlines', 'Swiss International Air Lines', 'Austrian Airlines',
  'Scandinavian Airlines (SAS)', 'Finnair', 'Iberia', 'Alitalia', 'Aeroflot',
  'Air India', 'Singapore Airlines', 'Cathay Pacific', 'Japan Airlines',
  'All Nippon Airways (ANA)', 'Korean Air', 'Thai Airways', 'Malaysia Airlines',
  'Garuda Indonesia', 'Philippine Airlines', 'Vietnam Airlines', 'China Southern',
  'China Eastern', 'Air China', 'Hainan Airlines', 'Xiamen Airlines', 'Sichuan Airlines',
  'Air Canada', 'American Airlines', 'Delta Air Lines', 'United Airlines', 'Southwest Airlines',
  'JetBlue Airways', 'Alaska Airlines', 'Hawaiian Airlines', 'Virgin America',
  'Virgin Atlantic', 'Virgin Australia', 'Qantas', 'Air New Zealand', 'South African Airways',
  'Ethiopian Airlines', 'Kenya Airways', 'Royal Air Maroc', 'Tunisair', 'Air Algerie',
  'Libyan Airlines', 'Sudan Airways', 'Air Mauritius', 'Comair', 'Mango',
  'FlySafair', 'Airlink', 'CemAir', 'Others'
];

export default function MemberFlights() {
  const [flights, setFlights] = useState<Flight[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterFromCity, setFilterFromCity] = useState('all');
  const [filterToCity, setFilterToCity] = useState('all');
  
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isDetailSheetOpen, setIsDetailSheetOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  
  const [formData, setFormData] = useState<FlightFormData>(initialFormData);
  const [selectedFlight, setSelectedFlight] = useState<Flight | null>(null);
  const [flightToDelete, setFlightToDelete] = useState<Flight | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [customAirline, setCustomAirline] = useState('');
  const [segments, setSegments] = useState<FlightSegment[]>([]);

  const { toast } = useToast();

  useEffect(() => {
    fetchFlights();
  }, []);

  // Segment management functions
  const addSegment = () => {
    const newSegment: FlightSegment = {
      segment_number: segments.length + 1,
      departure_city: '',
      arrival_city: '',
      departure_airport: 'N/A',
      arrival_airport: 'N/A',
      departure_country: 'N/A',
      arrival_country: 'N/A',
      flight_number: '',
      airline: formData.airline,
      notes: '',
    };
    setSegments([...segments, newSegment]);
  };

  const removeSegment = (index: number) => {
    const updatedSegments = segments.filter((_, i) => i !== index);
    // Renumber segments
    const renumberedSegments = updatedSegments.map((segment, i) => ({
      ...segment,
      segment_number: i + 1,
    }));
    setSegments(renumberedSegments);
  };

  const updateSegment = (index: number, field: keyof FlightSegment, value: string) => {
    const updatedSegments = segments.map((segment, i) =>
      i === index ? { ...segment, [field]: value } : segment
    );
    setSegments(updatedSegments);
  };

  const fetchFlights = async () => {
    try {
      setLoading(true);
      const response = await apiClient.get('/api/v1/flights/flights/');
      // Handle both array response and paginated response
      const flightsData = Array.isArray(response.data) ? response.data : response.data.results || [];
      setFlights(flightsData);
    } catch (error) {
      console.error('Failed to fetch flights:', error);
      toast({
        title: 'Error',
        description: 'Failed to fetch flights',
        variant: 'destructive',
      });
      setFlights([]); // Set empty array on error
    } finally {
      setLoading(false);
    }
  };

  const handleCreateFlight = async () => {
    try {
      setSubmitting(true);
      
      // Validate required fields
      if (!formData.airline || (formData.airline === 'Others' && !customAirline.trim())) {
        toast({
          title: 'Error',
          description: 'Please select an airline or enter a custom airline name',
          variant: 'destructive',
        });
        return;
      }
      
      if (!formData.departure_city.trim()) {
        toast({
          title: 'Error',
          description: 'Please enter departure city',
          variant: 'destructive',
        });
        return;
      }
      
      if (!formData.arrival_city.trim()) {
        toast({
          title: 'Error',
          description: 'Please enter arrival city',
          variant: 'destructive',
        });
        return;
      }
      
      
      if (!formData.sale_price || parseFloat(formData.sale_price) <= 0) {
        toast({
          title: 'Error',
          description: 'Please enter a valid sale price',
          variant: 'destructive',
        });
        return;
      }
      
      if (!formData.purchase_price || parseFloat(formData.purchase_price) <= 0) {
        toast({
          title: 'Error',
          description: 'Please enter a valid purchase price',
          variant: 'destructive',
        });
        return;
      }
      
      // Validate multi-city flights have segments
      if (formData.flight_type === 'multi_city' && segments.length === 0) {
        toast({
          title: 'Error',
          description: 'Multi-city flights must have at least one segment',
          variant: 'destructive',
        });
        return;
      }
      
      const payload = {
        flight_type: formData.flight_type,
        airline: formData.airline === 'Others' ? customAirline : formData.airline,
        flight_number: formData.flight_number || null,
        pnr_number: formData.pnr_number || null,
        departure_city: formData.departure_city,
        arrival_city: formData.arrival_city,
        sale_price: parseFloat(formData.sale_price),
        purchase_price: parseFloat(formData.purchase_price),
        notes: formData.notes,
        segments: formData.flight_type === 'multi_city' ? segments : undefined,
      };
      
      console.log('=== Frontend Flight Creation ===');
      console.log('Form data:', formData);
      console.log('Payload being sent:', payload);
      console.log('Payload types:', Object.entries(payload).map(([k, v]) => `${k}: ${typeof v} = ${v}`));
      
      await apiClient.post('/api/v1/flights/flights/', payload);
      toast({
        title: 'Success',
        description: 'Flight created successfully',
      });
      setIsCreateModalOpen(false);
      setFormData(initialFormData);
      fetchFlights();
    } catch (error: any) {
      console.error('Flight creation error:', error);
      
      // Handle specific error messages from the backend
      let errorMessage = 'Failed to create flight. Please try again.';
      
      if (error.response?.data) {
        const errorData = error.response.data;
        
        // Handle field-specific errors
        if (errorData.flight_number) {
          errorMessage = `Flight Number: ${Array.isArray(errorData.flight_number) ? errorData.flight_number[0] : errorData.flight_number}`;
        } else if (errorData.non_field_errors) {
          errorMessage = Array.isArray(errorData.non_field_errors) ? errorData.non_field_errors[0] : errorData.non_field_errors;
        } else if (errorData.detail) {
          errorMessage = errorData.detail;
        } else if (typeof errorData === 'string') {
          errorMessage = errorData;
        }
      }
      
      toast({
        title: 'Error',
        description: errorMessage,
        variant: 'destructive',
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleUpdateFlight = async () => {
    if (!selectedFlight) return;
    try {
      setSubmitting(true);
      
      // Validate required fields
      if (!formData.airline || (formData.airline === 'Others' && !customAirline.trim())) {
        toast({
          title: 'Error',
          description: 'Please select an airline or enter a custom airline name',
          variant: 'destructive',
        });
        return;
      }
      
      if (!formData.departure_city.trim()) {
        toast({
          title: 'Error',
          description: 'Please enter departure city',
          variant: 'destructive',
        });
        return;
      }
      
      if (!formData.arrival_city.trim()) {
        toast({
          title: 'Error',
          description: 'Please enter arrival city',
          variant: 'destructive',
        });
        return;
      }
      
      
      if (!formData.sale_price || parseFloat(formData.sale_price) <= 0) {
        toast({
          title: 'Error',
          description: 'Please enter a valid sale price',
          variant: 'destructive',
        });
        return;
      }
      
      if (!formData.purchase_price || parseFloat(formData.purchase_price) <= 0) {
        toast({
          title: 'Error',
          description: 'Please enter a valid purchase price',
          variant: 'destructive',
        });
        return;
      }
      
      // Validate multi-city flights have segments
      if (formData.flight_type === 'multi_city' && segments.length === 0) {
        toast({
          title: 'Error',
          description: 'Multi-city flights must have at least one segment',
          variant: 'destructive',
        });
        return;
      }
      
      await apiClient.patch(`/api/v1/flights/flights/${selectedFlight.id}/`, {
        flight_type: formData.flight_type,
        airline: formData.airline === 'Others' ? customAirline : formData.airline,
        flight_number: formData.flight_number || null,
        pnr_number: formData.pnr_number || null,
        departure_city: formData.departure_city,
        arrival_city: formData.arrival_city,
        sale_price: parseFloat(formData.sale_price),
        purchase_price: parseFloat(formData.purchase_price),
        notes: formData.notes,
        segments: formData.flight_type === 'multi_city' ? segments : undefined,
      });
      toast({
        title: 'Success',
        description: 'Flight updated successfully',
      });
      setIsEditModalOpen(false);
      setSelectedFlight(null);
      setFormData(initialFormData);
      fetchFlights();
    } catch (error: any) {
      console.error('Flight update error:', error);
      
      // Handle specific error messages from the backend
      let errorMessage = 'Failed to update flight. Please try again.';
      
      if (error.response?.data) {
        const errorData = error.response.data;
        
        // Handle field-specific errors
        if (errorData.flight_number) {
          errorMessage = `Flight Number: ${Array.isArray(errorData.flight_number) ? errorData.flight_number[0] : errorData.flight_number}`;
        } else if (errorData.non_field_errors) {
          errorMessage = Array.isArray(errorData.non_field_errors) ? errorData.non_field_errors[0] : errorData.non_field_errors;
        } else if (errorData.detail) {
          errorMessage = errorData.detail;
        } else if (typeof errorData === 'string') {
          errorMessage = errorData;
        }
      }
      
      toast({
        title: 'Error',
        description: errorMessage,
        variant: 'destructive',
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteFlight = async () => {
    if (!flightToDelete) return;
    try {
      await apiClient.delete(`/api/v1/flights/flights/${flightToDelete.id}/`);
      toast({
        title: 'Success',
        description: 'Flight deleted successfully',
      });
      setIsDeleteDialogOpen(false);
      setFlightToDelete(null);
      fetchFlights();
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to delete flight',
        variant: 'destructive',
      });
    }
  };

  const openCreateModal = () => {
    setFormData(initialFormData);
    setCustomAirline('');
    setSegments([]);
    setIsCreateModalOpen(true);
  };


  const openEditModal = (flight: Flight) => {
    setSelectedFlight(flight);
    
    // Check if airline is in the predefined list
    const isPredefinedAirline = airlines.includes(flight.airline);
    
    setFormData({
      flight_type: flight.flight_type || 'one_way',
      airline: isPredefinedAirline ? flight.airline : 'Others',
      flight_number: flight.flight_number || '',
      pnr_number: flight.pnr_number || '',
      departure_city: flight.departure_city,
      arrival_city: flight.arrival_city,
      sale_price: flight.sale_price.toString(),
      purchase_price: flight.purchase_price.toString(),
      notes: flight.notes || '',
    });
    
    // Set custom airline if it's not in the predefined list
    setCustomAirline(isPredefinedAirline ? '' : flight.airline);
    
    // Load segments for multi-city flights
    if (flight.flight_type === 'multi_city' && flight.segments) {
      setSegments(flight.segments);
    } else {
      setSegments([]);
    }
    
    setIsEditModalOpen(true);
  };

  const openDetailSheet = (flight: Flight) => {
    setSelectedFlight(flight);
    setIsDetailSheetOpen(true);
  };

  const openDeleteDialog = (flight: Flight) => {
    setFlightToDelete(flight);
    setIsDeleteDialogOpen(true);
  };

  const filteredFlights = flights.filter(flight => {
    const matchesSearch = 
      flight.airline.toLowerCase().includes(searchTerm.toLowerCase()) ||
      flight.flight_number.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesFromCity = filterFromCity === 'all' || flight.departure_city === filterFromCity;
    const matchesToCity = filterToCity === 'all' || flight.arrival_city === filterToCity;

    return matchesSearch && matchesFromCity && matchesToCity;
  });

  const uniqueFromCities = Array.from(new Set(flights.map(f => f.departure_city))).sort();
  const uniqueToCities = Array.from(new Set(flights.map(f => f.arrival_city))).sort();


  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Flights</h1>
          <p className="text-muted-foreground">Manage flight schedules and inventory</p>
        </div>
        <Button onClick={openCreateModal} className="gap-2">
          <Plus className="h-4 w-4" />
          Add New Flight
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Plane className="h-5 w-5" />
            Flight List
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4 mb-6 flex-wrap">
            <div className="flex-1 min-w-[200px]">
              <div className="relative">
                <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search by airline or flight number..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-9"
                />
              </div>
            </div>
            <Select value={filterFromCity} onValueChange={setFilterFromCity}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="From City" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Departure Cities</SelectItem>
                {uniqueFromCities.map((city) => (
                  <SelectItem key={city} value={city}>
                    {city}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={filterToCity} onValueChange={setFilterToCity}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="To City" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Arrival Cities</SelectItem>
                {uniqueToCities.map((city) => (
                  <SelectItem key={city} value={city}>
                    {city}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Flights Table */}
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
                  <TableHead>Type</TableHead>
                  <TableHead>Airline</TableHead>
                  <TableHead>Flight Number</TableHead>
                  <TableHead>Route</TableHead>
                  <TableHead>Sale Price</TableHead>
                  <TableHead>Purchase Price</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredFlights.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-muted-foreground py-8">
                      No flights found
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredFlights.map((flight) => (
                    <TableRow key={flight.id}>
                      <TableCell>
                        <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                          flight.flight_type === 'one_way' ? 'bg-blue-100 text-blue-800' :
                          flight.flight_type === 'return' ? 'bg-green-100 text-green-800' :
                          'bg-purple-100 text-purple-800'
                        }`}>
                          {flight.flight_type === 'one_way' ? 'One Way' :
                           flight.flight_type === 'return' ? 'Return' : 'Multi-City'}
                        </span>
                      </TableCell>
                      <TableCell className="font-medium">{flight.airline}</TableCell>
                      <TableCell>{flight.flight_number || 'N/A'}</TableCell>
                      <TableCell>
                        <span className="font-medium">{flight.departure_city} → {flight.arrival_city}</span>
                      </TableCell>
                      <TableCell>${Number(flight.sale_price || 0).toFixed(2)}</TableCell>
                      <TableCell>${Number(flight.purchase_price || 0).toFixed(2)}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-2">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => openDetailSheet(flight)}
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => openEditModal(flight)}
                          >
                            <Pencil className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => openDeleteDialog(flight)}
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
            <DialogTitle>Add New Flight</DialogTitle>
          </DialogHeader>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="create-flight-type">Flight Type *</Label>
              <Select
                value={formData.flight_type}
                onValueChange={(value) => setFormData({ ...formData, flight_type: value })}
              >
                <SelectTrigger id="create-flight-type">
                  <SelectValue placeholder="Select flight type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="one_way">One Way</SelectItem>
                  <SelectItem value="return">Return</SelectItem>
                  <SelectItem value="multi_city">Multi-City</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="create-airline">Airline *</Label>
              <Select
                value={formData.airline}
                onValueChange={(value) => setFormData({ ...formData, airline: value })}
              >
                <SelectTrigger id="create-airline">
                  <SelectValue placeholder="Select airline" />
                </SelectTrigger>
                <SelectContent>
                  {airlines.map((airline) => (
                    <SelectItem key={airline} value={airline}>
                      {airline}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="create-custom-airline">Custom Airline</Label>
              <Input
                id="create-custom-airline"
                placeholder="Custom airline"
                value={customAirline}
                onChange={(e) => setCustomAirline(e.target.value)}
                disabled={formData.airline !== 'Others'}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="create-pnr">PNR Number</Label>
              <Input
                id="create-pnr"
                value={formData.pnr_number}
                onChange={(e) => setFormData({ ...formData, pnr_number: e.target.value })}
                placeholder="e.g., ABC123"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="create-flight-number">Flight Number</Label>
              <Input
                id="create-flight-number"
                value={formData.flight_number}
                onChange={(e) => setFormData({ ...formData, flight_number: e.target.value })}
                placeholder="e.g., EK203"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="create-departure">Departure City *</Label>
              <Input
                id="create-departure"
                value={formData.departure_city}
                onChange={(e) => setFormData({ ...formData, departure_city: e.target.value })}
                placeholder="e.g., Dubai"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="create-arrival">Arrival City *</Label>
              <Input
                id="create-arrival"
                value={formData.arrival_city}
                onChange={(e) => setFormData({ ...formData, arrival_city: e.target.value })}
                placeholder="e.g., Jeddah"
              />
            </div>


            <div className="space-y-2">
              <Label htmlFor="create-sale-price">Sale Price *</Label>
              <Input
                id="create-sale-price"
                type="number"
                step="0.01"
                value={formData.sale_price}
                onChange={(e) => setFormData({ ...formData, sale_price: e.target.value })}
                placeholder="0.00"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="create-purchase-price">Purchase Price *</Label>
              <Input
                id="create-purchase-price"
                type="number"
                step="0.01"
                value={formData.purchase_price}
                onChange={(e) => setFormData({ ...formData, purchase_price: e.target.value })}
                placeholder="0.00"
              />
            </div>

            {/* Multi-City Segments */}
            {formData.flight_type === 'multi_city' && (
              <div className="md:col-span-2 space-y-4">
                <div className="flex items-center justify-between">
                  <Label className="text-base font-medium">Flight Segments</Label>
                  <Button type="button" variant="outline" size="sm" onClick={addSegment}>
                    <Plus className="h-4 w-4 mr-2" />
                    Add Segment
                  </Button>
                </div>
                
                {segments.map((segment, index) => (
                  <Card key={index} className="p-4">
                    <div className="flex items-center justify-between mb-4">
                      <h4 className="font-medium">Segment {segment.segment_number}</h4>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => removeSegment(index)}
                        className="text-destructive hover:text-destructive"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                    
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label>Departure City *</Label>
                        <Input
                          value={segment.departure_city}
                          onChange={(e) => updateSegment(index, 'departure_city', e.target.value)}
                          placeholder="e.g., Dubai"
                        />
                      </div>
                      
                      <div className="space-y-2">
                        <Label>Arrival City *</Label>
                        <Input
                          value={segment.arrival_city}
                          onChange={(e) => updateSegment(index, 'arrival_city', e.target.value)}
                          placeholder="e.g., Jeddah"
                        />
                      </div>
                      
                      <div className="space-y-2">
                        <Label>Flight Number</Label>
                        <Input
                          value={segment.flight_number}
                          onChange={(e) => updateSegment(index, 'flight_number', e.target.value)}
                          placeholder="e.g., EK203"
                        />
                      </div>
                      
                      <div className="space-y-2">
                        <Label>Airline</Label>
                        <Input
                          value={segment.airline}
                          onChange={(e) => updateSegment(index, 'airline', e.target.value)}
                          placeholder="e.g., Emirates"
                        />
                      </div>
                      
                      <div className="space-y-2 md:col-span-2">
                        <Label>Notes</Label>
                        <Textarea
                          value={segment.notes}
                          onChange={(e) => updateSegment(index, 'notes', e.target.value)}
                          placeholder="Segment notes..."
                          rows={2}
                        />
                      </div>
                    </div>
                  </Card>
                ))}
                
                {segments.length === 0 && (
                  <div className="text-center py-8 text-muted-foreground">
                    <p>No segments added yet. Click "Add Segment" to get started.</p>
                  </div>
                )}
              </div>
            )}

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
            <Button onClick={handleCreateFlight} disabled={submitting}>
              {submitting ? 'Creating...' : 'Create Flight'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Modal */}
      <Dialog open={isEditModalOpen} onOpenChange={setIsEditModalOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Edit Flight</DialogTitle>
          </DialogHeader>
          <div className="grid grid-cols-1 gap-4 py-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="edit-flight-type">Flight Type *</Label>
                <Select
                  value={formData.flight_type}
                  onValueChange={(value) => setFormData({ ...formData, flight_type: value })}
                >
                  <SelectTrigger id="edit-flight-type">
                    <SelectValue placeholder="Select flight type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="one_way">One Way</SelectItem>
                    <SelectItem value="return">Return</SelectItem>
                    <SelectItem value="multi_city">Multi-City</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="edit-airline">Airline *</Label>
                <Select
                  value={formData.airline}
                  onValueChange={(value) => setFormData({ ...formData, airline: value })}
                >
                  <SelectTrigger id="edit-airline">
                    <SelectValue placeholder="Select airline" />
                  </SelectTrigger>
                  <SelectContent>
                    {airlines.map((airline) => (
                      <SelectItem key={airline} value={airline}>
                        {airline}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="edit-custom-airline">Custom Airline</Label>
              <Input
                id="edit-custom-airline"
                placeholder="Custom airline"
                value={customAirline}
                onChange={(e) => setCustomAirline(e.target.value)}
                disabled={formData.airline !== 'Others'}
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="edit-pnr">PNR Number</Label>
                <Input
                  id="edit-pnr"
                  value={formData.pnr_number}
                  onChange={(e) => setFormData({ ...formData, pnr_number: e.target.value })}
                  placeholder="e.g., ABC123"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="edit-flight-number">Flight Number</Label>
                <Input
                  id="edit-flight-number"
                  value={formData.flight_number}
                  onChange={(e) => setFormData({ ...formData, flight_number: e.target.value })}
                  placeholder="e.g., EK203"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="edit-departure">Departure City *</Label>
                <Input
                  id="edit-departure"
                  value={formData.departure_city}
                  onChange={(e) => setFormData({ ...formData, departure_city: e.target.value })}
                  placeholder="e.g., Dubai"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="edit-arrival">Arrival City *</Label>
                <Input
                  id="edit-arrival"
                  value={formData.arrival_city}
                  onChange={(e) => setFormData({ ...formData, arrival_city: e.target.value })}
                  placeholder="e.g., Jeddah"
                />
              </div>
            </div>


            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="edit-sale-price">Sale Price *</Label>
                <Input
                  id="edit-sale-price"
                  type="number"
                  step="0.01"
                  value={formData.sale_price}
                  onChange={(e) => setFormData({ ...formData, sale_price: e.target.value })}
                  placeholder="0.00"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="edit-purchase-price">Purchase Price *</Label>
                <Input
                  id="edit-purchase-price"
                  type="number"
                  step="0.01"
                  value={formData.purchase_price}
                  onChange={(e) => setFormData({ ...formData, purchase_price: e.target.value })}
                  placeholder="0.00"
                />
              </div>
            </div>

            {/* Multi-City Segments for Edit */}
            {formData.flight_type === 'multi_city' && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <Label className="text-base font-medium">Flight Segments</Label>
                  <Button type="button" variant="outline" size="sm" onClick={addSegment}>
                    <Plus className="h-4 w-4 mr-2" />
                    Add Segment
                  </Button>
                </div>
                
                {segments.map((segment, index) => (
                  <Card key={index} className="p-4">
                    <div className="flex items-center justify-between mb-4">
                      <h4 className="font-medium">Segment {segment.segment_number}</h4>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => removeSegment(index)}
                        className="text-destructive hover:text-destructive"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                    
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label>Departure City *</Label>
                        <Input
                          value={segment.departure_city}
                          onChange={(e) => updateSegment(index, 'departure_city', e.target.value)}
                          placeholder="e.g., Dubai"
                        />
                      </div>
                      
                      <div className="space-y-2">
                        <Label>Arrival City *</Label>
                        <Input
                          value={segment.arrival_city}
                          onChange={(e) => updateSegment(index, 'arrival_city', e.target.value)}
                          placeholder="e.g., Jeddah"
                        />
                      </div>
                      
                      <div className="space-y-2">
                        <Label>Flight Number</Label>
                        <Input
                          value={segment.flight_number}
                          onChange={(e) => updateSegment(index, 'flight_number', e.target.value)}
                          placeholder="e.g., EK203"
                        />
                      </div>
                      
                      <div className="space-y-2">
                        <Label>Airline</Label>
                        <Input
                          value={segment.airline}
                          onChange={(e) => updateSegment(index, 'airline', e.target.value)}
                          placeholder="e.g., Emirates"
                        />
                      </div>
                      
                      <div className="space-y-2 md:col-span-2">
                        <Label>Notes</Label>
                        <Textarea
                          value={segment.notes}
                          onChange={(e) => updateSegment(index, 'notes', e.target.value)}
                          placeholder="Segment notes..."
                          rows={2}
                        />
                      </div>
                    </div>
                  </Card>
                ))}
                
                {segments.length === 0 && (
                  <div className="text-center py-8 text-muted-foreground">
                    <p>No segments added yet. Click "Add Segment" to get started.</p>
                  </div>
                )}
              </div>
            )}

            <div className="space-y-2">
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
            <Button onClick={handleUpdateFlight} disabled={submitting}>
              {submitting ? 'Updating...' : 'Update Flight'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Detail Sheet */}
      <Sheet open={isDetailSheetOpen} onOpenChange={setIsDetailSheetOpen}>
        <SheetContent className="w-full sm:max-w-lg overflow-y-auto">
          <SheetHeader>
            <SheetTitle>Flight Details</SheetTitle>
          </SheetHeader>
          {selectedFlight && (
            <div className="mt-6 space-y-6">
              {/* Flight Header */}
              <div className="flex items-center gap-3 p-4 bg-primary/5 rounded-lg">
                <Plane className="h-8 w-8 text-primary" />
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <p className="font-semibold text-lg">{selectedFlight.airline}</p>
                    <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                      selectedFlight.flight_type === 'one_way' ? 'bg-blue-100 text-blue-800' :
                      selectedFlight.flight_type === 'return' ? 'bg-green-100 text-green-800' :
                      'bg-purple-100 text-purple-800'
                    }`}>
                      {selectedFlight.flight_type === 'one_way' ? 'One Way' :
                       selectedFlight.flight_type === 'return' ? 'Return' : 'Multi-City'}
                    </span>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {selectedFlight.flight_number ? `Flight ${selectedFlight.flight_number}` : 'Flight Number Not Set'}
                  </p>
                </div>
              </div>

              {/* Route Information */}
              <div>
                <Label className="text-sm font-medium text-muted-foreground">Route</Label>
                
                {/* Main Flight Route - Always show for all flight types */}
                <div className="mt-2 grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-muted-foreground">Departure</p>
                    <p className="font-medium">{selectedFlight.departure_city}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Arrival</p>
                    <p className="font-medium">{selectedFlight.arrival_city}</p>
                  </div>
                </div>

                {/* Flight Segments - Show for multi-city flights */}
                {selectedFlight.flight_type === 'multi_city' && selectedFlight.segments && selectedFlight.segments.length > 0 && (
                  <div className="mt-4">
                    <Label className="text-sm font-medium text-muted-foreground mb-3 block">Flight Segments</Label>
                    <div className="space-y-3">
                      {selectedFlight.segments.map((segment, index) => (
                        <div key={segment.id || index} className="p-3 border rounded-lg">
                          <div className="flex items-center justify-between mb-2">
                            <span className="text-sm font-medium text-muted-foreground">Segment {segment.segment_number}</span>
                            {segment.flight_number && (
                              <span className="text-xs bg-gray-100 px-2 py-1 rounded">{segment.flight_number}</span>
                            )}
                          </div>
                          <div className="grid grid-cols-2 gap-4">
                            <div>
                              <p className="text-sm text-muted-foreground">Departure</p>
                              <p className="font-medium">{segment.departure_city}</p>
                            </div>
                            <div>
                              <p className="text-sm text-muted-foreground">Arrival</p>
                              <p className="font-medium">{segment.arrival_city}</p>
                            </div>
                          </div>
                          {segment.airline && segment.airline !== selectedFlight.airline && (
                            <div className="mt-2">
                              <p className="text-sm text-muted-foreground">Airline</p>
                              <p className="text-sm">{segment.airline}</p>
                            </div>
                          )}
                          {segment.notes && (
                            <div className="mt-2">
                              <p className="text-sm text-muted-foreground">Notes</p>
                              <p className="text-sm">{segment.notes}</p>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Flight Details */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-sm font-medium text-muted-foreground">Flight Number</Label>
                  <p className="mt-1">{selectedFlight.flight_number || 'Not specified'}</p>
                </div>
                <div>
                  <Label className="text-sm font-medium text-muted-foreground">PNR Number</Label>
                  <p className="mt-1">{selectedFlight.pnr_number || 'Not specified'}</p>
                </div>
              </div>

              {/* Pricing */}
              <div>
                <Label className="text-sm font-medium text-muted-foreground">Pricing</Label>
                <div className="mt-2 grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-muted-foreground">Sale Price</p>
                    <p className="font-medium text-lg">${Number(selectedFlight.sale_price || 0).toFixed(2)}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Purchase Price</p>
                    <p className="font-medium text-lg">${Number(selectedFlight.purchase_price || 0).toFixed(2)}</p>
                  </div>
                </div>
              </div>

              {/* Notes */}
              {selectedFlight.notes && (
                <div>
                  <Label className="text-sm font-medium text-muted-foreground">Notes</Label>
                  <p className="mt-1 text-sm">{selectedFlight.notes}</p>
                </div>
              )}

              {/* Audit Information */}
              <div className="pt-4 border-t">
                <Label className="text-sm font-medium text-muted-foreground">Audit Information</Label>
                <div className="mt-2 space-y-2">
                  {selectedFlight.created_by && (
                    <div>
                      <p className="text-sm text-muted-foreground">Created By</p>
                      <p className="text-sm">{selectedFlight.created_by}</p>
                    </div>
                  )}
                  {selectedFlight.created_at && (
                    <div>
                      <p className="text-sm text-muted-foreground">Created At</p>
                      <p className="text-sm">{new Date(selectedFlight.created_at).toLocaleString()}</p>
                    </div>
                  )}
                  {selectedFlight.updated_at && (
                    <div>
                      <p className="text-sm text-muted-foreground">Last Updated</p>
                      <p className="text-sm">{new Date(selectedFlight.updated_at).toLocaleString()}</p>
                    </div>
                  )}
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
            <AlertDialogTitle>Delete Flight</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete flight {flightToDelete?.flight_number} 
              ({flightToDelete?.airline})? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDeleteFlight} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}