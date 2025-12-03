import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { toast } from '@/hooks/use-toast';
import { Upload, Save, Building, Mail, Phone, MapPin, Globe, User } from 'lucide-react';
import apiClient from '@/api/client';

interface MemberProfile {
  id?: number;
  company_name: string;
  company_logo?: string;
  company_address: string;
  company_city: string;
  company_country: string;
  company_phone: string;
  company_email: string;
  company_website: string;
  company_registration_number: string;
  contact_person_name: string;
  contact_person_phone: string;
  contact_person_email: string;
  notes: string;
  parent_company_name?: string;
  parent_company_country?: string;
  parent_company_whatsapp?: string;
}

export default function MemberProfile() {
  const [loading, setLoading] = useState(false);
  const [uploadingLogo, setUploadingLogo] = useState(false);
  const [profile, setProfile] = useState<MemberProfile>({
    company_name: '',
    company_logo: '',
    company_address: '',
    company_city: '',
    company_country: '',
    company_phone: '',
    company_email: '',
    company_website: '',
    company_registration_number: '',
    contact_person_name: '',
    contact_person_phone: '',
    contact_person_email: '',
    notes: '',
    parent_company_name: '',
    parent_company_country: '',
    parent_company_whatsapp: '',
  });

  useEffect(() => {
    fetchProfile();
  }, []);

  const fetchProfile = async () => {
    try {
      setLoading(true);
      const response = await apiClient.get('/api/v1/accounts/profile/');
      if (response.data) {
        // Map AgencyBranding data to our profile interface
        setProfile({
          id: response.data.id,
          company_name: response.data.company_name || '',
          company_logo: response.data.logo_url || '',
          company_address: response.data.address || '',
          company_city: response.data.custom_fields?.city || '',
          company_country: response.data.custom_fields?.country || '',
          company_phone: response.data.phone || '',
          company_email: response.data.email || '',
          company_website: response.data.website || '',
          company_registration_number: response.data.custom_fields?.registration_number || '',
          contact_person_name: response.data.custom_fields?.contact_person_name || '',
          contact_person_phone: response.data.custom_fields?.contact_person_phone || '',
          contact_person_email: response.data.custom_fields?.contact_person_email || '',
          notes: response.data.custom_fields?.notes || '',
          parent_company_name: response.data.custom_fields?.parent_company_name || '',
          parent_company_country: response.data.custom_fields?.parent_company_country || '',
          parent_company_whatsapp: response.data.custom_fields?.parent_company_whatsapp || '',
        });
      }
    } catch (error: any) {
      if (error.response?.status === 404) {
        // Profile doesn't exist yet, that's okay
        console.log('Profile not found, will create new one');
      } else {
        console.error('Error fetching profile:', error);
        toast({
          title: 'Error',
          description: 'Failed to load profile. Please try again.',
          variant: 'destructive',
        });
      }
    } finally {
      setLoading(false);
    }
  };

  const handleLogoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file type
    if (!file.type.startsWith('image/')) {
      toast({
        title: 'Invalid File',
        description: 'Please upload an image file',
        variant: 'destructive',
      });
      return;
    }

    // Validate file size (max 5MB)
    if (file.size > 5 * 1024 * 1024) {
      toast({
        title: 'File Too Large',
        description: 'Logo must be less than 5MB',
        variant: 'destructive',
      });
      return;
    }

    try {
      setUploadingLogo(true);
      const formData = new FormData();
      formData.append('logo', file);

      const response = await apiClient.post('/api/v1/accounts/profile/upload-logo/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      setProfile({ ...profile, company_logo: response.data.logo_url });
      toast({
        title: 'Success',
        description: 'Logo uploaded successfully',
      });
    } catch (error: any) {
      console.error('Error uploading logo:', error);
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to upload logo. Please try again.',
        variant: 'destructive',
      });
    } finally {
      setUploadingLogo(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      
      // Map profile data to AgencyBranding format
      const brandingData = {
        company_name: profile.company_name,
        address: profile.company_address,
        phone: profile.company_phone,
        email: profile.company_email,
        website: profile.company_website,
        custom_fields: {
          notes: profile.notes,
          city: profile.company_city,
          country: profile.company_country,
          registration_number: profile.company_registration_number,
          contact_person_name: profile.contact_person_name,
          contact_person_phone: profile.contact_person_phone,
          contact_person_email: profile.contact_person_email,
          parent_company_name: profile.parent_company_name,
          parent_company_country: profile.parent_company_country,
          parent_company_whatsapp: profile.parent_company_whatsapp,
        }
      };
      
      // Always use POST to create/update profile
      const response = await apiClient.post('/api/v1/accounts/profile/', brandingData);
      setProfile({ ...profile, id: response.data.id });
      toast({
        title: 'Success',
        description: 'Profile saved successfully',
      });
    } catch (error: any) {
      console.error('Error saving profile:', error);
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to save profile. Please try again.',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Building className="h-5 w-5" />
            Travel Agency Profile
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Logo Upload Section */}
            <div className="space-y-4">
              <Label>Company Logo</Label>
              <div className="flex items-center gap-4">
                {profile.company_logo && (
                  <div className="w-32 h-32 border rounded-lg p-2 bg-muted/30">
                    <img
                      src={profile.company_logo}
                      alt="Company Logo"
                      className="w-full h-full object-contain"
                    />
                  </div>
                )}
                <div className="flex flex-col gap-2">
                  <Input
                    type="file"
                    accept="image/*"
                    onChange={handleLogoUpload}
                    disabled={uploadingLogo}
                    className="w-64"
                  />
                  <p className="text-xs text-muted-foreground">
                    Upload company logo (max 5MB, PNG/JPG recommended)
                  </p>
                </div>
              </div>
            </div>

            {/* Company Information */}
            <div className="space-y-4">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <Building className="h-4 w-4" />
                Company Information
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="company_name">Company Name *</Label>
                  <Input
                    id="company_name"
                    value={profile.company_name}
                    onChange={(e) => setProfile({ ...profile, company_name: e.target.value })}
                    placeholder="e.g., NAHD TRAVELS"
                    required
                  />
                </div>
                <div>
                  <Label htmlFor="company_registration_number">Registration Number</Label>
                  <Input
                    id="company_registration_number"
                    value={profile.company_registration_number}
                    onChange={(e) => setProfile({ ...profile, company_registration_number: e.target.value })}
                    placeholder="Company registration number"
                  />
                </div>
                <div className="md:col-span-2">
                  <Label htmlFor="company_address">Address</Label>
                  <Input
                    id="company_address"
                    value={profile.company_address}
                    onChange={(e) => setProfile({ ...profile, company_address: e.target.value })}
                    placeholder="Company address"
                  />
                </div>
                <div>
                  <Label htmlFor="company_city">City</Label>
                  <Input
                    id="company_city"
                    value={profile.company_city}
                    onChange={(e) => setProfile({ ...profile, company_city: e.target.value })}
                    placeholder="City"
                  />
                </div>
                <div>
                  <Label htmlFor="company_country">Country</Label>
                  <Input
                    id="company_country"
                    value={profile.company_country}
                    onChange={(e) => setProfile({ ...profile, company_country: e.target.value })}
                    placeholder="Country"
                  />
                </div>
              </div>
            </div>

            {/* Contact Information */}
            <div className="space-y-4">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <Phone className="h-4 w-4" />
                Contact Information
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="company_phone">Company Phone *</Label>
                  <Input
                    id="company_phone"
                    type="tel"
                    value={profile.company_phone}
                    onChange={(e) => setProfile({ ...profile, company_phone: e.target.value })}
                    placeholder="+966 123456789"
                    required
                  />
                </div>
                <div>
                  <Label htmlFor="company_email">Company Email *</Label>
                  <Input
                    id="company_email"
                    type="email"
                    value={profile.company_email}
                    onChange={(e) => setProfile({ ...profile, company_email: e.target.value })}
                    placeholder="info@company.com"
                    required
                  />
                </div>
                <div>
                  <Label htmlFor="company_website">Website</Label>
                  <Input
                    id="company_website"
                    type="url"
                    value={profile.company_website}
                    onChange={(e) => setProfile({ ...profile, company_website: e.target.value })}
                    placeholder="https://www.company.com"
                  />
                </div>
              </div>
            </div>

            {/* Contact Person */}
            <div className="space-y-4">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <User className="h-4 w-4" />
                Contact Person
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="contact_person_name">Contact Person Name</Label>
                  <Input
                    id="contact_person_name"
                    value={profile.contact_person_name}
                    onChange={(e) => setProfile({ ...profile, contact_person_name: e.target.value })}
                    placeholder="Full name"
                  />
                </div>
                <div>
                  <Label htmlFor="contact_person_phone">Contact Person Phone</Label>
                  <Input
                    id="contact_person_phone"
                    type="tel"
                    value={profile.contact_person_phone}
                    onChange={(e) => setProfile({ ...profile, contact_person_phone: e.target.value })}
                    placeholder="+966 123456789"
                  />
                </div>
                <div>
                  <Label htmlFor="contact_person_email">Contact Person Email</Label>
                  <Input
                    id="contact_person_email"
                    type="email"
                    value={profile.contact_person_email}
                    onChange={(e) => setProfile({ ...profile, contact_person_email: e.target.value })}
                    placeholder="person@company.com"
                  />
                </div>
              </div>
            </div>

            {/* Shirka Company (Noori Kaki) */}
            <div className="space-y-4">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                Shirka Company (Right-side on Voucher)
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <Label htmlFor="parent_company_name">Shirka Company Name</Label>
                  <Input
                    id="parent_company_name"
                    value={profile.parent_company_name}
                    onChange={(e) => setProfile({ ...profile, parent_company_name: e.target.value })}
                    placeholder="e.g., NOORI KAKI CO."
                  />
                </div>
                <div>
                  <Label htmlFor="parent_company_country">Shirka Company Country</Label>
                  <Input
                    id="parent_company_country"
                    value={profile.parent_company_country}
                    onChange={(e) => setProfile({ ...profile, parent_company_country: e.target.value })}
                    placeholder="e.g., PAKISTAN"
                  />
                </div>
                <div>
                  <Label htmlFor="parent_company_whatsapp">Shirka Company WhatsApp</Label>
                  <Input
                    id="parent_company_whatsapp"
                    value={profile.parent_company_whatsapp}
                    onChange={(e) => setProfile({ ...profile, parent_company_whatsapp: e.target.value })}
                    placeholder="WhatsApp number"
                  />
                </div>
              </div>
              <p className="text-xs text-muted-foreground">These appear on the voucher right side. Leave blank to hide.</p>
            </div>

            {/* Notes */}
            <div className="space-y-4">
              <Label htmlFor="notes">Additional Notes</Label>
              <Textarea
                id="notes"
                rows={4}
                value={profile.notes}
                onChange={(e) => setProfile({ ...profile, notes: e.target.value })}
                placeholder="Any additional information about your company..."
              />
            </div>

            {/* Submit Button */}
            <div className="flex justify-end">
              <Button type="submit" disabled={loading} className="gap-2">
                <Save className="h-4 w-4" />
                {loading ? 'Saving...' : 'Save Profile'}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

