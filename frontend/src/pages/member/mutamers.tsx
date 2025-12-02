import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
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
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet';
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { toast } from '@/hooks/use-toast';
import { Plus, Search, Edit, Trash2, Users, Eye, ChevronDown, ChevronUp } from 'lucide-react';
import apiClient from '@/api/client';

interface Mutamer {
  id: number;
  name: string;
  passport_number: string;
  visa_number?: string;
  nationality: string;
  gender: string;
  person_type?: string;
  date_of_birth?: string;
  phone: string;
  email: string;
  emergency_contact?: string;
  emergency_phone?: string;
  address?: string;
  city: string;
  state: string;
  country: string;
  postal_code?: string;
  notes?: string;
  age?: number;
  is_active: boolean;
  agency_name?: string;
  agent_name?: string;
  family_id?: string;
  is_family_head: boolean;
  family_head_name?: string;
  created_at: string;
  updated_at: string;
}

interface MutamerFormData {
  name: string;
  passport_number: string;
  visa_number: string;
  nationality: string;
  gender: string;
  date_of_birth: string;
  phone: string;
  email: string;
  emergency_contact: string;
  emergency_phone: string;
  address: string;
  city: string;
  state: string;
  country: string;
  postal_code: string;
  notes: string;
  family_id?: string;
  is_family_head: boolean;
  family_head_name?: string;
  person_type?: string; // UI-only: adult | child | infant
}

interface FamilyMember {
  name: string;
  passport_number: string;
  visa_number: string;
  nationality: string;
  gender: string;
  date_of_birth: string;
  phone: string;
  email: string;
  emergency_contact: string;
  emergency_phone: string;
  address: string;
  city: string;
  state: string;
  country: string;
  postal_code: string;
  notes: string;
  is_family_head: boolean;
  person_type?: string; // UI-only: adult | child | infant
}

const defaultFormData: MutamerFormData = {
  name: '',
  passport_number: '',
  visa_number: '',
  nationality: '',
  gender: '',
  date_of_birth: '',
  phone: '',
  email: '',
  emergency_contact: '',
  emergency_phone: '',
  address: '',
  city: '',
  state: '',
  country: '',
  postal_code: '',
  notes: '',
  family_id: '',
  is_family_head: false,
  family_head_name: '',
  person_type: '',
};

export default function MemberMutamers() {
  const [mutamers, setMutamers] = useState<Mutamer[]>([]);
  const [filteredMutamers, setFilteredMutamers] = useState<Mutamer[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterNationality, setFilterNationality] = useState('all');
  const [filterGender, setFilterGender] = useState('all');
  
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [isBulkAddOpen, setIsBulkAddOpen] = useState(false);
  const [editingMutamer, setEditingMutamer] = useState<Mutamer | null>(null);
  const [formData, setFormData] = useState<MutamerFormData>(defaultFormData);
  const [familyMembers, setFamilyMembers] = useState<FamilyMember[]>([]);
  const [currentFamilyId, setCurrentFamilyId] = useState<string>('');
  
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [mutamerToDelete, setMutamerToDelete] = useState<Mutamer | null>(null);
  const [selectedMutamer, setSelectedMutamer] = useState<Mutamer | null>(null);
  const [detailSheetOpen, setDetailSheetOpen] = useState(false);
  const [expandedFamilies, setExpandedFamilies] = useState<Set<string>>(new Set());
  const [addToFamilyDialogOpen, setAddToFamilyDialogOpen] = useState(false);
  const [selectedFamilyId, setSelectedFamilyId] = useState<string>('');
  const [selectedFamilyHeadName, setSelectedFamilyHeadName] = useState<string>('');
  const [deleteFamilyDialogOpen, setDeleteFamilyDialogOpen] = useState(false);
  const [familyToDelete, setFamilyToDelete] = useState<{id: string, name: string, memberCount: number} | null>(null);

  // Fetch mutamers
  const fetchMutamers = async () => {
    try {
      setLoading(true);
      const response = await apiClient.get('/api/v1/mutamers/mutamers/');
      // Handle both array response and paginated response
      const mutamersData = Array.isArray(response.data) ? response.data : response.data.results || [];
      setMutamers(mutamersData);
      setFilteredMutamers(mutamersData);
    } catch (error) {
      console.error('Failed to fetch mutamers:', error);
      toast({
        title: 'Error',
        description: 'Failed to load mutamers',
        variant: 'destructive',
      });
      setMutamers([]); // Set empty array on error
      setFilteredMutamers([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMutamers();
  }, []);

  // Apply filters
  useEffect(() => {
    let filtered = [...mutamers];

    // Search filter
    if (searchTerm) {
      const query = searchTerm.toLowerCase();
      filtered = filtered.filter(
        (m) =>
          (m.name && m.name.toLowerCase().includes(query)) ||
          m.passport_number.toLowerCase().includes(query) ||
          (m.visa_number && m.visa_number.toLowerCase().includes(query)) ||
          (m.phone && m.phone.toLowerCase().includes(query)) ||
          (m.email && m.email.toLowerCase().includes(query))
      );
    }

    // Nationality filter
    if (filterNationality !== 'all') {
      filtered = filtered.filter((m) => m.nationality === filterNationality);
    }

    // Gender filter
    if (filterGender !== 'all') {
      filtered = filtered.filter((m) => m.gender === filterGender);
    }

    setFilteredMutamers(filtered);
  }, [searchTerm, filterNationality, filterGender, mutamers]);

  const uniqueNationalities = Array.from(new Set(mutamers.map(m => m.nationality))).sort();
  const uniqueGenders = Array.from(new Set(mutamers.map(m => m.gender))).sort();

  // Generate unique family ID
  const generateFamilyId = () => {
    return `FAM_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  };

  // Add new family member to the list
  const addFamilyMember = () => {
    const newMember: FamilyMember = {
      name: '',
      passport_number: '',
      visa_number: '',
      nationality: '',
      gender: '',
      date_of_birth: '',
      phone: '',
      email: '',
      emergency_contact: '',
      emergency_phone: '',
      address: '',
      city: '',
      state: '',
      country: '',
      postal_code: '',
      notes: '',
      is_family_head: false,
      person_type: '',
    };
    setFamilyMembers([...familyMembers, newMember]);
  };

  // Remove family member from the list
  const removeFamilyMember = (index: number) => {
    setFamilyMembers(familyMembers.filter((_, i) => i !== index));
  };

  // Update family member data
  const updateFamilyMember = (index: number, field: keyof FamilyMember, value: string | boolean) => {
    const updatedMembers = [...familyMembers];
    updatedMembers[index] = { ...updatedMembers[index], [field]: value };
    
    // If setting as family head, unset all others
    if (field === 'is_family_head' && value === true) {
      updatedMembers.forEach((member, i) => {
        if (i !== index) {
          member.is_family_head = false;
        }
      });
    }
    
    setFamilyMembers(updatedMembers);
  };

  // Handle form open for add/edit
  const handleOpenForm = (mutamer?: Mutamer) => {
    if (mutamer) {
      setEditingMutamer(mutamer);
      setFormData({
        name: mutamer.name || '',
        passport_number: mutamer.passport_number,
        visa_number: mutamer.visa_number || '',
        nationality: mutamer.nationality,
        gender: mutamer.gender,
        date_of_birth: mutamer.date_of_birth || '',
        phone: mutamer.phone || '',
        email: mutamer.email || '',
        emergency_contact: mutamer.emergency_contact || '',
        emergency_phone: mutamer.emergency_phone || '',
        address: mutamer.address || '',
        city: mutamer.city || '',
        state: mutamer.state || '',
        country: mutamer.country || '',
        postal_code: mutamer.postal_code || '',
        notes: mutamer.notes || '',
        person_type: (mutamer as any).person_type || '',
      });
    } else {
      setEditingMutamer(null);
      setFormData(defaultFormData);
    }
    setIsFormOpen(true);
  };

  // Handle form close
  const handleCloseForm = () => {
    setIsFormOpen(false);
    setEditingMutamer(null);
    setFormData(defaultFormData);
  };

  // Handle bulk add form open
  const handleOpenBulkAdd = () => {
    setCurrentFamilyId(generateFamilyId());
    // Reset family members and add first member
    const newMember: FamilyMember = {
      name: '',
      passport_number: '',
      visa_number: '',
      nationality: '',
      gender: '',
      date_of_birth: '',
      phone: '',
      email: '',
      emergency_contact: '',
      emergency_phone: '',
      address: '',
      city: '',
      state: '',
      country: '',
      postal_code: '',
      notes: '',
      is_family_head: false,
    };
    setFamilyMembers([newMember]);
    setIsBulkAddOpen(true);
  };

  // Handle bulk add form close
  const handleCloseBulkAdd = () => {
    setIsBulkAddOpen(false);
    setFamilyMembers([]);
    setCurrentFamilyId('');
  };

  // Handle bulk add submit
  const handleBulkAddSubmit = async () => {
    try {
      // Validate that at least one family head is selected
      const hasFamilyHead = familyMembers.some(member => member.is_family_head);
      if (!hasFamilyHead) {
        toast({
          title: 'Validation Error',
          description: 'Please select a family head',
          variant: 'destructive',
        });
        return;
      }

      // Validate all required fields for all members
      for (let i = 0; i < familyMembers.length; i++) {
        const member = familyMembers[i];
        if (!member.name || !member.passport_number || !member.nationality || !member.gender) {
          toast({
            title: 'Validation Error',
            description: `Please fill in all required fields for member ${i + 1}`,
            variant: 'destructive',
          });
          return;
        }
      }

      // Get family head name
      const familyHead = familyMembers.find(member => member.is_family_head);
      const familyHeadName = familyHead?.name || '';

      // Submit all family members sequentially to avoid race conditions with passport number validation
      const results = [];
      for (let i = 0; i < familyMembers.length; i++) {
        const member = familyMembers[i];
        
        // Clean up form data - ensure all required fields are present and format properly
        const cleanedData: any = {
          name: member.name.trim(),
          passport_number: member.passport_number.trim(),
          nationality: member.nationality.trim(),
          gender: member.gender,
          person_type: member.person_type || '',
          visa_number: member.visa_number?.trim() || '',
          phone: member.phone?.trim() || '',
          email: member.email?.trim() || '',
          emergency_contact: member.emergency_contact?.trim() || '',
          emergency_phone: member.emergency_phone?.trim() || '',
          address: member.address?.trim() || '',
          city: member.city?.trim() || '',
          state: member.state?.trim() || '',
          country: member.country?.trim() || '',
          postal_code: member.postal_code?.trim() || '',
          notes: member.notes?.trim() || '',
          family_id: currentFamilyId,
          is_family_head: member.is_family_head,
          family_head_name: familyHeadName,
          is_active: true,
        };

        // Handle date_of_birth: only include if it's a valid non-empty string
        if (member.date_of_birth && member.date_of_birth.trim()) {
          cleanedData.date_of_birth = member.date_of_birth.trim();
        }

        try {
          const response = await apiClient.post('/api/v1/mutamers/mutamers/', cleanedData);
          results.push(response);
        } catch (error: any) {
          // Extract error message from response
          let errorMessage = 'Validation failed';
          
          if (error.response?.data) {
            const errorData = error.response.data;
            
            // Handle Django REST Framework validation errors
            if (typeof errorData === 'object') {
              // Get first error message if multiple fields have errors
              const firstError = Object.values(errorData)[0];
              if (Array.isArray(firstError)) {
                errorMessage = firstError[0];
              } else if (typeof firstError === 'string') {
                errorMessage = firstError;
              } else {
                // Try to stringify non-primitive error objects
                errorMessage = JSON.stringify(errorData);
              }
            } else if (typeof errorData === 'string') {
              errorMessage = errorData;
            }
          } else if (error.message) {
            errorMessage = error.message;
          }
          
          console.error(`Error saving family member ${i + 1}:`, error);
          console.error('Error details:', error.response?.data);
          
          toast({
            title: 'Error',
            description: `Failed to save member ${i + 1} (${member.name || 'Unnamed'}): ${errorMessage}`,
            variant: 'destructive',
          });
          
          // Stop processing remaining members if one fails
          throw error;
        }
      }
      
      toast({
        title: 'Success',
        description: `${familyMembers.length} family members added successfully`,
      });
      
      fetchMutamers();
      handleCloseBulkAdd();
    } catch (error: any) {
      // Error is already handled in the loop above
      console.error('Error saving family:', error);
    }
  };

  // Handle form submit
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Validation
    if (!formData.name || !formData.passport_number || !formData.nationality || !formData.gender) {
      toast({
        title: 'Validation Error',
        description: 'Please fill in all required fields',
        variant: 'destructive',
      });
      return;
    }

    // Check for duplicate passport number (only for new mutamers)
    if (!editingMutamer) {
      const existingMutamer = mutamers.find(m => m.passport_number === formData.passport_number);
      if (existingMutamer) {
        toast({
          title: 'Validation Error',
          description: 'A mutamer with this passport number already exists',
          variant: 'destructive',
        });
        return;
      }
    }

    try {
      // Clean up form data - ensure all required fields are present
      const cleanedData = {
        name: formData.name,
        passport_number: formData.passport_number,
        nationality: formData.nationality,
        gender: formData.gender,
        person_type: formData.person_type || '',
        visa_number: formData.visa_number || '',
        date_of_birth: formData.date_of_birth || '',
        phone: formData.phone || '',
        email: formData.email || '',
        emergency_contact: formData.emergency_contact || '',
        emergency_phone: formData.emergency_phone || '',
        address: formData.address || '',
        city: formData.city || '',
        state: formData.state || '',
        country: formData.country || '',
        postal_code: formData.postal_code || '',
        notes: formData.notes || '',
        is_active: true,
      };

      if (editingMutamer) {
        await apiClient.put(`/api/v1/mutamers/mutamers/${editingMutamer.id}/`, cleanedData);
        toast({
          title: 'Success',
          description: 'Mutamer updated successfully',
        });
      } else {
        await apiClient.post('/api/v1/mutamers/mutamers/', cleanedData);
        toast({
          title: 'Success',
          description: 'Mutamer added successfully',
        });
      }
      fetchMutamers();
      handleCloseForm();
    } catch (error: any) {
      console.error('Error saving mutamer:', error);
      
      // Handle validation errors from the API
      let errorMessage = 'Failed to save mutamer';
      
      if (error.response?.data) {
        const errorData = error.response.data;
        
        // Handle field-specific validation errors
        if (typeof errorData === 'object') {
          const fieldErrors = [];
          for (const [field, messages] of Object.entries(errorData)) {
            if (Array.isArray(messages)) {
              fieldErrors.push(`${field}: ${messages.join(', ')}`);
            } else {
              fieldErrors.push(`${field}: ${messages}`);
            }
          }
          if (fieldErrors.length > 0) {
            errorMessage = fieldErrors.join('; ');
          }
        } else if (typeof errorData === 'string') {
          errorMessage = errorData;
        }
      } else {
        errorMessage = error.message || 'Failed to save mutamer';
      }
      
      toast({
        title: 'Validation Error',
        description: errorMessage,
        variant: 'destructive',
      });
    }
  };

  // Handle delete
  const handleDelete = async () => {
    if (!mutamerToDelete) return;

    try {
      await apiClient.delete(`/api/v1/mutamers/mutamers/${mutamerToDelete.id}/`);
      toast({
        title: 'Success',
        description: 'Mutamer deleted successfully',
      });
      fetchMutamers();
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to delete mutamer',
        variant: 'destructive',
      });
    } finally {
      setDeleteDialogOpen(false);
      setMutamerToDelete(null);
    }
  };

  // Open delete confirmation
  const openDeleteDialog = (mutamer: Mutamer) => {
    setMutamerToDelete(mutamer);
    setDeleteDialogOpen(true);
  };

  // Open detail view
  const openDetailView = (mutamer: Mutamer) => {
    setSelectedMutamer(mutamer);
    setDetailSheetOpen(true);
  };

  // Toggle family expansion
  const toggleFamilyExpansion = (familyId: string) => {
    const newExpanded = new Set(expandedFamilies);
    if (newExpanded.has(familyId)) {
      newExpanded.delete(familyId);
    } else {
      newExpanded.add(familyId);
    }
    setExpandedFamilies(newExpanded);
  };

  // Group mutamers by family
  const groupMutamersByFamily = () => {
    const families: Record<string, Mutamer[]> = {};
    const individuals: Mutamer[] = [];

    filteredMutamers.forEach((mutamer) => {
      if (mutamer.family_id) {
        if (!families[mutamer.family_id]) {
          families[mutamer.family_id] = [];
        }
        families[mutamer.family_id].push(mutamer);
      } else {
        individuals.push(mutamer);
      }
    });

    return { families, individuals };
  };

  // Handle adding member to existing family
  const handleAddToExistingFamily = (familyId: string, familyHeadName: string) => {
    setSelectedFamilyId(familyId);
    setSelectedFamilyHeadName(familyHeadName);
    // Reset family members and add first member
    const newMember: FamilyMember = {
      name: '',
      passport_number: '',
      visa_number: '',
      nationality: '',
      gender: '',
      date_of_birth: '',
      phone: '',
      email: '',
      emergency_contact: '',
      emergency_phone: '',
      address: '',
      city: '',
      state: '',
      country: '',
      postal_code: '',
      notes: '',
      is_family_head: false,
    };
    setFamilyMembers([newMember]);
    setAddToFamilyDialogOpen(true);
  };

  // Handle close add to family dialog
  const handleCloseAddToFamily = () => {
    setAddToFamilyDialogOpen(false);
    setFamilyMembers([]);
    setSelectedFamilyId('');
    setSelectedFamilyHeadName('');
  };

  // Handle delete family dialog open
  const openDeleteFamilyDialog = (familyId: string, familyName: string, memberCount: number) => {
    setFamilyToDelete({ id: familyId, name: familyName, memberCount });
    setDeleteFamilyDialogOpen(true);
  };

  // Handle delete family
  const handleDeleteFamily = async () => {
    if (!familyToDelete) return;

    try {
      // Get all mutamers in this family
      const familyMutamers = mutamers.filter(m => m.family_id === familyToDelete.id);
      
      // Delete all mutamers in the family
      const deletePromises = familyMutamers.map(mutamer => 
        apiClient.delete(`/api/v1/mutamers/mutamers/${mutamer.id}/`)
      );

      await Promise.all(deletePromises);

      toast({
        title: 'Success',
        description: `Family "${familyToDelete.name}" and all ${familyToDelete.memberCount} members deleted successfully`,
      });

      // Refresh the mutamers list
      fetchMutamers();
      setDeleteFamilyDialogOpen(false);
      setFamilyToDelete(null);
    } catch (error: any) {
      console.error('Error deleting family:', error);
      toast({
        title: 'Error',
        description: 'Failed to delete family. Please try again.',
        variant: 'destructive',
      });
    }
  };

  // Handle submit add to existing family
  const handleAddToFamilySubmit = async () => {
    try {
      // Validate all required fields for all members
      for (let i = 0; i < familyMembers.length; i++) {
        const member = familyMembers[i];
        if (!member.name || !member.passport_number || !member.nationality || !member.gender) {
          toast({
            title: 'Validation Error',
            description: `Please fill in all required fields for member ${i + 1}`,
            variant: 'destructive',
          });
          return;
        }
      }

      // For existing families, use the existing family head name
      const familyHeadName = selectedFamilyHeadName;

      // Submit all family members
      const results = [];
      for (let i = 0; i < familyMembers.length; i++) {
        const member = familyMembers[i];
        
        // Clean up form data - ensure all required fields are present and format properly
        const cleanedData: any = {
          name: member.name.trim(),
          passport_number: member.passport_number.trim(),
          nationality: member.nationality.trim(),
          gender: member.gender,
          person_type: member.person_type || '',
          visa_number: member.visa_number?.trim() || '',
          phone: member.phone?.trim() || '',
          email: member.email?.trim() || '',
          emergency_contact: member.emergency_contact?.trim() || '',
          emergency_phone: member.emergency_phone?.trim() || '',
          address: member.address?.trim() || '',
          city: member.city?.trim() || '',
          state: member.state?.trim() || '',
          country: member.country?.trim() || '',
          postal_code: member.postal_code?.trim() || '',
          notes: member.notes?.trim() || '',
          family_id: selectedFamilyId,
          is_family_head: false, // New members added to existing family are never family heads
          family_head_name: familyHeadName,
          is_active: true,
        };

        // Handle date_of_birth: only include if it's a valid non-empty string
        if (member.date_of_birth && member.date_of_birth.trim()) {
          cleanedData.date_of_birth = member.date_of_birth.trim();
        }

        try {
          const response = await apiClient.post('/api/v1/mutamers/mutamers/', cleanedData);
          results.push(response);
        } catch (error: any) {
          // Extract error message from response
          let errorMessage = 'Validation failed';
          
          if (error.response?.data) {
            const errorData = error.response.data;
            
            // Handle Django REST Framework validation errors
            if (typeof errorData === 'object') {
              // Get first error message if multiple fields have errors
              const firstError = Object.values(errorData)[0];
              if (Array.isArray(firstError)) {
                errorMessage = firstError[0];
              } else if (typeof firstError === 'string') {
                errorMessage = firstError;
              } else {
                // Try to stringify non-primitive error objects
                errorMessage = JSON.stringify(errorData);
              }
            } else if (typeof errorData === 'string') {
              errorMessage = errorData;
            }
          } else if (error.message) {
            errorMessage = error.message;
          }
          
          console.error(`Error saving family member ${i + 1}:`, error);
          console.error('Error details:', error.response?.data);
          
          toast({
            title: 'Error',
            description: `Failed to save member ${i + 1} (${member.name || 'Unnamed'}): ${errorMessage}`,
            variant: 'destructive',
          });
          
          // Stop processing remaining members if one fails
          throw error;
        }
      }
      
      toast({
        title: 'Success',
        description: `${familyMembers.length} member(s) added to family successfully`,
      });
      
      fetchMutamers();
      handleCloseAddToFamily();
    } catch (error: any) {
      // Error is already handled in the loop above
      console.error('Error adding to family:', error);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Mutamers</h1>
          <p className="text-muted-foreground">Manage pilgrims and participants</p>
        </div>
        <div className="flex gap-3">
          <Button onClick={() => handleOpenForm()} className="gap-2 bg-primary hover:bg-primary/90">
            <Plus className="h-4 w-4" />
            Add Individual Mutamer
          </Button>
          <Button onClick={handleOpenBulkAdd} variant="outline" className="gap-2 border-primary text-primary hover:bg-primary hover:text-primary-foreground">
            <Users className="h-4 w-4" />
            Add Family Group
          </Button>
        </div>
      </div>

      {/* Action Description Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <Card className="border-l-4 border-l-blue-500">
          <CardContent className="pt-4">
            <div className="flex items-start gap-3">
              <div className="p-2 bg-blue-100 rounded-lg">
                <Plus className="h-5 w-5 text-blue-600" />
              </div>
              <div>
                <h3 className="font-semibold text-sm text-foreground">Individual Mutamer</h3>
                <p className="text-xs text-muted-foreground mt-1">
                  Add a single mutamer with complete personal details and travel information.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card className="border-l-4 border-l-green-500">
          <CardContent className="pt-4">
            <div className="flex items-start gap-3">
              <div className="p-2 bg-green-100 rounded-lg">
                <Users className="h-5 w-5 text-green-600" />
              </div>
              <div>
                <h3 className="font-semibold text-sm text-foreground">Family Group</h3>
                <p className="text-xs text-muted-foreground mt-1">
                  Add multiple family members at once. Perfect for group bookings and family travel.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="h-5 w-5" />
            All Mutamers ({filteredMutamers.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4 mb-6 flex-wrap">
            <div className="flex-1 min-w-[200px]">
              <div className="relative">
                <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search by name, passport, or phone..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-9"
                />
              </div>
            </div>
            <Select value={filterNationality} onValueChange={setFilterNationality}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Filter by Nationality" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Nationalities</SelectItem>
                {uniqueNationalities.map((nationality) => (
                  <SelectItem key={nationality} value={nationality}>
                    {nationality}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={filterGender} onValueChange={setFilterGender}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Filter by Gender" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Genders</SelectItem>
                {uniqueGenders.map((gender) => (
                  <SelectItem key={gender} value={gender}>
                    {gender.charAt(0).toUpperCase() + gender.slice(1)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Mutamers Display */}
          {loading ? (
            <div className="text-center py-8 text-muted-foreground">Loading...</div>
          ) : filteredMutamers.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              No mutamers found. Add your first mutamer to get started.
            </div>
          ) : (
            <div className="space-y-4">
              {(() => {
                const { families, individuals } = groupMutamersByFamily();
                
                return (
                  <>
                    {/* Family Groups */}
                    {Object.entries(families).map(([familyId, familyMembers]) => {
                      const familyHead = familyMembers.find(m => m.is_family_head) || familyMembers[0];
                      const isExpanded = expandedFamilies.has(familyId);
                      
                      return (
                        <Card key={familyId} className="overflow-hidden">
                          <CardHeader 
                            className="cursor-pointer hover:bg-muted/50 transition-colors"
                            onClick={() => toggleFamilyExpansion(familyId)}
                          >
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-3">
                                <div className="p-2 bg-primary/10 rounded-lg">
                                  <Users className="h-5 w-5 text-primary" />
                                </div>
                                <div>
                                  <CardTitle className="text-lg flex items-center gap-2">
                                    {familyHead.family_head_name || 'Family Group'}
                                    <span className="text-sm font-normal text-muted-foreground">
                                      ({familyMembers.length} {familyMembers.length === 1 ? 'member' : 'members'})
                                    </span>
                                  </CardTitle>
                                  <p className="text-xs text-muted-foreground mt-1 font-mono">
                                    {familyId}
                                  </p>
                                </div>
                              </div>
                              <div className="flex items-center gap-2">
                                <Button 
                                  variant="outline" 
                                  size="sm"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleAddToExistingFamily(familyId, familyHead.family_head_name || '');
                                  }}
                                  className="text-xs"
                                >
                                  <Plus className="h-3 w-3 mr-1" />
                                  Add Member
                                </Button>
                                <Button 
                                  variant="outline" 
                                  size="sm"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    openDeleteFamilyDialog(familyId, familyHead.family_head_name || 'Family Group', familyMembers.length);
                                  }}
                                  className="text-xs text-destructive hover:text-destructive hover:bg-destructive/10"
                                >
                                  <Trash2 className="h-3 w-3 mr-1" />
                                  Delete Family
                                </Button>
                                <Button variant="ghost" size="sm">
                                  {isExpanded ? (
                                    <ChevronUp className="h-4 w-4" />
                                  ) : (
                                    <ChevronDown className="h-4 w-4" />
                                  )}
                                </Button>
                              </div>
                            </div>
                          </CardHeader>
                          
                          {isExpanded && (
                            <CardContent className="pt-0">
                              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                {familyMembers.map((mutamer) => (
                                  <Card key={mutamer.id} className="border-2 hover:border-primary/50 transition-colors">
                                    <CardContent className="pt-4">
                                      <div className="flex items-start justify-between mb-3">
                                        <div className="flex-1">
                                          <div className="flex items-center gap-2 mb-1">
                                            <h4 className="font-semibold text-sm">{mutamer.name}</h4>
                        {mutamer.is_family_head && (
                                              <span className="px-2 py-0.5 bg-blue-100 text-blue-800 text-xs rounded-full font-medium">
                            Head
                          </span>
                        )}
                          </div>
                                          <div className="space-y-1 text-xs text-muted-foreground">
                                            <div className="flex items-center gap-2">
                                              <span className="font-medium">Passport:</span>
                                              <span>{mutamer.passport_number}</span>
                                            </div>
                                            <div className="flex items-center gap-2">
                                              <span className="font-medium">Nationality:</span>
                                              <span>{mutamer.nationality}</span>
                                            </div>
                                            <div className="flex items-center gap-2">
                                              <span className="font-medium">Gender:</span>
                                              <span className="capitalize">{mutamer.gender}</span>
                                            </div>
                                          </div>
                                        </div>
                                      </div>
                                      <div className="flex gap-1 pt-3 border-t">
                                        <Button
                                          variant="ghost"
                                          size="sm"
                                          className="h-7 px-2"
                                          onClick={(e) => {
                                            e.stopPropagation();
                                            openDetailView(mutamer);
                                          }}
                                        >
                                          <Eye className="h-3.5 w-3.5" />
                                        </Button>
                                        <Button
                                          variant="ghost"
                                          size="sm"
                                          className="h-7 px-2"
                                          onClick={(e) => {
                                            e.stopPropagation();
                                            handleOpenForm(mutamer);
                                          }}
                                        >
                                          <Edit className="h-3.5 w-3.5" />
                                        </Button>
                                        <Button
                                          variant="ghost"
                                          size="sm"
                                          className="h-7 px-2 text-destructive hover:text-destructive"
                                          onClick={(e) => {
                                            e.stopPropagation();
                                            openDeleteDialog(mutamer);
                                          }}
                                        >
                                          <Trash2 className="h-3.5 w-3.5" />
                                        </Button>
                                      </div>
                                    </CardContent>
                                  </Card>
                                ))}
                              </div>
                            </CardContent>
                          )}
                        </Card>
                      );
                    })}

                    {/* Individual Mutamers */}
                    {individuals.length > 0 && (
                      <div className="space-y-2">
                        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide px-2">
                          Individual Mutamers ({individuals.length})
                        </h3>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                          {individuals.map((mutamer) => (
                            <Card key={mutamer.id} className="border-2 hover:border-primary/50 transition-colors">
                              <CardContent className="pt-4">
                                <div className="flex items-start justify-between mb-3">
                                  <div className="flex-1">
                                    <h4 className="font-semibold text-sm mb-1">{mutamer.name}</h4>
                                    <div className="space-y-1 text-xs text-muted-foreground">
                                      <div className="flex items-center gap-2">
                                        <span className="font-medium">Passport:</span>
                                        <span>{mutamer.passport_number}</span>
                                      </div>
                                      <div className="flex items-center gap-2">
                                        <span className="font-medium">Nationality:</span>
                                        <span>{mutamer.nationality}</span>
                                      </div>
                                      <div className="flex items-center gap-2">
                                        <span className="font-medium">Gender:</span>
                                        <span className="capitalize">{mutamer.gender}</span>
                                      </div>
                                    </div>
                                  </div>
                                </div>
                                <div className="flex gap-1 pt-3 border-t">
                          <Button
                            variant="ghost"
                            size="sm"
                                    className="h-7 px-2"
                            onClick={() => openDetailView(mutamer)}
                          >
                                    <Eye className="h-3.5 w-3.5" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                                    className="h-7 px-2"
                            onClick={() => handleOpenForm(mutamer)}
                          >
                                    <Edit className="h-3.5 w-3.5" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                                    className="h-7 px-2 text-destructive hover:text-destructive"
                            onClick={() => openDeleteDialog(mutamer)}
                          >
                                    <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                              </CardContent>
                            </Card>
                          ))}
                        </div>
                      </div>
                    )}
                  </>
                );
              })()}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Add/Edit Dialog */}
      <Dialog open={isFormOpen} onOpenChange={setIsFormOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingMutamer ? 'Edit Mutamer' : 'Add Individual Mutamer'}</DialogTitle>
            <DialogDescription>
              {editingMutamer
                ? 'Update mutamer details below'
                : 'Enter individual mutamer details to add to your agency'}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit}>
            <div className="grid gap-4 py-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="name">Full Name *</Label>
                  <Input
                    id="name"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="Enter full name"
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="passport_number">Passport Number *</Label>
                  <Input
                    id="passport_number"
                    value={formData.passport_number}
                    onChange={(e) => setFormData({ ...formData, passport_number: e.target.value })}
                    placeholder="Enter passport number"
                    required
                    className={!editingMutamer && formData.passport_number && mutamers.find(m => m.passport_number === formData.passport_number) ? 'border-red-500' : ''}
                  />
                  {!editingMutamer && formData.passport_number && mutamers.find(m => m.passport_number === formData.passport_number) && (
                    <p className="text-sm text-red-500">This passport number is already in use</p>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="visa_number">Visa Number</Label>
                  <Input
                    id="visa_number"
                    value={formData.visa_number}
                    onChange={(e) => setFormData({ ...formData, visa_number: e.target.value })}
                    placeholder="Enter visa number (optional)"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="nationality">Nationality *</Label>
                  <Input
                    id="nationality"
                    value={formData.nationality}
                    onChange={(e) => setFormData({ ...formData, nationality: e.target.value })}
                    placeholder="Enter nationality"
                    required
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="gender">Gender *</Label>
                  <Select
                    value={formData.gender}
                    onValueChange={(value) => setFormData({ ...formData, gender: value })}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select gender" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="male">Male</SelectItem>
                      <SelectItem value="female">Female</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="person_type">Category</Label>
                  <Select
                    value={formData.person_type || ''}
                    onValueChange={(value) => setFormData({ ...formData, person_type: value })}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select category" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="adult">Adult</SelectItem>
                      <SelectItem value="child">Child</SelectItem>
                      <SelectItem value="infant">Infant</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="date_of_birth">Date of Birth</Label>
                <Input
                  id="date_of_birth"
                  type="date"
                  value={formData.date_of_birth}
                  onChange={(e) => setFormData({ ...formData, date_of_birth: e.target.value })}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="phone">Phone Number</Label>
                  <Input
                    id="phone"
                    type="tel"
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
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="emergency_contact">Emergency Contact</Label>
                  <Input
                    id="emergency_contact"
                    value={formData.emergency_contact}
                    onChange={(e) => setFormData({ ...formData, emergency_contact: e.target.value })}
                    placeholder="Enter emergency contact name"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="emergency_phone">Emergency Phone</Label>
                  <Input
                    id="emergency_phone"
                    type="tel"
                    value={formData.emergency_phone}
                    onChange={(e) => setFormData({ ...formData, emergency_phone: e.target.value })}
                    placeholder="Enter emergency phone number"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="address">Address</Label>
                <Input
                  id="address"
                  value={formData.address}
                  onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                  placeholder="Enter full address"
                />
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="city">City</Label>
                  <Input
                    id="city"
                    value={formData.city}
                    onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                    placeholder="Enter city"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="state">State</Label>
                  <Input
                    id="state"
                    value={formData.state}
                    onChange={(e) => setFormData({ ...formData, state: e.target.value })}
                    placeholder="Enter state"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="country">Country</Label>
                  <Input
                    id="country"
                    value={formData.country}
                    onChange={(e) => setFormData({ ...formData, country: e.target.value })}
                    placeholder="Enter country"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="postal_code">Postal Code</Label>
                <Input
                  id="postal_code"
                  value={formData.postal_code}
                  onChange={(e) => setFormData({ ...formData, postal_code: e.target.value })}
                  placeholder="Enter postal code"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="notes">Notes</Label>
                <Input
                  id="notes"
                  value={formData.notes}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                  placeholder="Enter any additional notes"
                />
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={handleCloseForm}>
                Cancel
              </Button>
              <Button type="submit">{editingMutamer ? 'Update' : 'Add'} Mutamer</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Mutamer</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete "{mutamerToDelete?.name}"? This action cannot be
              undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setMutamerToDelete(null)}>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete} className="bg-destructive text-destructive-foreground">
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Delete Family Confirmation Dialog */}
      <AlertDialog open={deleteFamilyDialogOpen} onOpenChange={setDeleteFamilyDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Entire Family</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete the entire family "{familyToDelete?.name}"? 
              This will permanently delete all {familyToDelete?.memberCount} family members and cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setFamilyToDelete(null)}>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDeleteFamily} className="bg-destructive text-destructive-foreground">
              Delete Family ({familyToDelete?.memberCount} members)
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Detail Sheet */}
      <Sheet open={detailSheetOpen} onOpenChange={setDetailSheetOpen}>
        <SheetContent className="overflow-y-auto">
          <SheetHeader>
            <SheetTitle>Mutamer Details</SheetTitle>
          </SheetHeader>
          {selectedMutamer && (
            <div className="space-y-6 py-6">
              <div className="space-y-4">
                <div>
                  <Label className="text-muted-foreground">Name</Label>
                  <p className="text-lg font-semibold">{selectedMutamer.name || 'N/A'}</p>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label className="text-muted-foreground">Passport Number</Label>
                    <p className="font-medium">{selectedMutamer.passport_number}</p>
                  </div>
                  <div>
                    <Label className="text-muted-foreground">Visa Number</Label>
                    <p className="font-medium">{selectedMutamer.visa_number || 'N/A'}</p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label className="text-muted-foreground">Nationality</Label>
                    <p className="font-medium">{selectedMutamer.nationality}</p>
                  </div>
                  <div>
                    <Label className="text-muted-foreground">Gender</Label>
                    <p className="font-medium">{selectedMutamer.gender}</p>
                  </div>
                </div>

                <div className="grid grid-cols-1 gap-4">
                  <div>
                    <Label className="text-muted-foreground">Category</Label>
                    <p className="font-medium capitalize">{selectedMutamer.person_type || 'N/A'}</p>
                  </div>
                </div>

                <div className="grid grid-cols-1 gap-4">
                  <div>
                    <Label className="text-muted-foreground">Age</Label>
                    <p className="font-medium">{selectedMutamer.age || 'N/A'}</p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label className="text-muted-foreground">Phone</Label>
                    <p className="font-medium">{selectedMutamer.phone || 'N/A'}</p>
                  </div>
                  <div>
                    <Label className="text-muted-foreground">Email</Label>
                    <p className="font-medium">{selectedMutamer.email || 'N/A'}</p>
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <Label className="text-muted-foreground">City</Label>
                    <p className="font-medium">{selectedMutamer.city || 'N/A'}</p>
                  </div>
                  <div>
                    <Label className="text-muted-foreground">State</Label>
                    <p className="font-medium">{selectedMutamer.state || 'N/A'}</p>
                  </div>
                  <div>
                    <Label className="text-muted-foreground">Country</Label>
                    <p className="font-medium">{selectedMutamer.country || 'N/A'}</p>
                  </div>
                </div>

              </div>

              <div className="pt-4 border-t space-y-2">
                {selectedMutamer.agent_name && (
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Agent:</span>
                    <span className="font-medium">{selectedMutamer.agent_name}</span>
                  </div>
                )}
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Created:</span>
                  <span className="font-medium">{new Date(selectedMutamer.created_at).toLocaleDateString()}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Last Updated:</span>
                  <span className="font-medium">{new Date(selectedMutamer.updated_at).toLocaleDateString()}</span>
                </div>
              </div>
            </div>
          )}
        </SheetContent>
      </Sheet>

      {/* Bulk Add Family Dialog */}
      <Dialog open={isBulkAddOpen} onOpenChange={setIsBulkAddOpen}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Add Family Group</DialogTitle>
            <DialogDescription>
              Add multiple family members at once. You can add one or more members to create a family group. Select one member as the family head.
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-6 py-4">
            <div className="flex justify-between items-center">
              <h3 className="text-lg font-semibold">Family Members ({familyMembers.length})</h3>
              <Button onClick={addFamilyMember} variant="outline" size="sm">
                <Plus className="h-4 w-4 mr-2" />
                Add Member
              </Button>
            </div>

            {familyMembers.map((member, index) => (
              <Card key={index} className="p-4">
                <div className="flex justify-between items-center mb-4">
                  <h4 className="font-medium">Member {index + 1}</h4>
                  <div className="flex gap-2">
                    <Checkbox
                      checked={member.is_family_head}
                      onCheckedChange={(checked) => updateFamilyMember(index, 'is_family_head', checked as boolean)}
                    />
                    <Label className="text-sm">Family Head</Label>
                    {familyMembers.length > 1 && (
                      <Button
                        onClick={() => removeFamilyMember(index)}
                        variant="ghost"
                        size="sm"
                        className="text-red-600 hover:text-red-700"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor={`name-${index}`}>Name *</Label>
                    <Input
                      id={`name-${index}`}
                      value={member.name}
                      onChange={(e) => updateFamilyMember(index, 'name', e.target.value)}
                      placeholder="Full name"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor={`passport-${index}`}>Passport Number *</Label>
                    <Input
                      id={`passport-${index}`}
                      value={member.passport_number}
                      onChange={(e) => updateFamilyMember(index, 'passport_number', e.target.value)}
                      placeholder="Passport number"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor={`visa-${index}`}>Visa Number</Label>
                    <Input
                      id={`visa-${index}`}
                      value={member.visa_number}
                      onChange={(e) => updateFamilyMember(index, 'visa_number', e.target.value)}
                      placeholder="Visa number"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor={`nationality-${index}`}>Nationality *</Label>
                    <Input
                      id={`nationality-${index}`}
                      value={member.nationality}
                      onChange={(e) => updateFamilyMember(index, 'nationality', e.target.value)}
                      placeholder="Nationality"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor={`gender-${index}`}>Gender *</Label>
                    <Select
                      value={member.gender}
                      onValueChange={(value) => updateFamilyMember(index, 'gender', value)}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select gender" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="male">Male</SelectItem>
                        <SelectItem value="female">Female</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor={`person-type-${index}`}>Category</Label>
                    <Select
                      value={member.person_type || ''}
                      onValueChange={(value) => updateFamilyMember(index, 'person_type', value)}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select category" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="adult">Adult</SelectItem>
                        <SelectItem value="child">Child</SelectItem>
                        <SelectItem value="infant">Infant</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor={`dob-${index}`}>Date of Birth</Label>
                    <Input
                      id={`dob-${index}`}
                      type="date"
                      value={member.date_of_birth}
                      onChange={(e) => updateFamilyMember(index, 'date_of_birth', e.target.value)}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor={`phone-${index}`}>Phone</Label>
                    <Input
                      id={`phone-${index}`}
                      value={member.phone}
                      onChange={(e) => updateFamilyMember(index, 'phone', e.target.value)}
                      placeholder="Phone number"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor={`email-${index}`}>Email</Label>
                    <Input
                      id={`email-${index}`}
                      type="email"
                      value={member.email}
                      onChange={(e) => updateFamilyMember(index, 'email', e.target.value)}
                      placeholder="Email address"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor={`emergency-contact-${index}`}>Emergency Contact</Label>
                    <Input
                      id={`emergency-contact-${index}`}
                      value={member.emergency_contact}
                      onChange={(e) => updateFamilyMember(index, 'emergency_contact', e.target.value)}
                      placeholder="Emergency contact name"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor={`emergency-phone-${index}`}>Emergency Phone</Label>
                    <Input
                      id={`emergency-phone-${index}`}
                      value={member.emergency_phone}
                      onChange={(e) => updateFamilyMember(index, 'emergency_phone', e.target.value)}
                      placeholder="Emergency phone number"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor={`address-${index}`}>Address</Label>
                    <Input
                      id={`address-${index}`}
                      value={member.address}
                      onChange={(e) => updateFamilyMember(index, 'address', e.target.value)}
                      placeholder="Full address"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor={`city-${index}`}>City</Label>
                    <Input
                      id={`city-${index}`}
                      value={member.city}
                      onChange={(e) => updateFamilyMember(index, 'city', e.target.value)}
                      placeholder="City"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor={`state-${index}`}>State</Label>
                    <Input
                      id={`state-${index}`}
                      value={member.state}
                      onChange={(e) => updateFamilyMember(index, 'state', e.target.value)}
                      placeholder="State"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor={`country-${index}`}>Country</Label>
                    <Input
                      id={`country-${index}`}
                      value={member.country}
                      onChange={(e) => updateFamilyMember(index, 'country', e.target.value)}
                      placeholder="Country"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor={`postal-${index}`}>Postal Code</Label>
                    <Input
                      id={`postal-${index}`}
                      value={member.postal_code}
                      onChange={(e) => updateFamilyMember(index, 'postal_code', e.target.value)}
                      placeholder="Postal code"
                    />
                  </div>

                  <div className="space-y-2 md:col-span-2">
                    <Label htmlFor={`notes-${index}`}>Notes</Label>
                    <Input
                      id={`notes-${index}`}
                      value={member.notes}
                      onChange={(e) => updateFamilyMember(index, 'notes', e.target.value)}
                      placeholder="Additional notes"
                    />
                  </div>
                </div>
              </Card>
            ))}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={handleCloseBulkAdd}>
              Cancel
            </Button>
            <Button onClick={handleBulkAddSubmit}>
              Add Family Group ({familyMembers.length} members)
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Add Member to Existing Family Dialog */}
      <Dialog open={addToFamilyDialogOpen} onOpenChange={setAddToFamilyDialogOpen}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Add Members to Family</DialogTitle>
            <DialogDescription>
              Add new members to the existing family "{selectedFamilyHeadName}". You can add one or more members.
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-6 py-4">
            <div className="flex justify-between items-center">
              <h3 className="text-lg font-semibold">New Family Members ({familyMembers.length})</h3>
              <Button onClick={addFamilyMember} size="sm" className="gap-2">
                <Plus className="h-4 w-4" />
                Add Member
              </Button>
            </div>

            {familyMembers.map((member, index) => (
              <Card key={index} className="p-4">
                <div className="flex justify-between items-center mb-4">
                  <h4 className="font-semibold">Member {index + 1}</h4>
                  {familyMembers.length > 1 && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => removeFamilyMember(index)}
                      className="text-destructive hover:text-destructive"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  )}
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor={`name-${index}`}>Name *</Label>
                    <Input
                      id={`name-${index}`}
                      value={member.name}
                      onChange={(e) => updateFamilyMember(index, 'name', e.target.value)}
                      placeholder="Enter full name"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor={`passport-${index}`}>Passport Number *</Label>
                    <Input
                      id={`passport-${index}`}
                      value={member.passport_number}
                      onChange={(e) => updateFamilyMember(index, 'passport_number', e.target.value)}
                      placeholder="Enter passport number"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor={`visa-${index}`}>Visa Number</Label>
                    <Input
                      id={`visa-${index}`}
                      value={member.visa_number}
                      onChange={(e) => updateFamilyMember(index, 'visa_number', e.target.value)}
                      placeholder="Enter visa number"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor={`nationality-${index}`}>Nationality *</Label>
                    <Input
                      id={`nationality-${index}`}
                      value={member.nationality}
                      onChange={(e) => updateFamilyMember(index, 'nationality', e.target.value)}
                      placeholder="Enter nationality"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor={`gender-${index}`}>Gender *</Label>
                    <Select
                      value={member.gender}
                      onValueChange={(value) => updateFamilyMember(index, 'gender', value)}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select gender" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="male">Male</SelectItem>
                        <SelectItem value="female">Female</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor={`person-type-${index}`}>Category</Label>
                    <Select
                      value={member.person_type || ''}
                      onValueChange={(value) => updateFamilyMember(index, 'person_type', value)}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select category" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="adult">Adult</SelectItem>
                        <SelectItem value="child">Child</SelectItem>
                        <SelectItem value="infant">Infant</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor={`dob-${index}`}>Date of Birth</Label>
                    <Input
                      id={`dob-${index}`}
                      type="date"
                      value={member.date_of_birth}
                      onChange={(e) => updateFamilyMember(index, 'date_of_birth', e.target.value)}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor={`phone-${index}`}>Phone</Label>
                    <Input
                      id={`phone-${index}`}
                      value={member.phone}
                      onChange={(e) => updateFamilyMember(index, 'phone', e.target.value)}
                      placeholder="Enter phone number"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor={`email-${index}`}>Email</Label>
                    <Input
                      id={`email-${index}`}
                      type="email"
                      value={member.email}
                      onChange={(e) => updateFamilyMember(index, 'email', e.target.value)}
                      placeholder="Enter email address"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor={`emergency-contact-${index}`}>Emergency Contact</Label>
                    <Input
                      id={`emergency-contact-${index}`}
                      value={member.emergency_contact}
                      onChange={(e) => updateFamilyMember(index, 'emergency_contact', e.target.value)}
                      placeholder="Enter emergency contact name"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor={`emergency-phone-${index}`}>Emergency Phone</Label>
                    <Input
                      id={`emergency-phone-${index}`}
                      value={member.emergency_phone}
                      onChange={(e) => updateFamilyMember(index, 'emergency_phone', e.target.value)}
                      placeholder="Enter emergency phone number"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor={`address-${index}`}>Address</Label>
                    <Input
                      id={`address-${index}`}
                      value={member.address}
                      onChange={(e) => updateFamilyMember(index, 'address', e.target.value)}
                      placeholder="Enter address"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor={`city-${index}`}>City</Label>
                    <Input
                      id={`city-${index}`}
                      value={member.city}
                      onChange={(e) => updateFamilyMember(index, 'city', e.target.value)}
                      placeholder="Enter city"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor={`state-${index}`}>State</Label>
                    <Input
                      id={`state-${index}`}
                      value={member.state}
                      onChange={(e) => updateFamilyMember(index, 'state', e.target.value)}
                      placeholder="Enter state"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor={`country-${index}`}>Country</Label>
                    <Input
                      id={`country-${index}`}
                      value={member.country}
                      onChange={(e) => updateFamilyMember(index, 'country', e.target.value)}
                      placeholder="Enter country"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor={`postal-${index}`}>Postal Code</Label>
                    <Input
                      id={`postal-${index}`}
                      value={member.postal_code}
                      onChange={(e) => updateFamilyMember(index, 'postal_code', e.target.value)}
                      placeholder="Enter postal code"
                    />
                  </div>

                  <div className="space-y-2 md:col-span-2">
                    <Label htmlFor={`notes-${index}`}>Notes</Label>
                    <Input
                      id={`notes-${index}`}
                      value={member.notes}
                      onChange={(e) => updateFamilyMember(index, 'notes', e.target.value)}
                      placeholder="Enter any additional notes"
                    />
                  </div>

                </div>
              </Card>
            ))}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={handleCloseAddToFamily}>
              Cancel
            </Button>
            <Button onClick={handleAddToFamilySubmit}>
              Add to Family ({familyMembers.length} members)
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}