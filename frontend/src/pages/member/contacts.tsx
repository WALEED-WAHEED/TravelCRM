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
import { toast } from '@/hooks/use-toast';
import { Users, Plus, Edit, Trash2, Search, Filter, Phone, Mail, MapPin, Building } from 'lucide-react';
import apiClient from '@/api/client';

interface ContactInstruction {
  id: number;
  city: string;
  role: string;
  contact_name: string;
  phone_number: string;
  notes?: string;
  created_by: {
    id: number;
    username: string;
    email: string;
  };
  created_at: string;
  updated_at: string;
}

interface Contact {
  id: number;
  name: string;
  contact_type: 'customer' | 'supplier' | 'partner' | 'vendor' | 'other';
  company: string;
  email: string;
  phone: string;
  alternate_phone: string;
  address: string;
  city: string;
  state: string;
  country: string;
  postal_code: string;
  website: string;
  notes: string;
  is_active: boolean;
  created_by: {
    id: number;
    username: string;
    email: string;
  };
  created_at: string;
  updated_at: string;
}

export default function MemberContacts() {
  const [contacts, setContacts] = useState<ContactInstruction[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [cityFilter, setCityFilter] = useState<string>('all');
  const [roleFilter, setRoleFilter] = useState<string>('all');
  
  // Modal states
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [editingContact, setEditingContact] = useState<ContactInstruction | null>(null);
  const [deletingContactId, setDeletingContactId] = useState<number | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  
  // Form data
  const [formData, setFormData] = useState({
    city: '',
    role: '',
    contact_name: '',
    phone_number: '',
    notes: '',
  });
  const [otherCity, setOtherCity] = useState('');

  // Fetch contacts
  const fetchContacts = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      
      if (cityFilter !== 'all') {
        params.append('city', cityFilter);
      }
      if (roleFilter !== 'all') {
        params.append('role', roleFilter);
      }
      if (searchQuery) {
        params.append('search', searchQuery);
      }

      const response = await apiClient.get(`/api/v1/contacts/contacts/?${params.toString()}`);
      const contactsData = Array.isArray(response.data) ? response.data : response.data.results || [];
      
      // Debug: Log all contacts with their city values
      console.log('Fetched contacts:', contactsData.map(c => ({
        id: c.id,
        role: c.role,
        city: c.city,
        contact_name: c.contact_name
      })));
      
      setContacts(contactsData);
    } catch (error) {
      console.error('Failed to fetch contacts:', error);
      setContacts([]);
      toast({
        title: 'Error',
        description: 'Failed to load contacts',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchContacts();
  }, [cityFilter, roleFilter, searchQuery]);

  // Normalize city name helper
  const normalizeCityName = (city: string): string => {
    const lowerTrimmed = city.toLowerCase().trim();
    if (lowerTrimmed === 'makkah') return 'Makkah';
    if (lowerTrimmed === 'medina' || lowerTrimmed === 'madina') return 'Medina';
    return city.trim(); // For 'Other' cities, keep the user-entered value
  };

  // Handle create/update
  const handleSubmit = async () => {
    try {
      setIsSaving(true);

      // Normalize city value before saving - STRICT normalization
      const cityValue = formData.city === 'Other' ? otherCity : formData.city;
      const normalizedCity = normalizeCityName(cityValue);

      // Log what we're saving to help debug
      console.log('Saving contact with city:', {
        selectedCity: formData.city,
        otherCity: otherCity,
        cityValue: cityValue,
        normalizedCity: normalizedCity
      });

      // Ensure city is saved exactly as normalized (Makkah or Medina)
      const submitData = {
        ...formData,
        city: normalizedCity,
      };

      if (editingContact) {
        console.log('Updating contact ID:', editingContact.id, 'with city:', normalizedCity);
        await apiClient.patch(`/api/v1/contacts/contacts/${editingContact.id}/`, submitData);
        toast({
          title: 'Success',
          description: 'Contact updated successfully',
        });
      } else {
        console.log('Creating new contact with city:', normalizedCity);
        await apiClient.post('/api/v1/contacts/contacts/', submitData);
        toast({
          title: 'Success',
          description: 'Contact created successfully',
        });
      }

      setIsCreateModalOpen(false);
      setIsEditModalOpen(false);
      setEditingContact(null);
      resetForm();
      fetchContacts();
    } catch (error: any) {
      console.error('Failed to save contact:', error);
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to save contact',
        variant: 'destructive',
      });
    } finally {
      setIsSaving(false);
    }
  };

  // Handle delete
  const handleDelete = async () => {
    if (!deletingContactId) return;

    try {
      await apiClient.delete(`/api/v1/contacts/contacts/${deletingContactId}/`);
      toast({
        title: 'Success',
        description: 'Contact deleted successfully',
      });
      fetchContacts();
    } catch (error: any) {
      console.error('Failed to delete contact:', error);
      toast({
        title: 'Error',
        description: 'Failed to delete contact',
        variant: 'destructive',
      });
    } finally {
      setIsDeleteDialogOpen(false);
      setDeletingContactId(null);
    }
  };

  // Reset form
  const resetForm = () => {
    setFormData({
      city: '',
      role: '',
      contact_name: '',
      phone_number: '',
      notes: '',
    });
    setOtherCity('');
  };

  // Open edit modal
  const openEditModal = (contact: ContactInstruction) => {
    setEditingContact(contact);
    const cityLower = (contact.city || '').toLowerCase().trim();
    const isMakkah = cityLower === 'makkah';
    const isMedina = cityLower === 'medina' || cityLower === 'madina';
    
    // Determine which dropdown value to show
    let dropdownCity = 'Other';
    if (isMakkah) dropdownCity = 'Makkah';
    else if (isMedina) dropdownCity = 'Medina';
    
    setFormData({
      city: dropdownCity,
      role: contact.role,
      contact_name: contact.contact_name,
      phone_number: contact.phone_number,
      notes: contact.notes || '',
    });
    setOtherCity(isMakkah || isMedina ? '' : contact.city);
    setIsEditModalOpen(true);
  };

  // Open delete dialog
  const openDeleteDialog = (contactId: number) => {
    setDeletingContactId(contactId);
    setIsDeleteDialogOpen(true);
  };

  // Normalize city name to ensure consistent matching
  const normalizeCity = (city: string): string => {
    const normalized = city?.toLowerCase().trim() || '';
    if (normalized === 'makkah') return 'Makkah';
    if (normalized === 'medina' || normalized === 'madina') return 'Medina';
    return city; // Keep original for other cities
  };

  // Group contacts by city - EXCLUSIVE filtering to prevent duplicates
  // Use a Set to track which contact IDs we've already categorized to prevent duplicates
  const categorizedIds = new Set<number>();
  const makkahContacts: ContactInstruction[] = [];
  const medinaContacts: ContactInstruction[] = [];
  const otherContacts: ContactInstruction[] = [];
  
  contacts.forEach(c => {
    // Skip if we've already categorized this contact
    if (categorizedIds.has(c.id)) {
      console.warn('Skipping duplicate contact ID:', c.id, 'Role:', c.role, 'City:', c.city);
      return;
    }
    
    const cityValue = c.city || '';
    const cityLower = cityValue.toLowerCase().trim();
    
    // Debug: Log contacts that might be causing issues
    if (cityLower.includes('makkah') || cityLower.includes('medina') || cityLower.includes('madina')) {
      console.log('Processing contact:', {
        id: c.id,
        role: c.role,
        city: cityValue,
        cityLower: cityLower,
        contact_name: c.contact_name
      });
    }
    
    // STRICT matching - only exact city names (mutually exclusive)
    // Makkah: ONLY "makkah" (case-insensitive, trimmed)
    if (cityLower === 'makkah') {
      makkahContacts.push(c);
      categorizedIds.add(c.id);
    } 
    // Medina: ONLY "medina" or "madina" (case-insensitive, trimmed)
    else if (cityLower === 'medina' || cityLower === 'madina') {
      medinaContacts.push(c);
      categorizedIds.add(c.id);
    } 
    // Everything else goes to Other
    else if (cityLower) {
      otherContacts.push(c);
      categorizedIds.add(c.id);
    }
  });
  
  // Final validation: Check for any remaining duplicates
  const allContactIds = [...makkahContacts.map(c => c.id), ...medinaContacts.map(c => c.id)];
  const duplicateIds = allContactIds.filter((id, index) => allContactIds.indexOf(id) !== index);
  if (duplicateIds.length > 0) {
    console.error('CRITICAL: Duplicate contact IDs still found after filtering:', duplicateIds);
    // Remove duplicates from makkah (keep in medina if it appears in both)
    duplicateIds.forEach(dupId => {
      const index = makkahContacts.findIndex(c => c.id === dupId);
      if (index !== -1) {
        console.warn('Removing duplicate from Makkah:', dupId);
        makkahContacts.splice(index, 1);
      }
    });
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Team Contacts</h1>
          <p className="text-muted-foreground">Manage Makkah and Medina team contacts</p>
        </div>
        <Button onClick={() => setIsCreateModalOpen(true)}>
          <Plus className="w-4 h-4 mr-2" />
          Add Contact
        </Button>
      </div>

      {/* Makkah and Medina Teams */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* MAKKAH TEAM */}
        <Card>
          <CardHeader className="bg-gradient-to-r from-blue-600 to-blue-700 text-white">
            <CardTitle className="text-xl font-bold">MAKKAH TEAM</CardTitle>
          </CardHeader>
          <CardContent className="p-6">
            {loading ? (
              <div className="space-y-3">
                {[...Array(3)].map((_, i) => (
                  <Skeleton key={i} className="h-12 w-full" />
                ))}
              </div>
            ) : makkahContacts.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <Users className="w-12 h-12 mx-auto mb-2 opacity-50" />
                <p>No Makkah contacts yet.</p>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-4"
                  onClick={() => {
                    setFormData({
                      city: 'Makkah',
                      role: '',
                      contact_name: '',
                      phone_number: '',
                      notes: '',
                    });
                    setIsCreateModalOpen(true);
                  }}
                >
                  <Plus className="w-4 h-4 mr-2" />
                  Add Makkah Contact
                </Button>
              </div>
            ) : (
              <div className="space-y-4">
                {makkahContacts.map((contact) => (
                  <div
                    key={contact.id}
                    className="flex items-start justify-between p-3 border rounded-lg hover:bg-muted/50 transition-colors group"
                  >
                    <div className="flex-1">
                      <div className="font-bold text-base mb-1">
                        {contact.role.toUpperCase()}
                      </div>
                      <div className="text-sm text-muted-foreground space-y-0.5">
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{contact.contact_name}</span>
                        </div>
                        <div className="flex items-center gap-2 text-primary">
                          <Phone className="w-3.5 h-3.5" />
                          <span>{contact.phone_number}</span>
                        </div>
                        {contact.notes && (
                          <div className="text-xs text-muted-foreground mt-1 italic">
                            {contact.notes}
                          </div>
                        )}
                      </div>
                    </div>
                    <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => openEditModal(contact)}
                        className="h-8 w-8 p-0"
                      >
                        <Edit className="w-4 h-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => openDeleteDialog(contact.id)}
                        className="h-8 w-8 p-0 text-destructive hover:text-destructive"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                ))}
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full mt-4"
                  onClick={() => {
                    setFormData({
                      city: 'Makkah',
                      role: '',
                      contact_name: '',
                      phone_number: '',
                      notes: '',
                    });
                    setIsCreateModalOpen(true);
                  }}
                >
                  <Plus className="w-4 h-4 mr-2" />
                  Add More Makkah Contact
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        {/* MEDINA TEAM */}
        <Card>
          <CardHeader className="bg-gradient-to-r from-green-600 to-green-700 text-white">
            <CardTitle className="text-xl font-bold">MEDINA TEAM</CardTitle>
          </CardHeader>
          <CardContent className="p-6">
            {loading ? (
              <div className="space-y-3">
                {[...Array(3)].map((_, i) => (
                  <Skeleton key={i} className="h-12 w-full" />
                ))}
              </div>
            ) : medinaContacts.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <Users className="w-12 h-12 mx-auto mb-2 opacity-50" />
                <p>No Medina contacts yet.</p>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-4"
                  onClick={() => {
                    setFormData({
                      city: 'Medina',
                      role: '',
                      contact_name: '',
                      phone_number: '',
                      notes: '',
                    });
                    setIsCreateModalOpen(true);
                  }}
                >
                  <Plus className="w-4 h-4 mr-2" />
                  Add Medina Contact
                </Button>
              </div>
            ) : (
              <div className="space-y-4">
                {medinaContacts.map((contact) => (
                  <div
                    key={contact.id}
                    className="flex items-start justify-between p-3 border rounded-lg hover:bg-muted/50 transition-colors group"
                  >
                    <div className="flex-1">
                      <div className="font-bold text-base mb-1">
                        {contact.role.toUpperCase()}
                      </div>
                      <div className="text-sm text-muted-foreground space-y-0.5">
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{contact.contact_name}</span>
                        </div>
                        <div className="flex items-center gap-2 text-primary">
                          <Phone className="w-3.5 h-3.5" />
                          <span>{contact.phone_number}</span>
                        </div>
                        {contact.notes && (
                          <div className="text-xs text-muted-foreground mt-1 italic">
                            {contact.notes}
                          </div>
                        )}
                      </div>
                    </div>
                    <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => openEditModal(contact)}
                        className="h-8 w-8 p-0"
                      >
                        <Edit className="w-4 h-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => openDeleteDialog(contact.id)}
                        className="h-8 w-8 p-0 text-destructive hover:text-destructive"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                ))}
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full mt-4"
                  onClick={() => {
                    setFormData({
                      city: 'Medina',
                      role: '',
                      contact_name: '',
                      phone_number: '',
                      notes: '',
                    });
                    setIsCreateModalOpen(true);
                  }}
                >
                  <Plus className="w-4 h-4 mr-2" />
                  Add More Medina Contact
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Other Contacts (if any) */}
      {otherContacts.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Other Contacts</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {otherContacts.map((contact) => (
                <div
                  key={contact.id}
                  className="flex items-start justify-between p-3 border rounded-lg hover:bg-muted/50 transition-colors group"
                >
                  <div className="flex-1">
                    <div className="font-bold text-base mb-1">
                      {contact.role} - {contact.city}
                    </div>
                    <div className="text-sm text-muted-foreground space-y-0.5">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{contact.contact_name}</span>
                      </div>
                      <div className="flex items-center gap-2 text-primary">
                        <Phone className="w-3.5 h-3.5" />
                        <span>{contact.phone_number}</span>
                      </div>
                      {contact.notes && (
                        <div className="text-xs text-muted-foreground mt-1 italic">
                          {contact.notes}
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => openEditModal(contact)}
                      className="h-8 w-8 p-0"
                    >
                      <Edit className="w-4 h-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => openDeleteDialog(contact.id)}
                      className="h-8 w-8 p-0 text-destructive hover:text-destructive"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Create/Edit Modal */}
      <Dialog open={isCreateModalOpen || isEditModalOpen} onOpenChange={(open) => {
        if (!open) {
          setIsCreateModalOpen(false);
          setIsEditModalOpen(false);
          setEditingContact(null);
          resetForm();
        }
      }}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>
              {editingContact ? 'Edit Contact Instruction' : 'Add Contact Instruction'}
            </DialogTitle>
          </DialogHeader>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="city">City</Label>
              <Select
                value={formData.city === 'Other' ? 'Other' : (formData.city || '')}
                onValueChange={(value) => {
                  if (value === 'Other') {
                    setFormData({ ...formData, city: 'Other' });
                  } else {
                    setFormData({ ...formData, city: value });
                    setOtherCity('');
                  }
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select city" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Makkah">Makkah</SelectItem>
                  <SelectItem value="Medina">Medina</SelectItem>
                  <SelectItem value="Other">Other</SelectItem>
                </SelectContent>
              </Select>
              {formData.city === 'Other' && (
                <Input
                  placeholder="Enter city name"
                  value={otherCity}
                  onChange={(e) => {
                    setOtherCity(e.target.value);
                  }}
                  className="mt-2"
                />
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="role">Role</Label>
              <Input
                id="role"
                value={formData.role}
                onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                placeholder="Makkah Management, Madina Helpline, etc."
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="contact_name">Contact Name</Label>
              <Input
                id="contact_name"
                value={formData.contact_name}
                onChange={(e) => setFormData({ ...formData, contact_name: e.target.value })}
                placeholder="Full name"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="phone_number">Phone Number</Label>
              <Input
                id="phone_number"
                value={formData.phone_number}
                onChange={(e) => setFormData({ ...formData, phone_number: e.target.value })}
                placeholder="+966 XX XXX XXXX"
              />
            </div>
            <div className="space-y-2 md:col-span-2">
              <Label htmlFor="notes">Notes</Label>
              <Textarea
                id="notes"
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                placeholder="Additional notes or instructions..."
                rows={3}
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => {
              setIsCreateModalOpen(false);
              setIsEditModalOpen(false);
              setEditingContact(null);
              resetForm();
            }}>
              Cancel
            </Button>
            <Button onClick={handleSubmit} disabled={isSaving}>
              {isSaving ? 'Saving...' : (editingContact ? 'Update' : 'Create')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Are you sure?</AlertDialogTitle>
            <AlertDialogDescription>
              This action cannot be undone. This will permanently delete the contact instruction.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete}>Delete</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}