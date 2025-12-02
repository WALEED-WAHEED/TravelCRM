import React, { useState, useEffect, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { useAuthStore } from '@/context/auth';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { Progress } from '@/components/ui/progress';
import { toast } from '@/hooks/use-toast';
import {
  ArrowLeft,
  ArrowRight,
  Check,
  Hotel,
  Plane,
  Car,
  Users,
  FileText,
  CheckCircle,
  Search,
  Plus,
  Trash2,
  Building,
  RefreshCw,
  Phone,
} from 'lucide-react';
import apiClient from '@/api/client';
import { useNavigate } from 'react-router-dom';

// Interfaces

interface Hotel {
  id: number;
  name: string;
  city: string;
  rating: number;
  nightly_rate: number;
  address?: string;
}

interface Flight {
  id: number;
  flight_type: string;
  airline: string;
  flight_number?: string;
  pnr_number?: string;
  departure_airport?: string;
  arrival_airport?: string;
  departure_city: string;
  arrival_city: string;
  departure_time?: string;
  arrival_time?: string;
  sale_price: number;
  purchase_price: number;
  notes?: string;
  created_by?: string;
  created_at?: string;
  updated_at?: string;
  segments?: FlightSegment[];
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
  departure_time?: string;
  arrival_time?: string;
  notes: string;
}

interface Transport {
  id: number;
  name: string;
  transport_type: string;
  capacity: number;
  sale_price?: number | string;
  purchase_price?: number | string;
  amenities?: string[];
  notes?: string;
  is_active?: boolean;
}

interface Mutamer {
  id: number;
  name: string;
  passport_number: string;
  visa_number?: string;
  nationality: string;
  gender: string;
  phone?: string;
  email?: string;
  family_id?: string;
  is_family_head: boolean;
  family_head_name?: string;
  person_type?: string;
  date_of_birth?: string;
  age?: number;
  is_active?: boolean;
}

interface Contact {
  id: number;
  city: string;
  role: string;
  contact_name: string;
  phone_number: string;
  notes?: string;
}

interface BookingData {
  // Basic booking info
  voucher_number: string;
  manual_number: string;
  pax_adults: number;
  pax_children: number;
  pax_infants: number;
  total_beds: number;
  
  // Client info
  client_company: string;
  client_country: string;
  client_whatsapp: string;
  
  // Accommodation details
  hotels: Array<{ 
    id: number; 
    city: string;
    hotel_name: string;
    view: string;
    meal_plan: string;
    meal: string;
    confirmation_number: string;
    room_type: string;
    check_in: string; 
    check_out: string; 
    nights: number;
  }>;
  
  // Flight details
  outbound_flight_id: number | null;
  return_flight_id: number | null;
  outbound_departure_time?: string;
  outbound_arrival_time?: string;
  return_departure_time?: string;
  return_arrival_time?: string;
  
  // Transport details
  transports: Array<{
    id: number;
    travel_date: string;
    transporter: string; // Read-only from transport.name
    vehicle_type: string; // Read-only from transport.transport_type
    description: string; // Read-only from transport.name or description
  }>;
  
  // Travelers
  mutamers: number[];
  contacts: number[];
  
  // Instructions and notes
  special_instructions: string;
  notes: string;
  
  // Team contacts - not stored, just displayed from contacts page (read-only)
}

const STEPS = [
  { number: 1, title: 'Basic Info', icon: FileText },
  { number: 2, title: 'Hotels', icon: Hotel },
  { number: 3, title: 'Flights', icon: Plane },
  { number: 4, title: 'Transport', icon: Car },
  { number: 5, title: 'Mutamers', icon: Users },
  { number: 6, title: 'Team Contacts', icon: Users },
  { number: 7, title: 'Review', icon: CheckCircle },
];

const ROOM_TYPES = [
  { value: 'single', label: 'Single Bed Room' },
  { value: 'double', label: 'Double Bed' },
  { value: 'triple', label: 'Triple Bed' },
  { value: 'quad', label: 'Quad Bed' },
  { value: 'quint', label: 'Quint Bed' },
  { value: 'sharing', label: 'Sharing' },
];

// Function to calculate nights between two dates
const calculateNights = (checkIn: string, checkOut: string): number => {
  if (!checkIn || !checkOut) return 1;
  
  const checkInDate = new Date(checkIn);
  const checkOutDate = new Date(checkOut);
  
  // Calculate the difference in milliseconds
  const timeDiff = checkOutDate.getTime() - checkInDate.getTime();
  
  // Convert to days and ensure it's at least 1 night
  const nights = Math.ceil(timeDiff / (1000 * 3600 * 24));
  
  return Math.max(1, nights);
};

export default function MemberBookings() {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const [currentStep, setCurrentStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [voucherNumbersRestored, setVoucherNumbersRestored] = useState(false);

  // Data from APIs
  const [hotels, setHotels] = useState<Hotel[]>([]);
  const [flights, setFlights] = useState<Flight[]>([]);
  const [transports, setTransports] = useState<Transport[]>([]);
  const [mutamers, setMutamers] = useState<Mutamer[]>([]);
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [agencyBranding, setAgencyBranding] = useState<any>(null);

  // Flight search and filter state
  const [flightSearchTerm, setFlightSearchTerm] = useState('');
  const [flightFilterFromCity, setFlightFilterFromCity] = useState('all');
  const [flightFilterToCity, setFlightFilterToCity] = useState('all');

  // Booking state
  const [bookingData, setBookingData] = useState<BookingData>({
    // Basic booking info
    voucher_number: '',
    manual_number: '',
    pax_adults: 0,
    pax_children: 0,
    pax_infants: 0,
    total_beds: 0,
    
    // Client info
    client_company: '',
    client_country: '',
    client_whatsapp: '',
    
    // Accommodation details
    hotels: [],
    
    // Flight details
    outbound_flight_id: null,
    return_flight_id: null,
    outbound_departure_time: '',
    outbound_arrival_time: '',
    return_departure_time: '',
    return_arrival_time: '',
    
    // Transport details
    transports: [],
    
    // Travelers
    mutamers: [],
    contacts: [],
    
    // Instructions and notes
    special_instructions: '',
    notes: '',
    
    // Team contacts
  });

  // Hotel selection state
  const [selectedHotels, setSelectedHotels] = useState<
    Array<{ 
      id: number; 
      city: string;
      hotel_name: string;
      view: string;
      meal_plan: string;
      confirmation_number: string;
      room_type: string;
      check_in: string; 
      check_out: string; 
      nights: number;
    }>
  >([]);

  // Fetch all data on mount
  useEffect(() => {
    fetchAllData();
  }, []);

  // Filter flights based on search and filters
  const filteredFlights = flights.filter((flight) => {
    const matchesSearch = !flightSearchTerm || 
      flight.airline.toLowerCase().includes(flightSearchTerm.toLowerCase()) ||
      (flight.flight_number && flight.flight_number.toLowerCase().includes(flightSearchTerm.toLowerCase()));
    
    const matchesFromCity = flightFilterFromCity === 'all' || flight.departure_city === flightFilterFromCity;
    const matchesToCity = flightFilterToCity === 'all' || flight.arrival_city === flightFilterToCity;
    
    return matchesSearch && matchesFromCity && matchesToCity;
  });

  // Organize flights by type
  const organizedFlights = {
    oneWay: filteredFlights.filter(flight => flight.flight_type === 'one_way'),
    return: filteredFlights.filter(flight => flight.flight_type === 'return'),
    multiCity: filteredFlights.filter(flight => flight.flight_type === 'multi_city')
  };

  // Get unique cities for filters
  const uniqueFromCities = [...new Set(flights.map(flight => flight.departure_city))].sort();
  const uniqueToCities = [...new Set(flights.map(flight => flight.arrival_city))].sort();

  // Selected flights for review section
  const selectedFlights = useMemo(() => {
    const entries: Array<{ key: 'outbound' | 'return'; label: string; flight: Flight }> = [];

    if (bookingData.outbound_flight_id) {
      const outbound = flights.find((flight) => flight.id === bookingData.outbound_flight_id);
      if (outbound) {
        entries.push({ key: 'outbound', label: 'Outbound', flight: outbound });
      }
    }

    if (bookingData.return_flight_id) {
      const returnFlight = flights.find((flight) => flight.id === bookingData.return_flight_id);
      if (returnFlight) {
        entries.push({ key: 'return', label: 'Return', flight: returnFlight });
      }
    }

    return entries;
  }, [bookingData.outbound_flight_id, bookingData.return_flight_id, flights]);

  const totalFlightSalePrice = selectedFlights.reduce(
    (total, entry) => total + Number(entry.flight.sale_price || 0),
    0
  );

  const formatCurrency = (value: number | string | null | undefined) => {
    const amount = Number(value ?? 0);
    return `$${amount.toFixed(2)}`;
  };

  const getFlightTypeLabel = (type: string) => {
    switch (type) {
      case 'one_way':
        return 'One Way';
      case 'return':
        return 'Return';
      case 'multi_city':
        return 'Multi-City';
      default:
        return type;
    }
  };

  const getFlightTypeBadgeClasses = (type: string) => {
    switch (type) {
      case 'one_way':
        return 'bg-blue-100 text-blue-800';
      case 'return':
        return 'bg-green-100 text-green-800';
      case 'multi_city':
        return 'bg-purple-100 text-purple-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  // Helper function to format sector (airport codes or city initials)
  const formatSector = (departure: string, arrival: string, depAirport?: string, arrAirport?: string) => {
    // Use airport if available and not "N/A", otherwise use first 3 letters of city
    const dep = (depAirport && depAirport !== 'N/A' && depAirport.trim() !== '') 
      ? depAirport.toUpperCase() 
      : departure.substring(0, 3).toUpperCase();
    const arr = (arrAirport && arrAirport !== 'N/A' && arrAirport.trim() !== '') 
      ? arrAirport.toUpperCase() 
      : arrival.substring(0, 3).toUpperCase();
    return `${dep}-${arr}`;
  };

  // Helper function to render flight cards
  const renderFlightCards = (flightList: Flight[], isSelected: (flight: Flight) => boolean, onSelect: (flight: Flight) => void, direction: string) => {
    if (flightList.length === 0) {
      return (
        <div className="text-center text-muted-foreground py-8">
          No {direction.toLowerCase()} flights found matching your criteria
        </div>
      );
    }

    return (
      <div className="grid gap-3">
        {flightList.map((flight) => {
          const selected = isSelected(flight);
          return (
            <div
              key={flight.id}
              className={`p-4 border rounded-lg cursor-pointer transition-all ${
                selected ? 'border-primary bg-primary/5 ring-2 ring-primary/20' : 'border-border hover:border-primary/50'
              }`}
              onClick={() => onSelect(flight)}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={`w-4 h-4 rounded-full border-2 flex items-center justify-center ${
                    selected ? 'border-primary bg-primary' : 'border-muted-foreground'
                  }`}>
                    {selected && <div className="w-2 h-2 rounded-full bg-white" />}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold">{flight.airline}</span>
                      <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                        flight.flight_type === 'one_way' ? 'bg-blue-100 text-blue-800' :
                        flight.flight_type === 'return' ? 'bg-green-100 text-green-800' :
                        'bg-purple-100 text-purple-800'
                      }`}>
                        {flight.flight_type === 'one_way' ? 'One Way' :
                         flight.flight_type === 'return' ? 'Return' : 'Multi-City'}
                      </span>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {flight.flight_number || 'N/A'} • {
                        (flight.departure_airport && flight.departure_airport !== 'N/A' && flight.departure_airport.trim() !== '') 
                          ? flight.departure_airport.toUpperCase() 
                          : flight.departure_city.substring(0, 3).toUpperCase()
                      } → {
                        (flight.arrival_airport && flight.arrival_airport !== 'N/A' && flight.arrival_airport.trim() !== '') 
                          ? flight.arrival_airport.toUpperCase() 
                          : flight.arrival_city.substring(0, 3).toUpperCase()
                      }
                    </p>
                    {flight.departure_time && flight.arrival_time && (
                      <p className="text-xs text-muted-foreground mt-1">
                        {new Date(flight.departure_time).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })} → {new Date(flight.arrival_time).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}
                      </p>
                    )}
                  </div>
                </div>
                <div className="text-right">
                  <p className="font-semibold">${Number(flight.sale_price || 0).toFixed(2)}</p>
                  <p className="text-xs text-muted-foreground">Sale Price</p>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  const fetchAllData = async () => {
    const fetchData = async (url: string, setter: (data: any[]) => void, name: string) => {
      try {
        const response = await apiClient.get(url);
        const data = Array.isArray(response.data) ? response.data : response.data.results || [];
        setter(data);
        if (name === 'contacts') {
          console.log(`✅ Fetched ${data.length} contacts from ${url}`, data);
        }
      } catch (error: any) {
        console.error(`Failed to fetch ${name} from ${url}:`, error);
        console.error('Error details:', error.response?.data);
        setter([]);
        toast({
          title: 'Warning',
          description: `Failed to load ${name}. You can still proceed with booking.`,
          variant: 'destructive',
        });
      }
    };

    const fetchAgencyBranding = async () => {
      try {
        const response = await apiClient.get('/api/v1/accounts/profile/');
        setAgencyBranding(response.data);
        console.log('✅ Agency branding loaded:', response.data);
      } catch (error) {
        console.error('❌ Error loading agency branding:', error);
      }
    };

    // Fetch each endpoint independently
    await Promise.all([
      fetchData('/api/v1/hotels/hotels/', setHotels, 'hotels'),
      fetchData('/api/v1/flights/flights/', setFlights, 'flights'),
      fetchData('/api/v1/transports/transports/', setTransports, 'transports'),
      fetchData('/api/v1/mutamers/mutamers/', setMutamers, 'mutamers'),
      fetchData('/api/v1/contacts/contacts/', setContacts, 'contacts'),
      fetchAgencyBranding(),
    ]);
  };

  // Calculate PAX (Adults, Children, Infants) and beds from selected mutamers
  useEffect(() => {
    const selectedMutamerObjects = mutamers.filter(m => bookingData.mutamers.includes(m.id));
    
    let adults = 0;
    let children = 0;
    let infants = 0;
    
    selectedMutamerObjects.forEach((mutamer) => {
      // If person_type is explicitly set, use it
      if (mutamer.person_type) {
        if (mutamer.person_type === 'adult') {
          adults++;
        } else if (mutamer.person_type === 'child') {
          children++;
        } else if (mutamer.person_type === 'infant') {
          infants++;
        }
      } else {
        // If person_type is not set, try to infer from age if available
        if (mutamer.age !== undefined && mutamer.age !== null) {
          if (mutamer.age >= 18) {
            adults++;
          } else if (mutamer.age >= 2) {
            children++;
          } else {
            infants++;
          }
        } else {
          // Default to adult if no age or person_type is available
          adults++;
        }
      }
    });
    
    // Calculate beds: Adults and children need beds, infants don't (they share with parents)
    const beds = adults + children;
    
    // Update bookingData with calculated values
    setBookingData(prev => ({
      ...prev,
      pax_adults: adults,
      pax_children: children,
      pax_infants: infants,
      total_beds: beds,
    }));
  }, [bookingData.mutamers, mutamers]);

  // Reset booking data and generate fresh voucher numbers
  const startNewBooking = async () => {
    if (!agencyBranding?.company_name) {
      toast({
        title: 'Error',
        description: 'Company profile not loaded. Please refresh the page.',
        variant: 'destructive',
      });
      return;
    }

    try {
      // Generate fresh voucher numbers
      const response = await apiClient.get('/api/v1/accounts/voucher-number/');
      
      // Save the new voucher numbers to localStorage
      saveVoucherNumbers(response.data.voucher_number, response.data.manual_number);
      
      // Reset booking data with fresh voucher numbers and company info
      setBookingData({
        // Basic booking info
        voucher_number: response.data.voucher_number,
        manual_number: response.data.manual_number,
        pax_adults: 0,
        pax_children: 0,
        pax_infants: 0,
        total_beds: 0,
        
        // Client info (from company profile)
        client_company: agencyBranding.company_name || '',
        client_country: agencyBranding.custom_fields?.country || '',
        client_whatsapp: agencyBranding.phone || '',
        
        // Accommodation details
        hotels: [],
        
        // Flight details
        outbound_flight_id: null,
        return_flight_id: null,
        
        // Transport details
        transports: [],
        
        // Mutamers
        mutamers: [],
        
      });
      
      setCurrentStep(1);
      
      toast({
        title: 'Success',
        description: 'New booking started with fresh voucher numbers!',
      });
    } catch (error) {
      console.error('Error starting new booking:', error);
      toast({
        title: 'Error',
        description: 'Failed to start new booking. Please try again.',
        variant: 'destructive',
      });
    }
  };

  const handleNext = () => {
    // Validation for each step
    if (currentStep === 1 && (!bookingData.voucher_number || !bookingData.client_company)) {
      toast({
        title: 'Validation Error',
        description: 'Please fill in all required basic information fields',
        variant: 'destructive',
      });
      return;
    }
    if (currentStep === 2 && bookingData.hotels.length === 0) {
      toast({
        title: 'Validation Error',
        description: 'Please select at least one hotel',
        variant: 'destructive',
      });
      return;
    }
    if (currentStep === 3 && !bookingData.outbound_flight_id) {
      toast({
        title: 'Validation Error',
        description: 'Please select an outbound flight',
        variant: 'destructive',
      });
      return;
    }
    if (currentStep === 5 && bookingData.mutamers.length === 0) {
      toast({
        title: 'Validation Error',
        description: 'Please select at least one mutamer',
        variant: 'destructive',
      });
      return;
    }

    if (currentStep < 7) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handlePrevious = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleFinish = async () => {
    try {
      setLoading(true);

      // Determine user role for approval workflow
      const userRole = user?.role || 'agent';
      const isMember = userRole === 'member' || userRole === 'developer';

      // Create booking
      const bookingResponse = await apiClient.post('/api/v1/bookings/bookings/', bookingData);

      // Get the first mutamer for voucher creation (vouchers require a mutamer)
      const firstMutamerId = bookingData.mutamers.length > 0 ? bookingData.mutamers[0] : null;
      
      if (!firstMutamerId) {
        throw new Error('At least one mutamer is required to create a voucher');
      }

      // Create voucher (always start as pending, then approve if member)
      const voucherData = {
        mutamer: firstMutamerId,
        total_amount: bookingData.total_price || calculateTotalPrice(),
        paid_amount: 0,
        notes: bookingData.notes || '',
        status: 'pending', // Always start as pending
      };

      const voucherResponse = await apiClient.post('/api/v1/vouchers/vouchers/', voucherData);

      // If member/developer created it, automatically approve it
      if (isMember && voucherResponse.data.id) {
        await apiClient.post(`/api/v1/vouchers/vouchers/${voucherResponse.data.id}/approve/`);
      }

      // Mark voucher as completed (this will clear localStorage and allow new numbers for next booking)
      markVoucherAsCompleted();

      toast({
        title: 'Success',
        description: isMember 
          ? 'Booking created and voucher approved successfully'
          : 'Booking created and voucher sent for approval',
      });

      // Navigate based on user role
      if (isMember) {
        // Member/Developer → go directly to vouchers page
        navigate('/member/vouchers');
      } else {
        // Agent → go to approvals page for member to approve
        navigate('/member/approvals');
      }
    } catch (error: any) {
      console.error('Error creating booking/voucher:', error);
      toast({
        title: 'Error',
        description: error.response?.data?.detail || error.message || 'Failed to create booking',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const toggleHotelSelection = (hotelId: number) => {
    const exists = selectedHotels.find((h) => h.id === hotelId);
    if (exists) {
      setSelectedHotels(selectedHotels.filter((h) => h.id !== hotelId));
      setBookingData({
        ...bookingData,
        hotels: bookingData.hotels.filter((h) => h.id !== hotelId),
      });
    } else {
      const hotel = hotels.find(h => h.id === hotelId);
      const newHotel = { 
        id: hotelId, 
        city: hotel?.city || '',
        hotel_name: hotel?.name || '',
        view: 'Standard',
        meal_plan: 'RO',
        meal: 'No',
        confirmation_number: '',
        room_type: 'sharing',
        check_in: '', 
        check_out: '', 
        nights: 1 
      };
      setSelectedHotels([...selectedHotels, newHotel]);
      setBookingData({
        ...bookingData,
        hotels: [...bookingData.hotels, newHotel],
      });
    }
  };

  const updateHotelDetails = (
    hotelId: number,
    field: 'nights' | 'check_in' | 'check_out' | 'room_type' | 'city' | 'hotel_name' | 'view' | 'meal_plan' | 'meal' | 'confirmation_number',
    value: string | number
  ) => {
    const updated = bookingData.hotels.map((h) =>
      h.id === hotelId ? { ...h, [field]: value } : h
    );
    setBookingData({ ...bookingData, hotels: updated });
    setSelectedHotels(updated);
  };

  // Function to handle date changes and auto-calculate nights
  const updateHotelDate = (hotelId: number, field: 'check_in' | 'check_out', value: string) => {
    const hotel = bookingData.hotels.find((h) => h.id === hotelId);
    if (!hotel) return;

    // Update the specific field
    const updatedHotel = { ...hotel, [field]: value };
    
    // Calculate nights if both dates are available
    let calculatedNights = hotel.nights;
    if (field === 'check_in' && value && hotel.check_out) {
      calculatedNights = calculateNights(value, hotel.check_out);
    } else if (field === 'check_out' && value && hotel.check_in) {
      calculatedNights = calculateNights(hotel.check_in, value);
    }

    // Update the hotel with new date and calculated nights
    const updated = bookingData.hotels.map((h) =>
      h.id === hotelId ? { ...updatedHotel, nights: calculatedNights } : h
    );
    
    setBookingData({ ...bookingData, hotels: updated });
    setSelectedHotels(updated);
  };

  const toggleTransportSelection = (transportId: number) => {
    const exists = bookingData.transports.find(t => t.id === transportId);
    if (exists) {
      setBookingData({
        ...bookingData,
        transports: bookingData.transports.filter((t) => t.id !== transportId),
      });
    } else {
      const transport = transports.find(t => t.id === transportId);
      setBookingData({
        ...bookingData,
        transports: [...bookingData.transports, {
          id: transportId,
          travel_date: '',
          transporter: transport?.name || '',
          vehicle_type: transport?.transport_type ? transport.transport_type.charAt(0).toUpperCase() + transport.transport_type.slice(1) : '',
          description: transport?.name || ''
        }],
      });
    }
  };

  const updateTransportDetails = (
    transportId: number,
    field: 'travel_date' | 'transporter' | 'vehicle_type' | 'description',
    value: string
  ) => {
    // Only allow editing travel_date, other fields are read-only and fetched from transport page
    if (field !== 'travel_date') {
      return;
    }
    const updated = bookingData.transports.map((t) =>
      t.id === transportId ? { ...t, [field]: value } : t
    );
    setBookingData({ ...bookingData, transports: updated });
  };

  const toggleMutamerSelection = (mutamerId: number) => {
    const exists = bookingData.mutamers.includes(mutamerId);
    if (exists) {
      setBookingData({
        ...bookingData,
        mutamers: bookingData.mutamers.filter((id) => id !== mutamerId),
      });
    } else {
      setBookingData({
        ...bookingData,
        mutamers: [...bookingData.mutamers, mutamerId],
      });
    }
  };

  const toggleContactSelection = (contactId: number) => {
    const exists = bookingData.contacts.includes(contactId);
    if (exists) {
      setBookingData({
        ...bookingData,
        contacts: bookingData.contacts.filter((id) => id !== contactId),
      });
    } else {
      setBookingData({
        ...bookingData,
        contacts: [...bookingData.contacts, contactId],
      });
    }
  };

  const calculateTotalPrice = () => {
    let total = 0;

    // Hotels
    bookingData.hotels.forEach((hotel) => {
      const h = hotels.find((ht) => ht.id === hotel.id);
      if (h) total += h.nightly_rate * hotel.nights;
    });

    // Flights
    const outbound = flights.find((f) => f.id === bookingData.outbound_flight_id);
    const returnFlight = flights.find((f) => f.id === bookingData.return_flight_id);
    if (outbound) total += Number(outbound.sale_price || 0);
    if (returnFlight) total += Number(returnFlight.sale_price || 0);

    // Transports
    bookingData.transports.forEach((transport) => {
      const t = transports.find((tr) => tr.id === transport.id);
      if (t) total += t.price;
    });

    return total;
  };

  // Get family head name from selected mutamers
  const getFamilyHeadName = () => {
    const selectedMutamers = mutamers.filter(m => bookingData.mutamers.includes(m.id));
    const familyHead = selectedMutamers.find(m => m.is_family_head);
    return familyHead ? familyHead.name : (selectedMutamers[0]?.name || 'No family head selected');
  };

  // Generate voucher number based on company name and sequence
  const generateVoucherNumber = (companyName: string, sequence: number) => {
    if (!companyName) return `V-${sequence.toString().padStart(6, '0')}`;
    
    // Extract first 3-4 letters from company name and convert to uppercase
    const prefix = companyName.replace(/[^a-zA-Z]/g, '').substring(0, 4).toUpperCase();
    return `${prefix}-${sequence.toString().padStart(6, '0')}`;
  };

  // Extract sequence number from voucher number (e.g., "NAHD-000016" -> 16)
  const extractSequenceNumber = (voucherNumber: string): number => {
    try {
      const parts = voucherNumber.split('-');
      if (parts.length > 1) {
        const sequenceStr = parts[parts.length - 1];
        return parseInt(sequenceStr, 10);
      }
    } catch (error) {
      console.error('Error extracting sequence number:', error);
    }
    return 0;
  };

  // Load voucher numbers from localStorage
  const loadVoucherNumbers = () => {
    try {
      const savedVoucherData = localStorage.getItem('current_voucher_numbers');
      if (savedVoucherData) {
        const { voucher_number, manual_number, timestamp } = JSON.parse(savedVoucherData);
        // Check if the voucher is not too old (24 hours)
        const now = new Date().getTime();
        const voucherTime = new Date(timestamp).getTime();
        const hoursDiff = (now - voucherTime) / (1000 * 60 * 60);
        
        if (hoursDiff < 24) {
          return { voucher_number, manual_number };
        }
      }
    } catch (error) {
      console.error('Error loading voucher numbers from localStorage:', error);
    }
    return null;
  };

  // Save voucher numbers to localStorage
  const saveVoucherNumbers = (voucher_number: string, manual_number: string) => {
    try {
      const voucherData = {
        voucher_number,
        manual_number,
        timestamp: new Date().toISOString()
      };
      localStorage.setItem('current_voucher_numbers', JSON.stringify(voucherData));
    } catch (error) {
      console.error('Error saving voucher numbers to localStorage:', error);
    }
  };

  // Mark voucher as completed (remove from localStorage)
  const markVoucherAsCompleted = () => {
    try {
      localStorage.removeItem('current_voucher_numbers');
      toast({
        title: 'Voucher Completed',
        description: 'Voucher has been generated successfully. New numbers will be generated for the next booking.',
      });
    } catch (error) {
      console.error('Error marking voucher as completed:', error);
    }
  };

  // Generate fresh voucher numbers (called when page opens or user clicks generate)
  const generateFreshVoucherNumbers = async () => {
    if (!agencyBranding?.company_name) {
      toast({
        title: 'Error',
        description: 'Company profile not loaded. Please refresh the page.',
        variant: 'destructive',
      });
      return;
    }

    try {
      const response = await apiClient.get('/api/v1/accounts/voucher-number/');
      
      // Save the new voucher numbers to localStorage
      saveVoucherNumbers(response.data.voucher_number, response.data.manual_number);
      
      setBookingData(prev => ({
        ...prev,
        voucher_number: response.data.voucher_number,
        manual_number: response.data.manual_number,
      }));
      
      toast({
        title: 'Success',
        description: 'New voucher numbers generated successfully!',
      });
    } catch (error) {
      console.error('Error generating voucher number:', error);
      // Fallback to frontend generation
      const sequence = Math.floor(Math.random() * 1000000) + 100000;
      const voucherNumber = generateVoucherNumber(agencyBranding.company_name, sequence);
      
      // Save the generated voucher numbers to localStorage
      saveVoucherNumbers(voucherNumber, voucherNumber);
      
      setBookingData(prev => ({
        ...prev,
        voucher_number: voucherNumber,
        manual_number: voucherNumber,
      }));
      
      toast({
        title: 'Success',
        description: 'New voucher numbers generated (offline mode)!',
      });
    }
  };

  // Auto-populate company info and load/generate voucher numbers when agency branding is loaded
  useEffect(() => {
    const populateCompanyInfoAndLoadVoucher = async () => {
      if (agencyBranding && agencyBranding.company_name) {
        try {
          // Always fetch from backend first to get current sequence
          const response = await apiClient.get('/api/v1/accounts/voucher-number/');
          const backendVoucherNumber = response.data.voucher_number;
          const backendManualNumber = response.data.manual_number;
          
          // Try to load existing voucher numbers from localStorage
          const savedVoucherNumbers = loadVoucherNumbers();
          
          if (savedVoucherNumbers) {
            // Compare sequence numbers
            const savedSequence = extractSequenceNumber(savedVoucherNumbers.voucher_number);
            const backendSequence = extractSequenceNumber(backendVoucherNumber);
            
            // If backend sequence is lower (sequence was reset), use backend value
            if (backendSequence < savedSequence) {
              // Clear localStorage and use backend value
              localStorage.removeItem('current_voucher_numbers');
              saveVoucherNumbers(backendVoucherNumber, backendManualNumber);
              
              setBookingData(prev => ({
                ...prev,
                voucher_number: backendVoucherNumber,
                manual_number: backendManualNumber,
                // Company info from profile
                client_company: agencyBranding.company_name || '',
                client_country: agencyBranding.custom_fields?.country || '',
                client_whatsapp: agencyBranding.phone || '',
              }));
            } else {
              // Use saved voucher numbers (they're still valid)
              setVoucherNumbersRestored(true);
              setBookingData(prev => ({
                ...prev,
                voucher_number: savedVoucherNumbers.voucher_number,
                manual_number: savedVoucherNumbers.manual_number,
                // Company info from profile
                client_company: agencyBranding.company_name || '',
                client_country: agencyBranding.custom_fields?.country || '',
                client_whatsapp: agencyBranding.phone || '',
              }));
            }
          } else {
            // No saved numbers, use backend value
            saveVoucherNumbers(backendVoucherNumber, backendManualNumber);
            
            setBookingData(prev => ({
              ...prev,
              voucher_number: backendVoucherNumber,
              manual_number: backendManualNumber,
              // Company info from profile
              client_company: agencyBranding.company_name || '',
              client_country: agencyBranding.custom_fields?.country || '',
              client_whatsapp: agencyBranding.phone || '',
            }));
          }
        } catch (error) {
          console.error('Error generating voucher number:', error);
          // Fallback: try localStorage if backend fails
          const savedVoucherNumbers = loadVoucherNumbers();
          
          if (savedVoucherNumbers) {
            setVoucherNumbersRestored(true);
            setBookingData(prev => ({
              ...prev,
              voucher_number: savedVoucherNumbers.voucher_number,
              manual_number: savedVoucherNumbers.manual_number,
              // Company info from profile
              client_company: agencyBranding.company_name || '',
              client_country: agencyBranding.custom_fields?.country || '',
              client_whatsapp: agencyBranding.phone || '',
            }));
          } else {
            // Final fallback to frontend generation
            const sequence = Math.floor(Math.random() * 1000000) + 100000;
            const voucherNumber = generateVoucherNumber(agencyBranding.company_name, sequence);
            
            saveVoucherNumbers(voucherNumber, voucherNumber);
            
            setBookingData(prev => ({
              ...prev,
              voucher_number: voucherNumber,
              manual_number: voucherNumber,
              // Company info from profile
              client_company: agencyBranding.company_name || '',
              client_country: agencyBranding.custom_fields?.country || '',
              client_whatsapp: agencyBranding.phone || '',
            }));
          }
        }
      }
    };

    populateCompanyInfoAndLoadVoucher();
  }, [agencyBranding]);

  const progressPercentage = (currentStep / 7) * 100;

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background to-muted/20 py-8">
      <div className="container max-w-5xl mx-auto px-4">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <div className="flex-1"></div>
            <div className="flex-1 text-center">
          <h1 className="text-4xl font-bold text-foreground mb-2">Create New Booking</h1>
          <p className="text-muted-foreground">Complete all steps to generate a travel voucher</p>
            </div>
            <div className="flex-1 flex justify-end">
            </div>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="mb-8">
          <Progress value={progressPercentage} className="h-2 mb-4" />
          <div className="flex justify-between">
            {STEPS.map((step) => {
              const Icon = step.icon;
              const isActive = currentStep === step.number;
              const isCompleted = currentStep > step.number;

              return (
                <div
                  key={step.number}
                  className={`flex flex-col items-center gap-2 ${
                    isActive ? 'text-primary' : isCompleted ? 'text-primary/70' : 'text-muted-foreground'
                  }`}
                >
                  <div
                    className={`w-12 h-12 rounded-full flex items-center justify-center border-2 transition-all ${
                      isActive
                        ? 'border-primary bg-primary text-primary-foreground'
                        : isCompleted
                        ? 'border-primary bg-primary/10'
                        : 'border-muted-foreground/30'
                    }`}
                  >
                    {isCompleted ? <Check className="h-5 w-5" /> : <Icon className="h-5 w-5" />}
                  </div>
                  <span className="text-xs font-medium hidden sm:block">{step.title}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Step Content */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              {React.createElement(STEPS[currentStep - 1].icon, { className: 'h-5 w-5' })}
              Step {currentStep}: {STEPS[currentStep - 1].title}
            </CardTitle>
          </CardHeader>
          <CardContent className="min-h-[400px]">

            {/* Step 1: Basic Information */}
            {currentStep === 1 && (
              <div className="space-y-6">
                {/* Voucher Preview Header */}
                {agencyBranding && (
                  <div className="bg-white border-2 border-gray-300 rounded-lg p-6">
                    <div className="grid grid-cols-3 gap-4 items-start">
                      {/* Left: Agency Details */}
                      <div className="space-y-2">
                        <h4 className="text-lg font-bold text-blue-600 uppercase">{agencyBranding.company_name || 'NAHD TRAVELS'}</h4>
                        <div className="text-sm space-y-1">
                          <p className="font-bold">Voucher Date: {new Date().toLocaleDateString('en-GB')}</p>
                          <p className="font-bold">PAX: {bookingData.pax_adults + bookingData.pax_children + bookingData.pax_infants} (A:{bookingData.pax_adults}, C:{bookingData.pax_children}, I:{bookingData.pax_infants}), Beds={bookingData.total_beds}</p>
                        </div>
                      </div>
                      
                      {/* Center: Logo */}
                      <div className="flex justify-center">
                        {agencyBranding.logo_url ? (
                          <img src={agencyBranding.logo_url} alt="Company Logo" className="h-20 w-auto" />
                        ) : (
                          <div className="text-4xl font-bold text-blue-600">NAHD</div>
                        )}
                      </div>
                      
                      {/* Right: Shirka Company */}
                      <div className="space-y-2 text-right">
                        <h4 className="text-lg font-bold text-blue-600 uppercase">{agencyBranding.custom_fields?.parent_company_name || 'NOORI KAKI CO.'}</h4>
                        <div className="text-sm space-y-1">
                          <p className="font-bold uppercase">{agencyBranding.custom_fields?.parent_company_country || 'PAKISTAN'}</p>
                          <p className="font-bold">{agencyBranding.custom_fields?.parent_company_whatsapp || agencyBranding.phone || 'N/A'}</p>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                  {/* Left Column */}
                  <div className="space-y-6">
                  {/* Voucher Information */}
                    <div className="space-y-5">
                      <h3 className="text-lg font-semibold text-foreground pb-2 border-b">Voucher Information</h3>
                      <div className="space-y-5">
                    <div>
                          <Label htmlFor="voucher_number" className="text-sm font-medium mb-2 block">Voucher Number *</Label>
                      <Input
                        id="voucher_number"
                        value={bookingData.voucher_number}
                        readOnly
                            className="bg-muted text-muted-foreground h-10"
                        placeholder="Auto-generated from company name"
                      />
                          <p className="text-xs text-muted-foreground mt-2">
                        Generated automatically based on company name. Numbers persist until voucher is completed.
                        {voucherNumbersRestored && (
                          <span className="text-green-600 font-medium"> (Restored from previous session)</span>
                        )}
                      </p>
                    </div>
                    <div>
                          <Label htmlFor="manual_number" className="text-sm font-medium mb-2 block">Manual Number</Label>
                      <Input
                        id="manual_number"
                        value={bookingData.manual_number}
                        readOnly
                            className="bg-muted text-muted-foreground h-10"
                        placeholder="Same as voucher number"
                      />
                          <p className="text-xs text-muted-foreground mt-2">
                        Same as voucher number
                      </p>
                        </div>
                    </div>
                  </div>

                    {/* Agency Information Section */}
                    <div className="space-y-5 pt-6 border-t border-border">
                      <h3 className="text-lg font-semibold text-foreground pb-2 border-b">Agency Information</h3>
                      <div className="space-y-5">
                    <div>
                          <Label htmlFor="client_company" className="text-sm font-medium mb-2 block">Company Name *</Label>
                      <Input
                        id="client_company"
                        value={bookingData.client_company}
                        readOnly
                            className="bg-muted text-muted-foreground h-10"
                        placeholder="Auto-populated from company profile"
                      />
                          <p className="text-xs text-muted-foreground mt-2">
                        Fetched from your company profile
                      </p>
                    </div>
                      </div>
                    </div>
                  </div>

                  {/* Right Column - Shirka Company Information */}
                  <div className="space-y-5">
                    {agencyBranding?.custom_fields && (
                      <div className="space-y-5">
                        <h3 className="text-lg font-semibold text-foreground pb-2 border-b">Shirka Company Information</h3>
                        <div className="space-y-5">
                    <div>
                            <Label htmlFor="parent_company_name" className="text-sm font-medium mb-2 block">Shirka Company Name</Label>
                      <Input
                              id="parent_company_name"
                              value={agencyBranding.custom_fields?.parent_company_name || ''}
                        readOnly
                              className="bg-muted text-muted-foreground h-10"
                              placeholder="Shirka company name"
                      />
                            <p className="text-xs text-muted-foreground mt-2">
                              Fetched from member profile
                      </p>
                    </div>
                    <div>
                            <Label htmlFor="parent_company_country" className="text-sm font-medium mb-2 block">Shirka Company Country</Label>
                      <Input
                              id="parent_company_country"
                              value={agencyBranding.custom_fields?.parent_company_country || ''}
                        readOnly
                              className="bg-muted text-muted-foreground h-10"
                              placeholder="Shirka company country"
                      />
                            <p className="text-xs text-muted-foreground mt-2">
                              Fetched from member profile
                      </p>
                    </div>
                    <div>
                            <Label htmlFor="parent_company_whatsapp" className="text-sm font-medium mb-2 block">Shirka Company Contact</Label>
                      <Input
                              id="parent_company_whatsapp"
                              value={agencyBranding.custom_fields?.parent_company_whatsapp || ''}
                              readOnly
                              className="bg-muted text-muted-foreground h-10"
                              placeholder="Shirka company contact"
                            />
                            <p className="text-xs text-muted-foreground mt-2">
                              Fetched from member profile
                            </p>
                    </div>
                    </div>
                    </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Step 2: Choose Hotels */}
            {currentStep === 2 && (
              <div className="space-y-4">
                {/* Accommodation Table */}
                {selectedHotels.length > 0 && (
                  <div className="space-y-2">
                    <h3 className="text-lg font-semibold bg-gray-700 text-white px-4 py-2 rounded-t">Accommodation</h3>
                    <div className="border rounded-lg overflow-hidden">
                      <div className="overflow-x-auto">
                        <table className="w-full border-collapse">
                          <thead>
                            <tr className="bg-gray-100">
                              <th className="border p-2 text-left text-xs font-semibold">City</th>
                              <th className="border p-2 text-left text-xs font-semibold">Hotel Name</th>
                              <th className="border p-2 text-left text-xs font-semibold">Rating</th>
                              <th className="border p-2 text-left text-xs font-semibold">Room Type</th>
                              <th className="border p-2 text-left text-xs font-semibold">Check-in</th>
                              <th className="border p-2 text-left text-xs font-semibold">Check-out</th>
                              <th className="border p-2 text-left text-xs font-semibold">Nights</th>
                            </tr>
                          </thead>
                          <tbody>
                            {selectedHotels.map((hotelData) => {
                              const hotel = hotels.find(h => h.id === hotelData.id);
                              if (!hotel) return null;
                              
                              const roomTypeLabel = ROOM_TYPES.find(rt => rt.value === hotelData.room_type)?.label || 'Sharing';
                              const formatDate = (dateStr: string) => {
                                if (!dateStr) return '';
                                const date = new Date(dateStr);
                                const day = String(date.getDate()).padStart(2, '0');
                                const month = String(date.getMonth() + 1).padStart(2, '0');
                                const year = String(date.getFullYear()).slice(-2);
                                return `${day}-${month}-${year}`;
                              };
                              
                              const nights = hotelData.nights || calculateNights(hotelData.check_in || '', hotelData.check_out || '');
                              
                              return (
                                <tr key={hotelData.id}>
                                  <td className="border p-2 text-sm">{hotel.city}</td>
                                  <td className="border p-2 text-sm">{hotel.name}</td>
                                  <td className="border p-2 text-sm">{hotel.rating}★</td>
                                  <td className="border p-2 text-sm">{roomTypeLabel}</td>
                                  <td className="border p-2 text-sm">{formatDate(hotelData.check_in || '')}</td>
                                  <td className="border p-2 text-sm">{formatDate(hotelData.check_out || '')}</td>
                                  <td className="border p-2 text-sm">{nights}</td>
                                </tr>
                              );
                            })}
                            <tr className="bg-gray-50">
                              <td colSpan={6} className="border p-2 text-sm font-semibold text-right">Total Nights:</td>
                              <td className="border p-2 text-sm font-semibold">
                                {selectedHotels.reduce((total, hotelData) => {
                                  const nights = hotelData.nights || calculateNights(hotelData.check_in || '', hotelData.check_out || '');
                                  return total + nights;
                                }, 0)}
                              </td>
                            </tr>
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </div>
                )}
                
                <Label>Select Hotels</Label>
                <div className="grid gap-4">
                  {hotels.map((hotel) => {
                    const isSelected = selectedHotels.some((h) => h.id === hotel.id);
                    const hotelData = selectedHotels.find((h) => h.id === hotel.id);

                    return (
                      <div
                        key={hotel.id}
                        className={`p-4 border rounded-lg ${
                          isSelected ? 'border-primary bg-primary/5' : 'border-border'
                        }`}
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex items-start gap-3">
                            <Checkbox
                              checked={isSelected}
                              onCheckedChange={() => toggleHotelSelection(hotel.id)}
                            />
                            <div className="flex-1">
                              <h4 className="font-semibold text-lg mb-1">{hotel.name}</h4>
                              <div className="text-sm text-muted-foreground space-y-1">
                                <p><span className="font-medium">City:</span> {hotel.city}</p>
                                <p><span className="font-medium">Rating:</span> {hotel.rating}★</p>
                              </div>
                            </div>
                          </div>
                        </div>

                        {isSelected && (
                          <div className="mt-4 space-y-4 pl-8">
                            {/* Dates and room type */}
                            <div className={`grid grid-cols-2 gap-3 ${hotel.rating >= 4 ? 'lg:grid-cols-5' : 'lg:grid-cols-4'}`}>
                            <div>
                                <Label className="text-xs">Room Type</Label>
                                <Select
                                  value={hotelData?.room_type || 'sharing'}
                                  onValueChange={(value) =>
                                    updateHotelDetails(hotel.id, 'room_type', value)
                                  }
                                >
                                  <SelectTrigger>
                                    <SelectValue placeholder="Select room type" />
                                  </SelectTrigger>
                                  <SelectContent>
                                    {ROOM_TYPES.map((roomType) => (
                                      <SelectItem key={roomType.value} value={roomType.value}>
                                        {roomType.label}
                                      </SelectItem>
                                    ))}
                                  </SelectContent>
                                </Select>
                              </div>
                            {hotel.rating >= 4 && (
                              <div>
                                <Label className="text-xs">Meal</Label>
                                <Select
                                  value={hotelData?.meal || 'No'}
                                  onValueChange={(value) =>
                                    updateHotelDetails(hotel.id, 'meal', value)
                                  }
                                >
                                  <SelectTrigger>
                                    <SelectValue placeholder="Select meal" />
                                  </SelectTrigger>
                                  <SelectContent>
                                    <SelectItem value="Yes">Yes</SelectItem>
                                    <SelectItem value="No">No</SelectItem>
                                  </SelectContent>
                                </Select>
                            </div>
                            )}
                            <div>
                              <Label className="text-xs">Check-in</Label>
                              <Input
                                type="date"
                                value={hotelData?.check_in || ''}
                                onChange={(e) =>
                                    updateHotelDate(hotel.id, 'check_in', e.target.value)
                                }
                              />
                            </div>
                            <div>
                              <Label className="text-xs">Check-out</Label>
                              <Input
                                type="date"
                                value={hotelData?.check_out || ''}
                                onChange={(e) =>
                                    updateHotelDate(hotel.id, 'check_out', e.target.value)
                                  }
                                />
                              </div>
                              <div>
                                <Label className="text-xs">Nights</Label>
                                <Input
                                  type="number"
                                  min="1"
                                  value={hotelData?.nights || 1}
                                  onChange={(e) =>
                                    updateHotelDetails(hotel.id, 'nights', parseInt(e.target.value))
                                  }
                                  className={hotelData?.check_in && hotelData?.check_out ? 'bg-muted text-muted-foreground' : ''}
                                  readOnly={hotelData?.check_in && hotelData?.check_out}
                                  title={hotelData?.check_in && hotelData?.check_out ? 'Nights are automatically calculated from check-in and check-out dates' : ''}
                                />
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Step 3: Select Flights */}
            {currentStep === 3 && (
              <div className="space-y-8">
                {/* Flight Selection Table */}
                {(bookingData.outbound_flight_id || bookingData.return_flight_id) && (() => {
                  const outboundFlight = flights.find(f => f.id === bookingData.outbound_flight_id);
                  const returnFlight = flights.find(f => f.id === bookingData.return_flight_id);
                  
                  const formatDate = (dateStr: string) => {
                    if (!dateStr) return '';
                    const date = new Date(dateStr);
                    const day = String(date.getDate()).padStart(2, '0');
                    const months = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'];
                    const month = months[date.getMonth()];
                    const hours = String(date.getHours()).padStart(2, '0');
                    const minutes = String(date.getMinutes()).padStart(2, '0');
                    return `${day}-${month} ${hours}:${minutes}`;
                  };
                  
                  // Determine flight type for display based on the selected flight's type
                  let flightType = 'one_way';
                  const selectedFlight = outboundFlight || returnFlight;
                  
                  if (selectedFlight) {
                    if (selectedFlight.flight_type === 'multi_city' && selectedFlight.segments && selectedFlight.segments.length > 0) {
                      flightType = 'multi_city';
                    } else if (selectedFlight.flight_type === 'return') {
                      flightType = 'return';
                    } else {
                      flightType = 'one_way';
                    }
                  }
                  
                  return (
                    <div className="space-y-2">
                      <h3 className="text-lg font-semibold bg-gray-700 text-white px-4 py-2 rounded-t">Flight Itinerary</h3>
                      <div className="border rounded-lg overflow-hidden">
                        <div className="overflow-x-auto">
                          {flightType === 'return' && selectedFlight ? (
                            // Return Flight Format - Show both departure and arrival
                            <table className="w-full border-collapse">
                              <thead>
                                <tr>
                                  <th colSpan={4} className="bg-blue-600 text-white px-4 py-2 text-sm font-semibold text-center">
                                    Departure (Pakistan to KSA)
                                  </th>
                                </tr>
                                <tr className="bg-gray-100">
                                  <th className="border p-2 text-left text-xs font-semibold">Flight</th>
                                  <th className="border p-2 text-left text-xs font-semibold">Sector</th>
                                  <th className="border p-2 text-left text-xs font-semibold">Departure</th>
                                  <th className="border p-2 text-left text-xs font-semibold">Arrival</th>
                                </tr>
                              </thead>
                              <tbody>
                                <tr>
                                  <td className="border p-2 text-sm">{selectedFlight.flight_number || `${selectedFlight.airline}-${selectedFlight.id}`}</td>
                                  <td className="border p-2 text-sm">{formatSector(selectedFlight.departure_city, selectedFlight.arrival_city, selectedFlight.departure_airport, selectedFlight.arrival_airport)}</td>
                                  <td className="border p-2 text-sm">{formatDate(bookingData.outbound_departure_time || selectedFlight.departure_time as any) || 'N/A'}</td>
                                  <td className="border p-2 text-sm">{formatDate(bookingData.outbound_arrival_time || selectedFlight.arrival_time as any) || 'N/A'}</td>
                                </tr>
                              </tbody>
                              <thead>
                                <tr>
                                  <th colSpan={4} className="bg-blue-600 text-white px-4 py-2 text-sm font-semibold text-center">
                                    Arrival (KSA to PAK)
                                  </th>
                                </tr>
                                <tr className="bg-gray-100">
                                  <th className="border p-2 text-left text-xs font-semibold">Flight</th>
                                  <th className="border p-2 text-left text-xs font-semibold">Sector</th>
                                  <th className="border p-2 text-left text-xs font-semibold">Departure</th>
                                  <th className="border p-2 text-left text-xs font-semibold">Arrival</th>
                                </tr>
                              </thead>
                              <tbody>
                                <tr>
                                  <td className="border p-2 text-sm">{selectedFlight.flight_number || `${selectedFlight.airline}-${selectedFlight.id}`}</td>
                                  <td className="border p-2 text-sm">{formatSector(selectedFlight.arrival_city, selectedFlight.departure_city, selectedFlight.arrival_airport, selectedFlight.departure_airport)}</td>
                                  <td className="border p-2 text-sm">{formatDate(bookingData.return_departure_time || selectedFlight.arrival_time as any) || 'N/A'}</td>
                                  <td className="border p-2 text-sm">{formatDate(bookingData.return_arrival_time || selectedFlight.departure_time as any) || 'N/A'}</td>
                                </tr>
                              </tbody>
                            </table>
                          ) : flightType === 'multi_city' && selectedFlight && selectedFlight.segments && selectedFlight.segments.length > 0 ? (
                            // Multi-City Format - Show all segments in sequence
                            <table className="w-full border-collapse">
                              <thead>
                                <tr>
                                  <th colSpan={4} className="bg-blue-600 text-white px-4 py-2 text-sm font-semibold text-center">
                                    Multi-City Itinerary
                                  </th>
                                </tr>
                                <tr className="bg-gray-100">
                                  <th className="border p-2 text-left text-xs font-semibold">Flight</th>
                                  <th className="border p-2 text-left text-xs font-semibold">Sector</th>
                                  <th className="border p-2 text-left text-xs font-semibold">Departure</th>
                                  <th className="border p-2 text-left text-xs font-semibold">Arrival</th>
                                </tr>
                              </thead>
                              <tbody>
                                {selectedFlight.segments.sort((a, b) => (a.segment_number || 0) - (b.segment_number || 0)).map((segment, index) => {
                                  // Get custom times for this segment from bookingData
                                  const segmentTimeKey = `segment_${selectedFlight.id}_${index}_departure_time`;
                                  const segmentArrivalKey = `segment_${selectedFlight.id}_${index}_arrival_time`;
                                  const customDepTime = (bookingData as any)[segmentTimeKey];
                                  const customArrTime = (bookingData as any)[segmentArrivalKey];
                                  
                                  return (
                                    <tr key={index}>
                                      <td className="border p-2 text-sm">{segment.flight_number || `${segment.airline}-${index + 1}`}</td>
                                      <td className="border p-2 text-sm">{formatSector(segment.departure_city, segment.arrival_city, segment.departure_airport, segment.arrival_airport)}</td>
                                      <td className="border p-2 text-sm">{formatDate(customDepTime || segment.departure_time as any) || 'N/A'}</td>
                                      <td className="border p-2 text-sm">{formatDate(customArrTime || segment.arrival_time as any) || 'N/A'}</td>
                                    </tr>
                                  );
                                })}
                              </tbody>
                            </table>
                          ) : (outboundFlight || returnFlight) ? (
                            // One-Way Format - Only Departure (for single flight selection)
                            <table className="w-full border-collapse">
                              <thead>
                                <tr>
                                  <th colSpan={4} className="bg-blue-600 text-white px-4 py-2 text-sm font-semibold text-center">
                                    Departure
                                  </th>
                                </tr>
                                <tr className="bg-gray-100">
                                  <th className="border p-2 text-left text-xs font-semibold">Flight</th>
                                  <th className="border p-2 text-left text-xs font-semibold">Sector</th>
                                  <th className="border p-2 text-left text-xs font-semibold">Departure</th>
                                  <th className="border p-2 text-left text-xs font-semibold">Arrival</th>
                                </tr>
                              </thead>
                              <tbody>
                                <tr>
                                  <td className="border p-2 text-sm">{(outboundFlight || returnFlight)?.flight_number || `${(outboundFlight || returnFlight)?.airline}-${(outboundFlight || returnFlight)?.id}`}</td>
                                  <td className="border p-2 text-sm">{formatSector((outboundFlight || returnFlight)!.departure_city, (outboundFlight || returnFlight)!.arrival_city, (outboundFlight || returnFlight)!.departure_airport, (outboundFlight || returnFlight)!.arrival_airport)}</td>
                                  <td className="border p-2 text-sm">{formatDate(outboundFlight ? (bookingData.outbound_departure_time || outboundFlight.departure_time as any) : (bookingData.return_departure_time || returnFlight?.departure_time as any)) || 'N/A'}</td>
                                  <td className="border p-2 text-sm">{formatDate(outboundFlight ? (bookingData.outbound_arrival_time || outboundFlight.arrival_time as any) : (bookingData.return_arrival_time || returnFlight?.arrival_time as any)) || 'N/A'}</td>
                                </tr>
                              </tbody>
                            </table>
                          ) : null}
                        </div>
                      </div>
                    </div>
                  );
                })()}
                
                {/* Search and Filters */}
                <div className="flex gap-4 mb-6 flex-wrap">
                  <div className="flex-1 min-w-[200px]">
                    <div className="relative">
                      <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                      <Input
                        placeholder="Search by airline or flight number..."
                        value={flightSearchTerm}
                        onChange={(e) => setFlightSearchTerm(e.target.value)}
                        className="pl-9"
                      />
                    </div>
                  </div>
                  <Select value={flightFilterFromCity} onValueChange={setFlightFilterFromCity}>
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
                  <Select value={flightFilterToCity} onValueChange={setFlightFilterToCity}>
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

                {/* One-Way Flights */}
                {organizedFlights.oneWay.length > 0 && (
                  <div className="space-y-4">
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
                      <Label className="text-lg font-semibold">One-Way Flights</Label>
                    </div>
                    {organizedFlights.oneWay.map((flight) => {
                      const isSelected = bookingData.outbound_flight_id === flight.id || bookingData.return_flight_id === flight.id;
                      return (
                        <div key={flight.id} className="space-y-4">
                          <div
                            className={`p-4 border rounded-lg cursor-pointer transition-all ${
                              isSelected ? 'border-primary bg-primary/5 ring-2 ring-primary/20' : 'border-border hover:border-primary/50'
                            }`}
                            onClick={() => {
                              const selectedFlight = flights.find(f => f.id === flight.id);
                              if (isSelected) {
                                // Deselect this flight
                                setBookingData({ 
                                  ...bookingData, 
                                  outbound_flight_id: null,
                                  return_flight_id: null,
                                  outbound_departure_time: '',
                                  outbound_arrival_time: '',
                                  return_departure_time: '',
                                  return_arrival_time: ''
                                });
                              } else {
                                // Select this flight (clear any other selections first)
                                setBookingData({ 
                                  ...bookingData, 
                                  outbound_flight_id: flight.id,
                                  return_flight_id: null,
                                  outbound_departure_time: selectedFlight?.departure_time || '',
                                  outbound_arrival_time: selectedFlight?.arrival_time || '',
                                  return_departure_time: '',
                                  return_arrival_time: ''
                                });
                              }
                            }}
                          >
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-3">
                                <div className={`w-4 h-4 rounded-full border-2 flex items-center justify-center ${
                                  isSelected ? 'border-primary bg-primary' : 'border-muted-foreground'
                                }`}>
                                  {isSelected && <div className="w-2 h-2 rounded-full bg-white" />}
                                </div>
                                <div>
                                  <div className="flex items-center gap-2">
                                    <span className="font-semibold">{flight.airline}</span>
                                    <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                                      One Way
                                    </span>
                                  </div>
                                  <p className="text-sm text-muted-foreground">
                                    {flight.flight_number || 'N/A'} • {
                                      (flight.departure_airport && flight.departure_airport !== 'N/A' && flight.departure_airport.trim() !== '') 
                                        ? flight.departure_airport.toUpperCase() 
                                        : flight.departure_city.substring(0, 3).toUpperCase()
                                    } → {
                                      (flight.arrival_airport && flight.arrival_airport !== 'N/A' && flight.arrival_airport.trim() !== '') 
                                        ? flight.arrival_airport.toUpperCase() 
                                        : flight.arrival_city.substring(0, 3).toUpperCase()
                                    }
                                  </p>
                                  {flight.departure_time && flight.arrival_time && (
                                    <p className="text-xs text-muted-foreground mt-1">
                                      {new Date(flight.departure_time).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })} → {new Date(flight.arrival_time).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}
                                    </p>
                                  )}
                                </div>
                              </div>
                              <div className="text-right">
                                <p className="font-semibold">${Number(flight.sale_price || 0).toFixed(2)}</p>
                                <p className="text-xs text-muted-foreground">Sale Price</p>
                              </div>
                            </div>
                          </div>
                          
                          {isSelected && (
                            <div className="ml-8 space-y-4 border-l-2 border-primary pl-4">
                              <div className="grid grid-cols-2 gap-3">
                                <div>
                                  <Label className="text-xs">Departure Time</Label>
                                  <Input
                                    type="datetime-local"
                                    value={bookingData.outbound_departure_time ? new Date(bookingData.outbound_departure_time).toISOString().slice(0, 16) : ''}
                                    onChange={(e) => {
                                      const dateValue = e.target.value ? new Date(e.target.value).toISOString() : '';
                                      setBookingData({ ...bookingData, outbound_departure_time: dateValue });
                                    }}
                                    placeholder="Select departure time"
                                  />
                                </div>
                                <div>
                                  <Label className="text-xs">Arrival Time</Label>
                                  <Input
                                    type="datetime-local"
                                    value={bookingData.outbound_arrival_time ? new Date(bookingData.outbound_arrival_time).toISOString().slice(0, 16) : ''}
                                    onChange={(e) => {
                                      const dateValue = e.target.value ? new Date(e.target.value).toISOString() : '';
                                      setBookingData({ ...bookingData, outbound_arrival_time: dateValue });
                                    }}
                                    placeholder="Select arrival time"
                                  />
                                </div>
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })}
              </div>
            )}

                {/* Return Flights */}
                {organizedFlights.return.length > 0 && (
                  <div className="space-y-4">
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                      <Label className="text-lg font-semibold">Return Flights</Label>
                    </div>
                    {organizedFlights.return.map((flight) => {
                      const isSelected = bookingData.outbound_flight_id === flight.id || bookingData.return_flight_id === flight.id;
                      
                      return (
                        <div key={flight.id} className="space-y-4">
                          <div
                            className={`p-4 border rounded-lg cursor-pointer transition-all ${
                              isSelected ? 'border-primary bg-primary/5 ring-2 ring-primary/20' : 'border-border hover:border-primary/50'
                            }`}
                            onClick={() => {
                              const selectedFlight = flights.find(f => f.id === flight.id);
                              if (isSelected) {
                                // Deselect this flight
                                setBookingData({ 
                                  ...bookingData, 
                                  outbound_flight_id: null,
                                  return_flight_id: null,
                                  outbound_departure_time: '',
                                  outbound_arrival_time: '',
                                  return_departure_time: '',
                                  return_arrival_time: ''
                                });
                        } else {
                                // Select this flight (clear any other selections first)
                                // For return flights, initialize both departure and return times
                                const isReturnFlight = flight.flight_type === 'return';
                                setBookingData({ 
                                  ...bookingData, 
                                  outbound_flight_id: flight.id,
                                  return_flight_id: null,
                                  outbound_departure_time: selectedFlight?.departure_time || '',
                                  outbound_arrival_time: selectedFlight?.arrival_time || '',
                                  return_departure_time: isReturnFlight ? (selectedFlight?.arrival_time || '') : '',
                                  return_arrival_time: isReturnFlight ? (selectedFlight?.departure_time || '') : ''
                                });
                              }
                            }}
                          >
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-3">
                                <div className={`w-4 h-4 rounded-full border-2 flex items-center justify-center ${
                                  isSelected ? 'border-primary bg-primary' : 'border-muted-foreground'
                                }`}>
                                  {isSelected && <div className="w-2 h-2 rounded-full bg-white" />}
                                </div>
                                <div>
                                  <div className="flex items-center gap-2">
                                    <span className="font-semibold">{flight.airline}</span>
                                    <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                      Return
                                    </span>
                                  </div>
                                  <p className="text-sm text-muted-foreground">
                                    {flight.flight_number || 'N/A'} • {
                                      (flight.departure_airport && flight.departure_airport !== 'N/A' && flight.departure_airport.trim() !== '') 
                                        ? flight.departure_airport.toUpperCase() 
                                        : flight.departure_city.substring(0, 3).toUpperCase()
                                    } → {
                                      (flight.arrival_airport && flight.arrival_airport !== 'N/A' && flight.arrival_airport.trim() !== '') 
                                        ? flight.arrival_airport.toUpperCase() 
                                        : flight.arrival_city.substring(0, 3).toUpperCase()
                                    }
                                  </p>
                                  {flight.departure_time && flight.arrival_time && (
                                    <p className="text-xs text-muted-foreground mt-1">
                                      {new Date(flight.departure_time).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })} → {new Date(flight.arrival_time).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}
                                    </p>
                                  )}
                                </div>
                              </div>
                              <div className="text-right">
                                <p className="font-semibold">${Number(flight.sale_price || 0).toFixed(2)}</p>
                                <p className="text-xs text-muted-foreground">Sale Price</p>
                              </div>
                            </div>
                          </div>
                          
                          {isSelected && flight.flight_type === 'return' && (
                            <div className="ml-8 space-y-4 border-l-2 border-primary pl-4">
                              <div className="space-y-4">
                                <div>
                                  <Label className="text-sm font-medium mb-2 block">Departure (Pakistan to KSA)</Label>
                                  <div className="grid grid-cols-2 gap-3">
                                    <div>
                                      <Label className="text-xs">Departure Time</Label>
                                      <Input
                                        type="datetime-local"
                                        value={bookingData.outbound_departure_time ? new Date(bookingData.outbound_departure_time).toISOString().slice(0, 16) : ''}
                                        onChange={(e) => {
                                          const dateValue = e.target.value ? new Date(e.target.value).toISOString() : '';
                                          setBookingData({ ...bookingData, outbound_departure_time: dateValue });
                                        }}
                                        placeholder="Select departure time"
                                      />
                                    </div>
                                    <div>
                                      <Label className="text-xs">Arrival Time</Label>
                                      <Input
                                        type="datetime-local"
                                        value={bookingData.outbound_arrival_time ? new Date(bookingData.outbound_arrival_time).toISOString().slice(0, 16) : ''}
                                        onChange={(e) => {
                                          const dateValue = e.target.value ? new Date(e.target.value).toISOString() : '';
                                          setBookingData({ ...bookingData, outbound_arrival_time: dateValue });
                                        }}
                                        placeholder="Select arrival time"
                                      />
                                    </div>
                                  </div>
                                </div>
                                <div>
                                  <Label className="text-sm font-medium mb-2 block">Arrival (KSA to PAK)</Label>
                                  <div className="grid grid-cols-2 gap-3">
                                    <div>
                                      <Label className="text-xs">Departure Time</Label>
                                      <Input
                                        type="datetime-local"
                                        value={bookingData.return_departure_time ? new Date(bookingData.return_departure_time).toISOString().slice(0, 16) : ''}
                                        onChange={(e) => {
                                          const dateValue = e.target.value ? new Date(e.target.value).toISOString() : '';
                                          setBookingData({ ...bookingData, return_departure_time: dateValue });
                                        }}
                                        placeholder="Select departure time"
                                      />
                                    </div>
                                    <div>
                                      <Label className="text-xs">Arrival Time</Label>
                                      <Input
                                        type="datetime-local"
                                        value={bookingData.return_arrival_time ? new Date(bookingData.return_arrival_time).toISOString().slice(0, 16) : ''}
                                        onChange={(e) => {
                                          const dateValue = e.target.value ? new Date(e.target.value).toISOString() : '';
                                          setBookingData({ ...bookingData, return_arrival_time: dateValue });
                                        }}
                                        placeholder="Select arrival time"
                                      />
                                    </div>
                                  </div>
                                </div>
                              </div>
                            </div>
                          )}
                          
                          {isSelected && flight.flight_type !== 'return' && (
                            <div className="ml-8 space-y-4 border-l-2 border-primary pl-4">
                              <div className="grid grid-cols-2 gap-3">
                                <div>
                                  <Label className="text-xs">Departure Time</Label>
                                  <Input
                                    type="datetime-local"
                                    value={bookingData.outbound_departure_time ? new Date(bookingData.outbound_departure_time).toISOString().slice(0, 16) : ''}
                                    onChange={(e) => {
                                      const dateValue = e.target.value ? new Date(e.target.value).toISOString() : '';
                                      setBookingData({ ...bookingData, outbound_departure_time: dateValue });
                                    }}
                                    placeholder="Select departure time"
                                  />
                                </div>
                                <div>
                                  <Label className="text-xs">Arrival Time</Label>
                                  <Input
                                    type="datetime-local"
                                    value={bookingData.outbound_arrival_time ? new Date(bookingData.outbound_arrival_time).toISOString().slice(0, 16) : ''}
                                    onChange={(e) => {
                                      const dateValue = e.target.value ? new Date(e.target.value).toISOString() : '';
                                      setBookingData({ ...bookingData, outbound_arrival_time: dateValue });
                                    }}
                                    placeholder="Select arrival time"
                                  />
                                </div>
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* Multi-City Flights */}
                {organizedFlights.multiCity.length > 0 && (
                  <div className="space-y-4">
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 bg-purple-500 rounded-full"></div>
                      <Label className="text-lg font-semibold">Multi-City Flights</Label>
                    </div>
                    {organizedFlights.multiCity.map((flight) => {
                      const isSelected = bookingData.outbound_flight_id === flight.id || bookingData.return_flight_id === flight.id;
                      return (
                        <div key={flight.id} className="space-y-4">
                          <div
                            className={`p-4 border rounded-lg cursor-pointer transition-all ${
                              isSelected ? 'border-primary bg-primary/5 ring-2 ring-primary/20' : 'border-border hover:border-primary/50'
                            }`}
                            onClick={() => {
                              const selectedFlight = flights.find(f => f.id === flight.id);
                              if (isSelected) {
                                // Deselect this flight
                                setBookingData({ 
                                  ...bookingData, 
                                  outbound_flight_id: null,
                                  return_flight_id: null,
                                  outbound_departure_time: '',
                                  outbound_arrival_time: '',
                                  return_departure_time: '',
                                  return_arrival_time: ''
                                });
                        } else {
                                // Select this flight (clear any other selections first)
                                // For multi-city, initialize segment times if needed
                                setBookingData({ 
                                  ...bookingData, 
                                  outbound_flight_id: flight.id,
                                  return_flight_id: null,
                                  outbound_departure_time: selectedFlight?.departure_time || '',
                                  outbound_arrival_time: selectedFlight?.arrival_time || '',
                                  return_departure_time: '',
                                  return_arrival_time: ''
                                });
                              }
                            }}
                          >
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-3">
                                <div className={`w-4 h-4 rounded-full border-2 flex items-center justify-center ${
                                  isSelected ? 'border-primary bg-primary' : 'border-muted-foreground'
                                }`}>
                                  {isSelected && <div className="w-2 h-2 rounded-full bg-white" />}
                                </div>
                                <div>
                                  <div className="flex items-center gap-2">
                                    <span className="font-semibold">{flight.airline}</span>
                                    <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                                      Multi-City
                                    </span>
                                  </div>
                                  <p className="text-sm text-muted-foreground">
                                    {flight.flight_number || 'N/A'} • {
                                      (flight.departure_airport && flight.departure_airport !== 'N/A' && flight.departure_airport.trim() !== '') 
                                        ? flight.departure_airport.toUpperCase() 
                                        : flight.departure_city.substring(0, 3).toUpperCase()
                                    } → {
                                      (flight.arrival_airport && flight.arrival_airport !== 'N/A' && flight.arrival_airport.trim() !== '') 
                                        ? flight.arrival_airport.toUpperCase() 
                                        : flight.arrival_city.substring(0, 3).toUpperCase()
                                    }
                                  </p>
                                  {flight.departure_time && flight.arrival_time && (
                                    <p className="text-xs text-muted-foreground mt-1">
                                      {new Date(flight.departure_time).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })} → {new Date(flight.arrival_time).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}
                                    </p>
                                  )}
                                </div>
                              </div>
                              <div className="text-right">
                                <p className="font-semibold">${Number(flight.sale_price || 0).toFixed(2)}</p>
                                <p className="text-xs text-muted-foreground">Sale Price</p>
                              </div>
                            </div>
                          </div>
                          
                          {isSelected && flight.flight_type === 'multi_city' && flight.segments && flight.segments.length > 0 && (
                            <div className="ml-8 space-y-4 border-l-2 border-primary pl-4">
                              <div className="space-y-4">
                                {flight.segments.sort((a, b) => (a.segment_number || 0) - (b.segment_number || 0)).map((segment, index) => {
                                  const segmentTimeKey = `segment_${flight.id}_${index}_departure_time`;
                                  const segmentArrivalKey = `segment_${flight.id}_${index}_arrival_time`;
                                  const customDepTime = (bookingData as any)[segmentTimeKey];
                                  const customArrTime = (bookingData as any)[segmentArrivalKey];
                                  
                                  return (
                                    <div key={index} className="space-y-2">
                                      <Label className="text-sm font-medium">
                                        Segment {index + 1}: {formatSector(segment.departure_city, segment.arrival_city, segment.departure_airport, segment.arrival_airport)}
                                      </Label>
                                      <div className="grid grid-cols-2 gap-3">
                                        <div>
                                          <Label className="text-xs">Departure Time</Label>
                                          <Input
                                            type="datetime-local"
                                            value={customDepTime ? new Date(customDepTime).toISOString().slice(0, 16) : (segment.departure_time ? new Date(segment.departure_time).toISOString().slice(0, 16) : '')}
                                            onChange={(e) => {
                                              const dateValue = e.target.value ? new Date(e.target.value).toISOString() : '';
                                              setBookingData({ ...bookingData, [segmentTimeKey]: dateValue });
                                            }}
                                            placeholder="Select departure time"
                                          />
                                        </div>
                                        <div>
                                          <Label className="text-xs">Arrival Time</Label>
                                          <Input
                                            type="datetime-local"
                                            value={customArrTime ? new Date(customArrTime).toISOString().slice(0, 16) : (segment.arrival_time ? new Date(segment.arrival_time).toISOString().slice(0, 16) : '')}
                                            onChange={(e) => {
                                              const dateValue = e.target.value ? new Date(e.target.value).toISOString() : '';
                                              setBookingData({ ...bookingData, [segmentArrivalKey]: dateValue });
                                            }}
                                            placeholder="Select arrival time"
                                          />
                                        </div>
                                      </div>
                                    </div>
                                  );
                                })}
                              </div>
                            </div>
                          )}
                          
                          {isSelected && flight.flight_type !== 'multi_city' && flight.flight_type !== 'return' && (
                            <div className="ml-8 space-y-4 border-l-2 border-primary pl-4">
                              <div className="grid grid-cols-2 gap-3">
                                <div>
                                  <Label className="text-xs">Departure Time</Label>
                                  <Input
                                    type="datetime-local"
                                    value={bookingData.outbound_departure_time ? new Date(bookingData.outbound_departure_time).toISOString().slice(0, 16) : ''}
                                    onChange={(e) => {
                                      const dateValue = e.target.value ? new Date(e.target.value).toISOString() : '';
                                      setBookingData({ ...bookingData, outbound_departure_time: dateValue });
                                    }}
                                    placeholder="Select departure time"
                                  />
                                </div>
                                <div>
                                  <Label className="text-xs">Arrival Time</Label>
                                  <Input
                                    type="datetime-local"
                                    value={bookingData.outbound_arrival_time ? new Date(bookingData.outbound_arrival_time).toISOString().slice(0, 16) : ''}
                                    onChange={(e) => {
                                      const dateValue = e.target.value ? new Date(e.target.value).toISOString() : '';
                                      setBookingData({ ...bookingData, outbound_arrival_time: dateValue });
                                    }}
                                    placeholder="Select arrival time"
                                  />
                                </div>
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* No flights found */}
                {filteredFlights.length === 0 && (
                  <div className="text-center text-muted-foreground py-12">
                    <Plane className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p className="text-lg font-medium">No flights found</p>
                    <p className="text-sm">Try adjusting your search criteria or filters</p>
                  </div>
                )}
              </div>
            )}

            {/* Step 4: Choose Transport */}
            {currentStep === 4 && (
              <div className="space-y-8">
                {/* Transport Selection Table */}
                {bookingData.transports.length > 0 && (
                  <div className="space-y-2">
                    <h3 className="text-lg font-semibold bg-gray-700 text-white px-4 py-2 rounded-t">Transport/Services</h3>
                    <div className="border rounded-lg overflow-hidden">
                      <div className="overflow-x-auto">
                        <table className="w-full border-collapse">
                          <thead>
                            <tr className="bg-gray-100">
                              <th className="border p-2 text-left text-xs font-semibold">Travel Date</th>
                              <th className="border p-2 text-left text-xs font-semibold">Transporter</th>
                              <th className="border p-2 text-left text-xs font-semibold">Type</th>
                              <th className="border p-2 text-left text-xs font-semibold">Description</th>
                            </tr>
                          </thead>
                          <tbody>
                            {bookingData.transports.map((transportData) => {
                              const transport = transports.find(t => t.id === transportData.id);
                              if (!transport) return null;
                              
                              return (
                                <tr key={transportData.id}>
                                  <td className="border p-2 text-sm">
                                    {transportData.travel_date || ''}
                                  </td>
                                  <td className="border p-2 text-sm">{transportData.transporter || transport.name}</td>
                                  <td className="border p-2 text-sm">
                                    {transportData.vehicle_type || (transport.transport_type ? transport.transport_type.charAt(0).toUpperCase() + transport.transport_type.slice(1) : '')}
                                  </td>
                                  <td className="border p-2 text-sm">{transportData.description || transport.name || ''}</td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </div>
                )}
                
                <Label>Select Transport Services</Label>
                <div className="grid gap-4">
                  {transports.map((transport) => {
                    const isSelected = bookingData.transports.some(t => t.id === transport.id);
                    const transportData = bookingData.transports.find(t => t.id === transport.id);

                    return (
                    <div
                      key={transport.id}
                        className={`p-4 border rounded-lg ${
                          isSelected ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/50'
                        }`}
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex items-start gap-3">
                      <Checkbox
                              checked={isSelected}
                        onCheckedChange={() => toggleTransportSelection(transport.id)}
                      />
                            <div className="flex-1">
                              <h4 className="font-semibold text-lg mb-1">{transport.name}</h4>
                              <div className="text-sm text-muted-foreground space-y-1">
                                <p><span className="font-medium">Type:</span> {transport.transport_type ? transport.transport_type.charAt(0).toUpperCase() + transport.transport_type.slice(1) : 'N/A'}</p>
                                <p><span className="font-medium">Capacity:</span> {transport.capacity || 'N/A'}</p>
                                <p><span className="font-medium">Price:</span> ${Number(transport.sale_price || 0).toFixed(2)}</p>
                              </div>
                      </div>
                    </div>
                        </div>

                        {isSelected && (
                          <div className="mt-4 space-y-4 pl-8 border-l-2 border-primary">
                            <div className="space-y-3">
                              <div>
                                <Label className="text-xs">Travel Date</Label>
                                <Input
                                  type="date"
                                  value={transportData?.travel_date || ''}
                                  onChange={(e) => updateTransportDetails(transport.id, 'travel_date', e.target.value)}
                                  placeholder="Select travel date"
                                />
                                <p className="text-xs text-muted-foreground mt-2">
                                  Select the date when this transport service will be used
                                </p>
                              </div>
                              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 bg-muted/30 p-3 rounded">
                              <div>
                                  <Label className="text-xs font-medium">Transporter</Label>
                                <Input
                                    value={transportData?.transporter || transport.name}
                                    readOnly
                                    className="bg-muted text-muted-foreground h-10"
                                    placeholder="Transporter name"
                                />
                                  <p className="text-xs text-muted-foreground mt-1">
                                    Fetched from transport page
                                  </p>
                              </div>
                              <div>
                                  <Label className="text-xs font-medium">Type</Label>
                                <Input
                                    value={transportData?.vehicle_type || (transport.transport_type ? transport.transport_type.charAt(0).toUpperCase() + transport.transport_type.slice(1) : '')}
                                    readOnly
                                    className="bg-muted text-muted-foreground h-10"
                                    placeholder="Vehicle type"
                                  />
                                  <p className="text-xs text-muted-foreground mt-1">
                                    Fetched from transport page
                                  </p>
                              </div>
                              <div>
                                  <Label className="text-xs font-medium">Description</Label>
                                <Input
                                    value={transportData?.description || transport.name || ''}
                                    readOnly
                                    className="bg-muted text-muted-foreground h-10"
                                    placeholder="Description"
                                />
                                  <p className="text-xs text-muted-foreground mt-1">
                                    Fetched from transport page
                                  </p>
                                </div>
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Step 5: Add Mutamers */}
            {currentStep === 5 && (
              <div className="space-y-6">
                <div className="flex justify-between items-center">
                  <Label className="text-lg font-semibold">Select Mutamers</Label>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => navigate('/member/mutamers')}
                  >
                    Add New Mutamer
                  </Button>
                </div>

                {/* Selected Mutamers Table */}
                {bookingData.mutamers.length > 0 && (
                  <div className="space-y-2">
                    <h3 className="text-lg font-semibold bg-gray-700 text-white px-4 py-2 rounded-t">Selected Mutamers</h3>
                    <div className="border rounded-lg overflow-hidden">
                      <div className="overflow-x-auto">
                        <table className="w-full border-collapse">
                          <thead>
                            <tr className="bg-gray-100">
                              <th className="border p-2 text-left text-xs font-semibold">SNO</th>
                              <th className="border p-2 text-left text-xs font-semibold">Passport</th>
                              <th className="border p-2 text-left text-xs font-semibold">Mutamer Name</th>
                              <th className="border p-2 text-left text-xs font-semibold">G</th>
                              <th className="border p-2 text-left text-xs font-semibold">PAX</th>
                              <th className="border p-2 text-left text-xs font-semibold">Bed</th>
                              <th className="border p-2 text-left text-xs font-semibold">MOFA #</th>
                              <th className="border p-2 text-left text-xs font-semibold">GRP #</th>
                              <th className="border p-2 text-left text-xs font-semibold">Visa #</th>
                              <th className="border p-2 text-left text-xs font-semibold">PNR</th>
                            </tr>
                          </thead>
                          <tbody>
                            {bookingData.mutamers.map((mutamerId, index) => {
                              const mutamer = mutamers.find(m => m.id === mutamerId);
                              if (!mutamer) return null;
                              
                              // Determine PAX type
                              let paxType = 'Adult';
                              if (mutamer.person_type) {
                                paxType = mutamer.person_type.charAt(0).toUpperCase() + mutamer.person_type.slice(1);
                              } else if (mutamer.age !== undefined && mutamer.age !== null) {
                                if (mutamer.age >= 18) {
                                  paxType = 'Adult';
                                } else if (mutamer.age >= 2) {
                                  paxType = 'Child';
                                } else {
                                  paxType = 'Infant';
                                }
                              }
                              
                              // Determine if bed is needed: Only if hotels are selected AND (Adults/Children need beds, Infants don't)
                              const hasHotels = bookingData.hotels.length > 0;
                              const needsBed = hasHotels && paxType !== 'Infant';
                              
                              return (
                                <tr key={mutamerId}>
                                  <td className="border p-2 text-sm">{index + 1}</td>
                                  <td className="border p-2 text-sm">{mutamer.passport_number}</td>
                                  <td className="border p-2 text-sm font-medium">{mutamer.name}</td>
                                  <td className="border p-2 text-sm">{mutamer.gender ? mutamer.gender.charAt(0).toUpperCase() : 'N/A'}</td>
                                  <td className="border p-2 text-sm">{paxType}</td>
                                  <td className="border p-2 text-sm">{needsBed ? 'Yes' : 'No'}</td>
                                  <td className="border p-2 text-sm">—</td>
                                  <td className="border p-2 text-sm">0</td>
                                  <td className="border p-2 text-sm">{mutamer.visa_number || '—'}</td>
                                  <td className="border p-2 text-sm">—</td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </div>
                )}

                {(() => {
                  // Group mutamers by family
                  const families: Record<string, Mutamer[]> = {};
                  const individuals: Mutamer[] = [];

                  mutamers.filter(m => m.is_active !== false).forEach((mutamer) => {
                    if (mutamer.family_id) {
                      if (!families[mutamer.family_id]) {
                        families[mutamer.family_id] = [];
                      }
                      families[mutamer.family_id].push(mutamer);
                    } else {
                      individuals.push(mutamer);
                    }
                  });

                  // Sort family members - head first
                  Object.keys(families).forEach(familyId => {
                    families[familyId].sort((a, b) => {
                      if (a.is_family_head) return -1;
                      if (b.is_family_head) return 1;
                      return 0;
                    });
                  });

                  return (
                    <div className="space-y-6">
                      {/* Family Groups */}
                      {Object.keys(families).length > 0 && (
                        <div className="space-y-4">
                          <h3 className="text-md font-semibold text-muted-foreground uppercase tracking-wide border-b pb-2">
                            Families ({Object.keys(families).length})
                          </h3>
                          {Object.entries(families).map(([familyId, familyMembers]) => {
                            const familyHead = familyMembers.find(m => m.is_family_head);
                            const familyHeadName = familyHead?.name || familyMembers[0]?.family_head_name || 'Family';
                            const allSelected = familyMembers.every(m => bookingData.mutamers.includes(m.id));
                            const someSelected = familyMembers.some(m => bookingData.mutamers.includes(m.id));

                            return (
                              <div
                                key={familyId}
                                className={`border-2 rounded-lg overflow-hidden ${
                                  allSelected ? 'border-primary bg-primary/5' : someSelected ? 'border-primary/50 bg-primary/5' : 'border-border'
                                }`}
                              >
                                {/* Family Header */}
                                <div className="bg-muted/50 p-4 border-b">
                                  <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-3">
                                      <Checkbox
                                        checked={allSelected}
                                        onCheckedChange={(checked) => {
                                          if (checked) {
                                            // Select all family members
                                            const newMutamerIds = [...new Set([...bookingData.mutamers, ...familyMembers.map(m => m.id)])];
                                            setBookingData({ ...bookingData, mutamers: newMutamerIds });
                                          } else {
                                            // Deselect all family members
                                            const newMutamerIds = bookingData.mutamers.filter(id => !familyMembers.some(m => m.id === id));
                                            setBookingData({ ...bookingData, mutamers: newMutamerIds });
                                          }
                                        }}
                                      />
                                      <div>
                                        <h4 className="font-semibold text-lg flex items-center gap-2">
                                          {familyHeadName}
                                          <span className="text-xs font-normal text-muted-foreground">
                                            ({familyMembers.length} {familyMembers.length === 1 ? 'member' : 'members'})
                                          </span>
                                        </h4>
                                        {familyHead && (
                                          <p className="text-sm text-muted-foreground">
                                            Head: {familyHead.name} • {familyHead.passport_number}
                                          </p>
                                        )}
                                      </div>
                                    </div>
                                    <div className="text-sm text-muted-foreground">
                                      {familyMembers.filter(m => bookingData.mutamers.includes(m.id)).length} / {familyMembers.length} selected
                                    </div>
                                  </div>
                                </div>

                                {/* Family Members */}
                                <div className="p-4 space-y-3 bg-background">
                                  {familyMembers.map((mutamer) => (
                                    <div
                                      key={mutamer.id}
                                      className={`p-3 border rounded-lg flex items-center gap-3 ${
                                        bookingData.mutamers.includes(mutamer.id)
                                          ? 'border-primary bg-primary/5'
                                          : 'border-border hover:border-primary/30'
                                      }`}
                                    >
                                      <Checkbox
                                        checked={bookingData.mutamers.includes(mutamer.id)}
                                        onCheckedChange={() => toggleMutamerSelection(mutamer.id)}
                                      />
                                      <div className="flex-1">
                                        <div className="flex items-center gap-2 mb-1">
                                          <h4 className="font-semibold">{mutamer.name}</h4>
                                          {mutamer.is_family_head && (
                                            <span className="px-2 py-0.5 bg-blue-100 text-blue-800 text-xs rounded-full font-medium">
                                              Head
                                            </span>
                                          )}
                                          {mutamer.person_type && (
                                            <span className="px-2 py-0.5 bg-gray-100 text-gray-700 text-xs rounded-full">
                                              {mutamer.person_type.charAt(0).toUpperCase() + mutamer.person_type.slice(1)}
                                            </span>
                                          )}
                                        </div>
                                        <div className="text-sm text-muted-foreground space-y-0.5">
                                          <p>Passport: {mutamer.passport_number}</p>
                                          <p>Nationality: {mutamer.nationality} • Gender: {mutamer.gender ? mutamer.gender.charAt(0).toUpperCase() + mutamer.gender.slice(1) : 'N/A'}</p>
                                          {mutamer.visa_number && (
                                            <p>Visa: {mutamer.visa_number}</p>
                                          )}
                                        </div>
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      )}

                      {/* Individual Mutamers */}
                      {individuals.length > 0 && (
                        <div className="space-y-4">
                          <h3 className="text-md font-semibold text-muted-foreground uppercase tracking-wide border-b pb-2">
                            Individual Mutamers ({individuals.length})
                          </h3>
                <div className="grid gap-3">
                            {individuals.map((mutamer) => (
                    <div
                      key={mutamer.id}
                      className={`p-4 border rounded-lg flex items-center gap-3 ${
                        bookingData.mutamers.includes(mutamer.id)
                          ? 'border-primary bg-primary/5'
                                    : 'border-border hover:border-primary/30'
                      }`}
                    >
                      <Checkbox
                        checked={bookingData.mutamers.includes(mutamer.id)}
                        onCheckedChange={() => toggleMutamerSelection(mutamer.id)}
                      />
                      <div className="flex-1">
                                  <div className="flex items-center gap-2 mb-1">
                                    <h4 className="font-semibold">{mutamer.name}</h4>
                                    {mutamer.person_type && (
                                      <span className="px-2 py-0.5 bg-gray-100 text-gray-700 text-xs rounded-full">
                                        {mutamer.person_type.charAt(0).toUpperCase() + mutamer.person_type.slice(1)}
                                      </span>
                                    )}
                                  </div>
                                  <div className="text-sm text-muted-foreground space-y-0.5">
                                    <p>Passport: {mutamer.passport_number}</p>
                                    <p>Nationality: {mutamer.nationality} • Gender: {mutamer.gender ? mutamer.gender.charAt(0).toUpperCase() + mutamer.gender.slice(1) : 'N/A'}</p>
                                    {mutamer.visa_number && (
                                      <p>Visa: {mutamer.visa_number}</p>
                          )}
                                  </div>
                      </div>
                    </div>
                  ))}
                </div>
                        </div>
                      )}

                      {/* No Mutamers */}
                      {Object.keys(families).length === 0 && individuals.length === 0 && (
                        <div className="text-center py-12 border-2 border-dashed rounded-lg">
                          <p className="text-muted-foreground mb-2">No mutamers available</p>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => navigate('/member/mutamers')}
                          >
                            Add New Mutamer
                          </Button>
                        </div>
                      )}
                    </div>
                  );
                })()}
              </div>
            )}

            {/* Step 6: Team Contacts */}
            {currentStep === 6 && (
              <div className="space-y-6">
                <Label className="text-lg font-semibold">Team Contacts</Label>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* Makkah Team */}
                  {(() => {
                    const makkahTeamContacts = contacts.filter(c => {
                      const cityLower = (c.city || '').toLowerCase().trim();
                      return cityLower === 'makkah';
                    });

                    return (
                      <div className="space-y-2">
                        <h3 className="text-lg font-bold bg-blue-600 text-white px-4 py-2">
                          MAKKAH TEAM
                        </h3>
                        <div className="bg-white p-4 space-y-1 border rounded-lg border-t-0 rounded-t-none">
                          {makkahTeamContacts.length === 0 ? (
                            <div className="text-sm text-muted-foreground text-center py-4">
                              No Makkah contacts available
                            </div>
                          ) : (
                            makkahTeamContacts.map((contact) => (
                              <div key={contact.id} className="text-sm">
                                <span className="font-bold">{contact.role.toUpperCase()}:</span>{' '}
                                <span className="font-medium">{contact.contact_name},</span>{' '}
                                <span className="text-muted-foreground">Phone: {contact.phone_number}</span>
                              </div>
                            ))
                          )}
                        </div>
                      </div>
                    );
                  })()}

                  {/* Medina Team */}
                  {(() => {
                    const medinaTeamContacts = contacts.filter(c => {
                      const cityLower = (c.city || '').toLowerCase().trim();
                      return cityLower === 'medina' || cityLower === 'madina';
                    });

                    return (
                      <div className="space-y-2">
                        <h3 className="text-lg font-bold bg-green-600 text-white px-4 py-2">
                          MEDINA TEAM
                        </h3>
                        <div className="bg-white p-4 space-y-1 border rounded-lg border-t-0 rounded-t-none">
                          {medinaTeamContacts.length === 0 ? (
                            <div className="text-sm text-muted-foreground text-center py-4">
                              No Medina contacts available
                            </div>
                          ) : (
                            medinaTeamContacts.map((contact) => (
                              <div key={contact.id} className="text-sm">
                                <span className="font-bold">{contact.role.toUpperCase()}:</span>{' '}
                                <span className="font-medium">{contact.contact_name},</span>{' '}
                                <span className="text-muted-foreground">Phone: {contact.phone_number}</span>
                              </div>
                            ))
                          )}
                        </div>
                      </div>
                    );
                  })()}
                </div>
              </div>
            )}

            {/* Step 7: Review & Summary */}
            {currentStep === 7 && (
              <div className="space-y-6">
                <div className="bg-gradient-to-r from-primary/10 to-primary/5 p-6 rounded-lg">
                  <h3 className="text-2xl font-bold mb-2">Booking Summary</h3>
                  <p className="text-muted-foreground">Review all details before confirming</p>
                </div>

                {/* Agency Information */}
                {agencyBranding && (
                  <div className="p-4 border rounded-lg bg-muted/30">
                    <h4 className="font-semibold flex items-center gap-2 mb-3">
                      <Building className="h-4 w-4" />
                      Travel Agency Details
                    </h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="flex items-center gap-3">
                        {agencyBranding.logo_url && (
                          <img
                            src={agencyBranding.logo_url}
                            alt="Agency Logo"
                            className="w-16 h-16 object-contain rounded-lg border"
                          />
                        )}
                        <div>
                          <p className="font-medium text-lg">{agencyBranding.company_name}</p>
                          <p className="text-sm text-muted-foreground">{agencyBranding.address}</p>
                        </div>
                      </div>
                      <div className="space-y-1 text-sm">
                        <p><span className="font-medium">Phone:</span> {agencyBranding.phone}</p>
                        <p><span className="font-medium">Email:</span> {agencyBranding.email}</p>
                        {agencyBranding.website && (
                          <p><span className="font-medium">Website:</span> {agencyBranding.website}</p>
                        )}
                      </div>
                    </div>
                  </div>
                )}

                <div className="grid gap-4">

                  {/* Hotels */}
                  {bookingData.hotels.length > 0 && (
                    <div className="p-4 border rounded-lg">
                      <h4 className="font-semibold flex items-center gap-2 mb-4">
                        <Hotel className="h-4 w-4" />
                        Accommodation ({bookingData.hotels.length})
                      </h4>
                      <div className="overflow-x-auto">
                        <table className="w-full border-collapse">
                          <thead>
                            <tr className="bg-gray-100">
                              <th className="border p-2 text-left text-xs font-semibold">City</th>
                              <th className="border p-2 text-left text-xs font-semibold">Hotel Name</th>
                              <th className="border p-2 text-left text-xs font-semibold">Rating</th>
                              <th className="border p-2 text-left text-xs font-semibold">Room Type</th>
                              <th className="border p-2 text-left text-xs font-semibold">Check-in</th>
                              <th className="border p-2 text-left text-xs font-semibold">Check-out</th>
                              <th className="border p-2 text-left text-xs font-semibold">Nights</th>
                              <th className="border p-2 text-left text-xs font-semibold">Meal</th>
                            </tr>
                          </thead>
                          <tbody>
                            {bookingData.hotels.map((hotel) => {
                              const h = hotels.find((ht) => ht.id === hotel.id);
                              if (!h) return null;
                              const roomTypeLabel = ROOM_TYPES.find(rt => rt.value === hotel.room_type)?.label || 'Sharing';
                              const formatDate = (dateStr: string) => {
                                if (!dateStr) return '';
                                const date = new Date(dateStr);
                                const day = String(date.getDate()).padStart(2, '0');
                                const month = String(date.getMonth() + 1).padStart(2, '0');
                                const year = String(date.getFullYear()).slice(-2);
                                return `${day}-${month}-${year}`;
                              };
                              const nights = hotel.nights || calculateNights(hotel.check_in || '', hotel.check_out || '');
                              return (
                                <tr key={hotel.id}>
                                  <td className="border p-2 text-sm">{h.city}</td>
                                  <td className="border p-2 text-sm">{h.name}</td>
                                  <td className="border p-2 text-sm">{h.rating}★</td>
                                  <td className="border p-2 text-sm">{roomTypeLabel}</td>
                                  <td className="border p-2 text-sm">{formatDate(hotel.check_in || '')}</td>
                                  <td className="border p-2 text-sm">{formatDate(hotel.check_out || '')}</td>
                                  <td className="border p-2 text-sm">{nights}</td>
                                  <td className="border p-2 text-sm">{hotel.meal || 'N/A'}</td>
                                </tr>
                              );
                            })}
                            <tr className="bg-gray-50">
                              <td colSpan={7} className="border p-2 text-sm font-semibold text-right">Total Nights:</td>
                              <td className="border p-2 text-sm font-semibold">
                                {bookingData.hotels.reduce((total, hotel) => {
                                  const nights = hotel.nights || calculateNights(hotel.check_in || '', hotel.check_out || '');
                                  return total + nights;
                                }, 0)}
                              </td>
                            </tr>
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {/* Flights */}
                  {(bookingData.outbound_flight_id || bookingData.return_flight_id) && (
                    <div className="p-4 border rounded-lg">
                      <h4 className="font-semibold flex items-center gap-2 mb-2">
                        <Plane className="h-4 w-4" />
                        Flights
                      </h4>
                      {selectedFlights.length > 0 ? (
                        <div className="overflow-x-auto">
                          <table className="w-full border-collapse">
                            <thead>
                              <tr className="bg-gray-100">
                                <th className="border p-2 text-left text-xs font-semibold">Journey</th>
                                <th className="border p-2 text-left text-xs font-semibold">Flight Type</th>
                                <th className="border p-2 text-left text-xs font-semibold">Airline</th>
                                <th className="border p-2 text-left text-xs font-semibold">Flight No.</th>
                                <th className="border p-2 text-left text-xs font-semibold">Route</th>
                                <th className="border p-2 text-right text-xs font-semibold">Sale Price</th>
                              </tr>
                            </thead>
                            <tbody>
                              {selectedFlights.map(({ key, label, flight }) => (
                                <tr key={key}>
                                  <td className="border p-2 text-sm">
                                    <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-primary/10 text-primary">
                                      {label}
                                    </span>
                                  </td>
                                  <td className="border p-2 text-sm">
                                    <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getFlightTypeBadgeClasses(flight.flight_type)}`}>
                                      {getFlightTypeLabel(flight.flight_type)}
                                    </span>
                                  </td>
                                  <td className="border p-2 text-sm font-medium">{flight.airline}</td>
                                  <td className="border p-2 text-sm">{flight.flight_number || 'N/A'}</td>
                                  <td className="border p-2 text-sm">
                                    {flight.departure_city} → {flight.arrival_city}
                                  </td>
                                  <td className="border p-2 text-sm text-right">{formatCurrency(flight.sale_price)}</td>
                                </tr>
                              ))}
                            </tbody>
                            <tfoot>
                              <tr className="bg-gray-50">
                                <td colSpan={5} className="border p-2 text-sm font-semibold text-right">
                                  Total Sale Price:
                                </td>
                                <td className="border p-2 text-sm font-semibold text-right">
                                  {formatCurrency(totalFlightSalePrice)}
                                </td>
                              </tr>
                            </tfoot>
                          </table>
                        </div>
                      ) : (
                        <div className="text-sm text-muted-foreground">
                          Selected flight details are not available. Please verify the selection.
                        </div>
                      )}
                    </div>
                  )}

                  {/* Transports */}
                  {bookingData.transports.length > 0 && (
                    <div className="p-4 border rounded-lg">
                      <h4 className="font-semibold flex items-center gap-2 mb-4">
                        <Car className="h-4 w-4" />
                        Transport/Services ({bookingData.transports.length})
                      </h4>
                      <div className="overflow-x-auto">
                        <table className="w-full border-collapse">
                          <thead>
                            <tr className="bg-gray-100">
                              <th className="border p-2 text-left text-xs font-semibold">Travel Date</th>
                              <th className="border p-2 text-left text-xs font-semibold">Transporter</th>
                              <th className="border p-2 text-left text-xs font-semibold">Type</th>
                              <th className="border p-2 text-left text-xs font-semibold">Description</th>
                            </tr>
                          </thead>
                          <tbody>
                            {bookingData.transports.map((transportData) => {
                              const transport = transports.find(t => t.id === transportData.id);
                              if (!transport) return null;
                              return (
                                <tr key={transportData.id}>
                                  <td className="border p-2 text-sm">{transportData.travel_date || ''}</td>
                                  <td className="border p-2 text-sm">{transportData.transporter || transport.name}</td>
                                  <td className="border p-2 text-sm">
                                    {transportData.vehicle_type || (transport.transport_type ? transport.transport_type.charAt(0).toUpperCase() + transport.transport_type.slice(1) : '')}
                                  </td>
                                  <td className="border p-2 text-sm">{transportData.description || transport.name || ''}</td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {/* Mutamers */}
                  {bookingData.mutamers.length > 0 && (
                    <div className="p-4 border rounded-lg">
                      <h4 className="font-semibold flex items-center gap-2 mb-4">
                        <Users className="h-4 w-4" />
                        Mutamers ({bookingData.mutamers.length})
                      </h4>
                      {(() => {
                        const familyHead = mutamers.find(m => bookingData.mutamers.includes(m.id) && m.is_family_head);
                        if (familyHead) {
                          return (
                      <div className="mb-3 p-2 bg-blue-50 rounded-lg">
                        <p className="text-sm font-medium text-blue-800">
                                Family Head: {familyHead.name}
                        </p>
                      </div>
                          );
                        }
                        return null;
                      })()}
                      <div className="overflow-x-auto">
                        <table className="w-full border-collapse text-sm">
                          <thead>
                            <tr className="bg-gray-100">
                              <th className="border p-2 text-left text-xs font-semibold">SNO</th>
                              <th className="border p-2 text-left text-xs font-semibold">Passport</th>
                              <th className="border p-2 text-left text-xs font-semibold">Mutamer Name</th>
                              <th className="border p-2 text-left text-xs font-semibold">G</th>
                              <th className="border p-2 text-left text-xs font-semibold">PAX</th>
                              <th className="border p-2 text-left text-xs font-semibold">Bed</th>
                              <th className="border p-2 text-left text-xs font-semibold">MOFA #</th>
                              <th className="border p-2 text-left text-xs font-semibold">GRP #</th>
                              <th className="border p-2 text-left text-xs font-semibold">Visa #</th>
                              <th className="border p-2 text-left text-xs font-semibold">PNR</th>
                            </tr>
                          </thead>
                          <tbody>
                            {bookingData.mutamers.map((mId, index) => {
                        const m = mutamers.find((mt) => mt.id === mId);
                              if (!m) return null;
                              
                              // Determine PAX type
                              let paxType = 'Adult';
                              if (m.person_type) {
                                paxType = m.person_type.charAt(0).toUpperCase() + m.person_type.slice(1);
                              } else if (m.age !== undefined && m.age !== null) {
                                if (m.age >= 18) {
                                  paxType = 'Adult';
                                } else if (m.age >= 2) {
                                  paxType = 'Child';
                                } else {
                                  paxType = 'Infant';
                                }
                              }
                              
                              // Determine if bed is needed: Only if hotels are selected AND (Adults/Children need beds, Infants don't)
                              const hasHotels = bookingData.hotels.length > 0;
                              const needsBed = hasHotels && paxType !== 'Infant';
                              
                        return (
                                <tr key={mId}>
                                  <td className="border p-2">{index + 1}</td>
                                  <td className="border p-2">{m.passport_number}</td>
                                  <td className="border p-2 font-medium">
                                    {m.name}
                                    {m.is_family_head && (
                                      <span className="ml-2 px-2 py-0.5 bg-blue-100 text-blue-800 text-xs rounded-full font-medium">
                                  Head
                                </span>
                              )}
                                  </td>
                                  <td className="border p-2">{m.gender ? m.gender.charAt(0).toUpperCase() : 'N/A'}</td>
                                  <td className="border p-2">{paxType}</td>
                                  <td className="border p-2">{needsBed ? 'Yes' : 'No'}</td>
                                  <td className="border p-2">—</td>
                                  <td className="border p-2">0</td>
                                  <td className="border p-2">{m.visa_number || '—'}</td>
                                  <td className="border p-2">—</td>
                                </tr>
                        );
                      })}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {/* Team Contacts */}
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    {/* Makkah Team */}
                    {(() => {
                      const makkahTeamContacts = contacts.filter(c => {
                        const cityLower = (c.city || '').toLowerCase().trim();
                        return cityLower === 'makkah';
                      });

                      if (makkahTeamContacts.length === 0) return null;

                      return (
                        <div className="p-4 border rounded-lg">
                          <h4 className="font-semibold flex items-center gap-2 mb-3">
                            <Users className="h-4 w-4" />
                            Makkah Team
                          </h4>
                          <div className="space-y-1 text-sm">
                            {makkahTeamContacts.map((contact) => (
                              <div key={contact.id}>
                                <span className="font-bold">{contact.role.toUpperCase()}:</span>{' '}
                                <span className="font-medium">{contact.contact_name},</span>{' '}
                                <span className="text-muted-foreground">Phone: {contact.phone_number}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      );
                    })()}

                    {/* Medina Team */}
                    {(() => {
                      const medinaTeamContacts = contacts.filter(c => {
                        const cityLower = (c.city || '').toLowerCase().trim();
                        return cityLower === 'medina' || cityLower === 'madina';
                      });

                      if (medinaTeamContacts.length === 0) return null;

                      return (
                        <div className="p-4 border rounded-lg">
                          <h4 className="font-semibold flex items-center gap-2 mb-3">
                            <Users className="h-4 w-4" />
                            Medina Team
                          </h4>
                          <div className="space-y-1 text-sm">
                            {medinaTeamContacts.map((contact) => (
                              <div key={contact.id}>
                                <span className="font-bold">{contact.role.toUpperCase()}:</span>{' '}
                                <span className="font-medium">{contact.contact_name},</span>{' '}
                                <span className="text-muted-foreground">Phone: {contact.phone_number}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      );
                    })()}
                  </div>

                  {/* Total Price */}
                  <div className="p-6 bg-primary/10 rounded-lg">
                    <div className="flex justify-between items-center">
                      <span className="text-lg font-semibold">Total Price</span>
                      <span className="text-2xl font-bold text-primary">
                        ${calculateTotalPrice().toFixed(2)}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Navigation Buttons */}
        <div className="flex justify-between">
          <Button
            variant="outline"
            onClick={handlePrevious}
            disabled={currentStep === 1}
            className="gap-2"
          >
            <ArrowLeft className="h-4 w-4" />
            Previous
          </Button>

          {currentStep < 7 ? (
            <Button onClick={handleNext} className="gap-2">
              Next
              <ArrowRight className="h-4 w-4" />
            </Button>
          ) : (
            <Button onClick={handleFinish} disabled={loading} className="gap-2">
              {loading ? 'Creating...' : 'Finish & Generate Voucher'}
              <Check className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}