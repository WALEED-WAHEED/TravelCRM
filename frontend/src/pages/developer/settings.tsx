import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Separator } from '@/components/ui/separator';
import { Palette, Shield, Settings2, Upload, Check, Loader2, ExternalLink } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { useNavigate } from 'react-router-dom';
import apiClient from '@/api/client';
import { testTokenExpiration, testConcurrentRequests } from '@/utils/testAuth';

interface SystemSettings {
  // Branding
  logo_url?: string;
  system_name: string;
  primary_color: string;
  secondary_color: string;
  accent_color: string;
  
  // Authentication & Security
  password_min_length: number;
  password_require_special: boolean;
  jwt_access_expiry_minutes: number;
  jwt_refresh_expiry_days: number;
  enable_two_factor: boolean;
  
  // System Preferences
  default_max_users_per_agency: number;
  auto_approve_agencies: boolean;
  smtp_host: string;
  smtp_port: number;
  smtp_from_email: string;
  default_timezone: string;
  date_format: string;
}

export default function DeveloperSettings() {
  const { toast } = useToast();
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(true);
  
  // Test functions for token expiration handling
  const handleTestTokenExpiration = async () => {
    try {
      await testTokenExpiration();
      toast({
        title: "Test Completed",
        description: "Check console for results. No infinite loops should occur.",
      });
    } catch (error) {
      toast({
        title: "Test Failed",
        description: "An error occurred during testing.",
        variant: "destructive",
      });
    }
  };

  const handleTestConcurrentRequests = async () => {
    try {
      await testConcurrentRequests();
      toast({
        title: "Test Completed",
        description: "Check console for results. Concurrent requests should be handled properly.",
      });
    } catch (error) {
      toast({
        title: "Test Failed",
        description: "An error occurred during testing.",
        variant: "destructive",
      });
    }
  };
  const [isSaving, setIsSaving] = useState(false);
  const [logoFile, setLogoFile] = useState<File | null>(null);
  const [logoPreview, setLogoPreview] = useState<string>('');
  
  const [settings, setSettings] = useState<SystemSettings>({
    system_name: 'Travel Management System',
    primary_color: '#3b82f6',
    secondary_color: '#8b5cf6',
    accent_color: '#10b981',
    password_min_length: 8,
    password_require_special: true,
    jwt_access_expiry_minutes: 30,
    jwt_refresh_expiry_days: 7,
    enable_two_factor: false,
    default_max_users_per_agency: 50,
    auto_approve_agencies: false,
    smtp_host: '',
    smtp_port: 587,
    smtp_from_email: '',
    default_timezone: 'UTC',
    date_format: 'YYYY-MM-DD',
  });

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      setIsLoading(true);
      const response = await apiClient.get('/api/v1/settings/');
      setSettings(response.data);
      if (response.data.logo_url) {
        setLogoPreview(response.data.logo_url);
      }
    } catch (error: any) {
      console.error('Failed to fetch settings:', error);
      toast({
        title: 'Error',
        description: 'Failed to load settings. Using defaults.',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setLogoFile(file);
      const reader = new FileReader();
      reader.onloadend = () => {
        setLogoPreview(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleSave = async () => {
    try {
      setIsSaving(true);
      
      const formData = new FormData();
      
      // Add all settings to formData
      Object.entries(settings).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          formData.append(key, value.toString());
        }
      });
      
      // Add logo file if present
      if (logoFile) {
        formData.append('logo', logoFile);
      }

      await apiClient.patch('/api/v1/settings/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      toast({
        title: 'Success',
        description: 'Settings saved successfully',
      });
    } catch (error: any) {
      console.error('Failed to save settings:', error);
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to save settings',
        variant: 'destructive',
      });
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-24">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-950/20 dark:to-purple-950/20 p-6 rounded-lg">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-foreground">System Settings</h1>
            <p className="text-muted-foreground">Configure system-wide branding, security, and preferences</p>
          </div>
          <Button
            variant="outline"
            onClick={() => navigate('/developer/system-config')}
            className="flex items-center gap-2"
          >
            <ExternalLink className="h-4 w-4" />
            Advanced Configuration
          </Button>
        </div>
      </div>

      {/* Branding Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Palette className="h-5 w-5" />
            Branding
          </CardTitle>
          <CardDescription>Customize system logo, name, and colors</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Logo Upload */}
          <div className="space-y-2">
            <Label htmlFor="logo">System Logo</Label>
            <div className="flex items-center gap-4">
              {logoPreview && (
                <div className="w-24 h-24 rounded-lg border-2 border-border overflow-hidden bg-white dark:bg-gray-800 flex items-center justify-center">
                  <img src={logoPreview} alt="Logo preview" className="max-w-full max-h-full object-contain" />
                </div>
              )}
              <div className="flex-1">
                <Input
                  id="logo"
                  type="file"
                  accept="image/*"
                  onChange={handleLogoChange}
                  className="cursor-pointer"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Recommended: PNG or SVG, max 2MB
                </p>
              </div>
            </div>
          </div>

          <Separator />

          {/* System Name */}
          <div className="space-y-2">
            <Label htmlFor="system_name">System Name</Label>
            <Input
              id="system_name"
              value={settings.system_name}
              onChange={(e) => setSettings({ ...settings, system_name: e.target.value })}
              placeholder="Travel Management System"
            />
          </div>

          <Separator />

          {/* Color Pickers */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label htmlFor="primary_color">Primary Color</Label>
              <div className="flex gap-2">
                <Input
                  id="primary_color"
                  type="color"
                  value={settings.primary_color}
                  onChange={(e) => setSettings({ ...settings, primary_color: e.target.value })}
                  className="w-20 h-10 cursor-pointer"
                />
                <Input
                  value={settings.primary_color}
                  onChange={(e) => setSettings({ ...settings, primary_color: e.target.value })}
                  placeholder="#3b82f6"
                  className="flex-1"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="secondary_color">Secondary Color</Label>
              <div className="flex gap-2">
                <Input
                  id="secondary_color"
                  type="color"
                  value={settings.secondary_color}
                  onChange={(e) => setSettings({ ...settings, secondary_color: e.target.value })}
                  className="w-20 h-10 cursor-pointer"
                />
                <Input
                  value={settings.secondary_color}
                  onChange={(e) => setSettings({ ...settings, secondary_color: e.target.value })}
                  placeholder="#8b5cf6"
                  className="flex-1"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="accent_color">Accent Color</Label>
              <div className="flex gap-2">
                <Input
                  id="accent_color"
                  type="color"
                  value={settings.accent_color}
                  onChange={(e) => setSettings({ ...settings, accent_color: e.target.value })}
                  className="w-20 h-10 cursor-pointer"
                />
                <Input
                  value={settings.accent_color}
                  onChange={(e) => setSettings({ ...settings, accent_color: e.target.value })}
                  placeholder="#10b981"
                  className="flex-1"
                />
              </div>
            </div>
          </div>

          {/* Live Preview */}
          <div className="mt-6 p-4 rounded-lg border-2 border-dashed border-border bg-muted/30">
            <p className="text-sm font-medium mb-3">Live Preview</p>
            <div className="flex items-center gap-4 p-4 bg-background rounded-lg">
              {logoPreview && (
                <div className="w-12 h-12 rounded flex items-center justify-center" style={{ backgroundColor: settings.primary_color }}>
                  <img src={logoPreview} alt="Logo" className="max-w-full max-h-full object-contain" />
                </div>
              )}
              <div>
                <h3 className="font-semibold" style={{ color: settings.primary_color }}>{settings.system_name}</h3>
                <div className="flex gap-2 mt-2">
                  <div className="w-8 h-8 rounded" style={{ backgroundColor: settings.primary_color }} title="Primary" />
                  <div className="w-8 h-8 rounded" style={{ backgroundColor: settings.secondary_color }} title="Secondary" />
                  <div className="w-8 h-8 rounded" style={{ backgroundColor: settings.accent_color }} title="Accent" />
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Authentication & Security Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Authentication & Security
          </CardTitle>
          <CardDescription>Configure password policies and token settings</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-2">
              <Label htmlFor="password_min_length">Password Minimum Length</Label>
              <Input
                id="password_min_length"
                type="number"
                min="6"
                max="20"
                value={settings.password_min_length}
                onChange={(e) => setSettings({ ...settings, password_min_length: parseInt(e.target.value) })}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password_require_special" className="flex items-center justify-between">
                <span>Require Special Characters</span>
                <Switch
                  id="password_require_special"
                  checked={settings.password_require_special}
                  onCheckedChange={(checked) => setSettings({ ...settings, password_require_special: checked })}
                />
              </Label>
              <p className="text-xs text-muted-foreground">
                Enforce special characters in passwords
              </p>
            </div>
          </div>

          <Separator />

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-2">
              <Label htmlFor="jwt_access_expiry_minutes">JWT Access Token Expiry (minutes)</Label>
              <Input
                id="jwt_access_expiry_minutes"
                type="number"
                min="5"
                max="1440"
                value={settings.jwt_access_expiry_minutes}
                onChange={(e) => setSettings({ ...settings, jwt_access_expiry_minutes: parseInt(e.target.value) })}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="jwt_refresh_expiry_days">JWT Refresh Token Expiry (days)</Label>
              <Input
                id="jwt_refresh_expiry_days"
                type="number"
                min="1"
                max="90"
                value={settings.jwt_refresh_expiry_days}
                onChange={(e) => setSettings({ ...settings, jwt_refresh_expiry_days: parseInt(e.target.value) })}
              />
            </div>
          </div>

          <Separator />

          <div className="space-y-2">
            <Label htmlFor="enable_two_factor" className="flex items-center justify-between">
              <span>Enable Two-Factor Authentication</span>
              <Switch
                id="enable_two_factor"
                checked={settings.enable_two_factor}
                onCheckedChange={(checked) => setSettings({ ...settings, enable_two_factor: checked })}
              />
            </Label>
            <p className="text-xs text-muted-foreground">
              Future feature placeholder - not yet implemented
            </p>
          </div>
        </CardContent>
      </Card>

      {/* System Preferences Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings2 className="h-5 w-5" />
            System Preferences
          </CardTitle>
          <CardDescription>Configure default settings and email configuration</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-2">
              <Label htmlFor="default_max_users_per_agency">Default Max Users per Agency</Label>
              <Input
                id="default_max_users_per_agency"
                type="number"
                min="1"
                max="1000"
                value={settings.default_max_users_per_agency}
                onChange={(e) => setSettings({ ...settings, default_max_users_per_agency: parseInt(e.target.value) })}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="auto_approve_agencies" className="flex items-center justify-between">
                <span>Auto-approve Agency Accounts</span>
                <Switch
                  id="auto_approve_agencies"
                  checked={settings.auto_approve_agencies}
                  onCheckedChange={(checked) => setSettings({ ...settings, auto_approve_agencies: checked })}
                />
              </Label>
              <p className="text-xs text-muted-foreground">
                Automatically approve new agency registrations
              </p>
            </div>
          </div>

          <Separator />

          <div className="space-y-4">
            <h4 className="font-medium">Email Configuration (SMTP)</h4>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="smtp_host">SMTP Host</Label>
                <Input
                  id="smtp_host"
                  value={settings.smtp_host}
                  onChange={(e) => setSettings({ ...settings, smtp_host: e.target.value })}
                  placeholder="smtp.gmail.com"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="smtp_port">SMTP Port</Label>
                <Input
                  id="smtp_port"
                  type="number"
                  value={settings.smtp_port}
                  onChange={(e) => setSettings({ ...settings, smtp_port: parseInt(e.target.value) })}
                  placeholder="587"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="smtp_from_email">From Email Address</Label>
              <Input
                id="smtp_from_email"
                type="email"
                value={settings.smtp_from_email}
                onChange={(e) => setSettings({ ...settings, smtp_from_email: e.target.value })}
                placeholder="noreply@yourdomain.com"
              />
            </div>
          </div>

          <Separator />

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-2">
              <Label htmlFor="default_timezone">Default Timezone</Label>
              <Select
                value={settings.default_timezone}
                onValueChange={(value) => setSettings({ ...settings, default_timezone: value })}
              >
                <SelectTrigger id="default_timezone">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="UTC">UTC</SelectItem>
                  <SelectItem value="America/New_York">America/New York (EST)</SelectItem>
                  <SelectItem value="America/Chicago">America/Chicago (CST)</SelectItem>
                  <SelectItem value="America/Denver">America/Denver (MST)</SelectItem>
                  <SelectItem value="America/Los_Angeles">America/Los Angeles (PST)</SelectItem>
                  <SelectItem value="Europe/London">Europe/London</SelectItem>
                  <SelectItem value="Europe/Paris">Europe/Paris</SelectItem>
                  <SelectItem value="Asia/Dubai">Asia/Dubai</SelectItem>
                  <SelectItem value="Asia/Kolkata">Asia/Kolkata</SelectItem>
                  <SelectItem value="Asia/Tokyo">Asia/Tokyo</SelectItem>
                  <SelectItem value="Australia/Sydney">Australia/Sydney</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="date_format">Date Format</Label>
              <Select
                value={settings.date_format}
                onValueChange={(value) => setSettings({ ...settings, date_format: value })}
              >
                <SelectTrigger id="date_format">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="YYYY-MM-DD">YYYY-MM-DD (2025-01-30)</SelectItem>
                  <SelectItem value="DD/MM/YYYY">DD/MM/YYYY (30/01/2025)</SelectItem>
                  <SelectItem value="MM/DD/YYYY">MM/DD/YYYY (01/30/2025)</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Token Expiration Test Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Authentication Testing
          </CardTitle>
          <CardDescription>Test token expiration handling and logout functionality</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="bg-yellow-50 dark:bg-yellow-950/20 p-4 rounded-lg">
            <p className="text-sm text-yellow-800 dark:text-yellow-200">
              <strong>Warning:</strong> These tests will simulate token expiration scenarios. 
              Use only for debugging the infinite redirect loop fix.
            </p>
          </div>
          
          <div className="flex gap-4">
            <Button
              onClick={handleTestTokenExpiration}
              variant="outline"
              className="flex items-center gap-2"
            >
              <Shield className="h-4 w-4" />
              Test Token Expiration
            </Button>
            
            <Button
              onClick={handleTestConcurrentRequests}
              variant="outline"
              className="flex items-center gap-2"
            >
              <Shield className="h-4 w-4" />
              Test Concurrent Requests
            </Button>
          </div>
          
          <div className="text-sm text-muted-foreground">
            <p>• <strong>Token Expiration Test:</strong> Simulates expired tokens and verifies cleanup</p>
            <p>• <strong>Concurrent Requests Test:</strong> Tests multiple simultaneous requests with expired tokens</p>
            <p>• Check the browser console for detailed test results</p>
          </div>
        </CardContent>
      </Card>

      {/* Sticky Save Button */}
      <div className="fixed bottom-6 right-6 z-50">
        <Button
          onClick={handleSave}
          disabled={isSaving}
          size="lg"
          className="shadow-lg"
        >
          {isSaving ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Saving...
            </>
          ) : (
            <>
              <Check className="mr-2 h-4 w-4" />
              Save Changes
            </>
          )}
        </Button>
      </div>
    </div>
  );
}