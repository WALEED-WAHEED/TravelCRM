import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { toast } from '@/hooks/use-toast';
import { Upload, Save, Building, Phone, MapPin } from 'lucide-react';
import apiClient from '@/api/client';

interface SAASProductConfig {
  id?: number;
  product_name: string;
  logo_url?: string;
  address: string;
  phone: string;
}

export default function DeveloperSAASProfile() {
  const [loading, setLoading] = useState(false);
  const [uploadingLogo, setUploadingLogo] = useState(false);
  const [config, setConfig] = useState<SAASProductConfig>({
    product_name: '',
    address: '',
    phone: '',
  });

  useEffect(() => {
    fetchConfig();
  }, []);

  const fetchConfig = async () => {
    try {
      setLoading(true);
      const response = await apiClient.get('/api/v1/system-config/saas-product-config/');
      if (response.data) {
        setConfig({
          id: response.data.id,
          product_name: response.data.product_name || '',
          logo_url: response.data.logo_url || '',
          address: response.data.address || '',
          phone: response.data.phone || '',
        });
      }
    } catch (error: any) {
      console.error('Error fetching SAAS product config:', error);
      toast({
        title: 'Error',
        description: 'Failed to load SAAS product configuration. Please try again.',
        variant: 'destructive',
      });
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

      const response = await apiClient.post('/api/v1/system-config/saas-product-config/upload-logo/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      setConfig({ ...config, logo_url: response.data.logo_url });
      toast({
        title: 'Success',
        description: 'Logo uploaded successfully',
      });
    } catch (error: any) {
      console.error('Error uploading logo:', error);
      toast({
        title: 'Error',
        description: error.response?.data?.error || 'Failed to upload logo. Please try again.',
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
      
      const configData = {
        product_name: config.product_name,
        address: config.address,
        phone: config.phone,
      };
      
      const response = await apiClient.patch('/api/v1/system-config/saas-product-config/', configData);
      setConfig({ ...config, id: response.data.id });
      toast({
        title: 'Success',
        description: 'SAAS product configuration saved successfully',
      });
    } catch (error: any) {
      console.error('Error saving config:', error);
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to save configuration. Please try again.',
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
            SAAS Product Configuration
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Logo Upload Section */}
            <div className="space-y-4">
              <Label>Product Logo</Label>
              <div className="flex items-center gap-4">
                {config.logo_url && (
                  <div className="w-32 h-32 border rounded-lg p-2 bg-muted/30">
                    <img
                      src={config.logo_url}
                      alt="Product Logo"
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
                    Upload product logo (max 5MB, PNG/JPG recommended)
                  </p>
                </div>
              </div>
            </div>

            {/* Product Information */}
            <div className="space-y-4">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <Building className="h-4 w-4" />
                Product Information
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="md:col-span-2">
                  <Label htmlFor="product_name">Product Name *</Label>
                  <Input
                    id="product_name"
                    value={config.product_name}
                    onChange={(e) => setConfig({ ...config, product_name: e.target.value })}
                    placeholder="e.g., Nahd Travels CRM"
                    required
                  />
                </div>
                <div className="md:col-span-2">
                  <Label htmlFor="address">Address</Label>
                  <Textarea
                    id="address"
                    value={config.address}
                    onChange={(e) => setConfig({ ...config, address: e.target.value })}
                    placeholder="Product address"
                    rows={3}
                  />
                </div>
                <div>
                  <Label htmlFor="phone">Phone Number</Label>
                  <Input
                    id="phone"
                    type="tel"
                    value={config.phone}
                    onChange={(e) => setConfig({ ...config, phone: e.target.value })}
                    placeholder="+966 123456789"
                  />
                </div>
              </div>
            </div>

            {/* Submit Button */}
            <div className="flex justify-end">
              <Button type="submit" disabled={loading} className="gap-2">
                <Save className="h-4 w-4" />
                {loading ? 'Saving...' : 'Save Configuration'}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

