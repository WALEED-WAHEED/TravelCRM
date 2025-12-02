import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useToast } from '@/hooks/use-toast';
import { systemConfigService, SystemConfiguration, AgencyBranding, EmailTemplate, APIKey } from '@/services';
import { Settings, Palette, Mail, Key, Building2, Globe, Upload } from 'lucide-react';

const SystemConfigPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState('configurations');
  const [loading, setLoading] = useState(false);
  const [configurations, setConfigurations] = useState<SystemConfiguration[]>([]);
  const [agencyBrandings, setAgencyBrandings] = useState<AgencyBranding[]>([]);
  const [emailTemplates, setEmailTemplates] = useState<EmailTemplate[]>([]);
  const [apiKeys, setApiKeys] = useState<APIKey[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const { toast } = useToast();

  useEffect(() => {
    loadData();
  }, [activeTab]);

  const loadData = async () => {
    setLoading(true);
    try {
      switch (activeTab) {
        case 'configurations':
          const configs = await systemConfigService.getConfigurations();
          setConfigurations(configs);
          break;
        case 'branding':
          const brandings = await systemConfigService.getAgencyBrandings();
          setAgencyBrandings(brandings);
          break;
        case 'templates':
          const templates = await systemConfigService.getEmailTemplates();
          setEmailTemplates(templates);
          break;
        case 'api-keys':
          const keys = await systemConfigService.getAPIKeys();
          setApiKeys(keys);
          break;
        case 'dashboard':
          const dashboardSummary = await systemConfigService.getSystemConfigSummary();
          setSummary(dashboardSummary);
          break;
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to load data. Please try again.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleConfigurationUpdate = async (id: number, data: Partial<SystemConfiguration>) => {
    try {
      await systemConfigService.updateConfiguration(id, data);
      toast({
        title: "Success",
        description: "Configuration updated successfully.",
      });
      loadData();
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to update configuration.",
        variant: "destructive",
      });
    }
  };

  const handleBrandingUpdate = async (id: number, data: Partial<AgencyBranding>) => {
    try {
      await systemConfigService.updateAgencyBranding(id, data);
      toast({
        title: "Success",
        description: "Agency branding updated successfully.",
      });
      loadData();
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to update agency branding.",
        variant: "destructive",
      });
    }
  };

  const handleLogoUpload = async (id: number, file: File) => {
    try {
      await systemConfigService.uploadLogo(id, file);
      toast({
        title: "Success",
        description: "Logo uploaded successfully.",
      });
      loadData();
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to upload logo.",
        variant: "destructive",
      });
    }
  };

  return (
    <div className="container mx-auto p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold flex items-center gap-2">
          <Settings className="h-8 w-8" />
          System Configuration
        </h1>
        <p className="text-muted-foreground mt-2">
          Manage system-wide settings, agency branding, and developer configurations.
        </p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="configurations" className="flex items-center gap-2">
            <Settings className="h-4 w-4" />
            Configurations
          </TabsTrigger>
          <TabsTrigger value="branding" className="flex items-center gap-2">
            <Palette className="h-4 w-4" />
            Agency Branding
          </TabsTrigger>
          <TabsTrigger value="templates" className="flex items-center gap-2">
            <Mail className="h-4 w-4" />
            Email Templates
          </TabsTrigger>
          <TabsTrigger value="api-keys" className="flex items-center gap-2">
            <Key className="h-4 w-4" />
            API Keys
          </TabsTrigger>
          <TabsTrigger value="dashboard" className="flex items-center gap-2">
            <Building2 className="h-4 w-4" />
            Dashboard
          </TabsTrigger>
        </TabsList>

        <TabsContent value="configurations" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle>System Configurations</CardTitle>
              <CardDescription>
                Manage system-wide configuration settings
              </CardDescription>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="flex items-center justify-center p-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
                </div>
              ) : (
                <div className="space-y-4">
                  {Array.isArray(configurations) && configurations.map((config) => (
                    <Card key={config.id} className="p-4">
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <Label className="font-medium">{config.key}</Label>
                            <Badge variant={config.is_active ? "default" : "secondary"}>
                              {config.is_active ? "Active" : "Inactive"}
                            </Badge>
                          </div>
                          <p className="text-sm text-muted-foreground mb-2">{config.description}</p>
                          <div className="flex items-center gap-2">
                            <Input
                              value={config.value}
                              onChange={(e) => {
                                // Handle inline editing
                              }}
                              className="flex-1"
                            />
                            <Switch
                              checked={config.is_active}
                              onCheckedChange={(checked) => {
                                handleConfigurationUpdate(config.id, { is_active: checked });
                              }}
                            />
                          </div>
                        </div>
                      </div>
                    </Card>
                  )) || (
                    <div className="text-center py-8">
                      <p className="text-muted-foreground">No configurations found</p>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="branding" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle>Agency Branding</CardTitle>
              <CardDescription>
                Customize branding for each agency
              </CardDescription>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="flex items-center justify-center p-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
                </div>
              ) : (
                <div className="space-y-6">
                  {agencyBrandings.map((branding) => (
                    <Card key={branding.id} className="p-6">
                      <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-3">
                          <Building2 className="h-5 w-5" />
                          <h3 className="text-lg font-semibold">{branding.agency.name}</h3>
                          <Badge variant={branding.is_active ? "default" : "secondary"}>
                            {branding.is_active ? "Active" : "Inactive"}
                          </Badge>
                        </div>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="space-y-4">
                          <div>
                            <Label htmlFor={`company-name-${branding.id}`}>Company Name</Label>
                            <Input
                              id={`company-name-${branding.id}`}
                              value={branding.company_name}
                              onChange={(e) => {
                                // Handle inline editing
                              }}
                            />
                          </div>

                          <div>
                            <Label htmlFor={`tagline-${branding.id}`}>Tagline</Label>
                            <Input
                              id={`tagline-${branding.id}`}
                              value={branding.tagline}
                              onChange={(e) => {
                                // Handle inline editing
                              }}
                            />
                          </div>

                          <div className="grid grid-cols-2 gap-4">
                            <div>
                              <Label htmlFor={`primary-color-${branding.id}`}>Primary Color</Label>
                              <div className="flex items-center gap-2">
                                <Input
                                  id={`primary-color-${branding.id}`}
                                  type="color"
                                  value={branding.primary_color}
                                  onChange={(e) => {
                                    // Handle color change
                                  }}
                                  className="w-12 h-10 p-1"
                                />
                                <Input
                                  value={branding.primary_color}
                                  onChange={(e) => {
                                    // Handle hex input
                                  }}
                                  className="flex-1"
                                />
                              </div>
                            </div>

                            <div>
                              <Label htmlFor={`secondary-color-${branding.id}`}>Secondary Color</Label>
                              <div className="flex items-center gap-2">
                                <Input
                                  id={`secondary-color-${branding.id}`}
                                  type="color"
                                  value={branding.secondary_color}
                                  onChange={(e) => {
                                    // Handle color change
                                  }}
                                  className="w-12 h-10 p-1"
                                />
                                <Input
                                  value={branding.secondary_color}
                                  onChange={(e) => {
                                    // Handle hex input
                                  }}
                                  className="flex-1"
                                />
                              </div>
                            </div>
                          </div>
                        </div>

                        <div className="space-y-4">
                          <div>
                            <Label htmlFor={`logo-${branding.id}`}>Logo</Label>
                            <div className="flex items-center gap-4">
                              {branding.logo && (
                                <img
                                  src={branding.logo}
                                  alt="Agency Logo"
                                  className="h-16 w-16 object-contain border rounded"
                                />
                              )}
                              <div>
                                <Input
                                  id={`logo-${branding.id}`}
                                  type="file"
                                  accept="image/*"
                                  onChange={(e) => {
                                    const file = e.target.files?.[0];
                                    if (file) {
                                      handleLogoUpload(branding.id, file);
                                    }
                                  }}
                                  className="hidden"
                                />
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={() => document.getElementById(`logo-${branding.id}`)?.click()}
                                >
                                  <Upload className="h-4 w-4 mr-2" />
                                  Upload Logo
                                </Button>
                              </div>
                            </div>
                          </div>

                          <div>
                            <Label htmlFor={`website-${branding.id}`}>Website</Label>
                            <Input
                              id={`website-${branding.id}`}
                              type="url"
                              value={branding.website}
                              onChange={(e) => {
                                // Handle website update
                              }}
                            />
                          </div>

                          <div>
                            <Label htmlFor={`email-${branding.id}`}>Email</Label>
                            <Input
                              id={`email-${branding.id}`}
                              type="email"
                              value={branding.email}
                              onChange={(e) => {
                                // Handle email update
                              }}
                            />
                          </div>
                        </div>
                      </div>
                    </Card>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="templates" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle>Email Templates</CardTitle>
              <CardDescription>
                Manage email templates for different purposes
              </CardDescription>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="flex items-center justify-center p-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
                </div>
              ) : (
                <div className="space-y-4">
                  {emailTemplates.map((template) => (
                    <Card key={template.id} className="p-4">
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <h4 className="font-medium">{template.name}</h4>
                            <Badge variant="outline">{template.template_type}</Badge>
                            {template.is_default && (
                              <Badge variant="default">Default</Badge>
                            )}
                            <Badge variant={template.is_active ? "default" : "secondary"}>
                              {template.is_active ? "Active" : "Inactive"}
                            </Badge>
                          </div>
                          <p className="text-sm text-muted-foreground mb-2">{template.subject}</p>
                          <p className="text-sm text-muted-foreground">
                            Agency: {template.agency?.name || "Global"}
                          </p>
                        </div>
                        <Button variant="outline" size="sm">
                          Edit Template
                        </Button>
                      </div>
                    </Card>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="api-keys" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle>API Keys</CardTitle>
              <CardDescription>
                Manage API keys for external integrations
              </CardDescription>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="flex items-center justify-center p-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
                </div>
              ) : (
                <div className="space-y-4">
                  {apiKeys.map((key) => (
                    <Card key={key.id} className="p-4">
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <h4 className="font-medium">{key.name}</h4>
                            <Badge variant="outline">{key.key_type}</Badge>
                            <Badge variant={key.is_active ? "default" : "secondary"}>
                              {key.is_active ? "Active" : "Inactive"}
                            </Badge>
                          </div>
                          <p className="text-sm text-muted-foreground mb-2">{key.description}</p>
                          <p className="text-sm text-muted-foreground">
                            Key: {key.api_key_masked}
                          </p>
                          {key.endpoint_url && (
                            <p className="text-sm text-muted-foreground">
                              Endpoint: {key.endpoint_url}
                            </p>
                          )}
                          <p className="text-sm text-muted-foreground">
                            Agency: {key.agency?.name || "Global"}
                          </p>
                        </div>
                        <div className="flex gap-2">
                          <Button variant="outline" size="sm">
                            Test Connection
                          </Button>
                          <Button variant="outline" size="sm">
                            Edit
                          </Button>
                        </div>
                      </div>
                    </Card>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="dashboard" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle>System Dashboard</CardTitle>
              <CardDescription>
                Overview of system configuration and health status
              </CardDescription>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="flex items-center justify-center p-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
                </div>
              ) : summary ? (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <Card className="p-4">
                    <div className="flex items-center gap-3">
                      <Settings className="h-8 w-8 text-blue-500" />
                      <div>
                        <p className="text-2xl font-bold">{summary.total_configurations}</p>
                        <p className="text-sm text-muted-foreground">Total Configurations</p>
                      </div>
                    </div>
                  </Card>

                  <Card className="p-4">
                    <div className="flex items-center gap-3">
                      <Building2 className="h-8 w-8 text-green-500" />
                      <div>
                        <p className="text-2xl font-bold">{summary.total_agencies}</p>
                        <p className="text-sm text-muted-foreground">Total Agencies</p>
                      </div>
                    </div>
                  </Card>

                  <Card className="p-4">
                    <div className="flex items-center gap-3">
                      <Palette className="h-8 w-8 text-purple-500" />
                      <div>
                        <p className="text-2xl font-bold">{summary.agencies_with_branding}</p>
                        <p className="text-sm text-muted-foreground">Agencies with Branding</p>
                      </div>
                    </div>
                  </Card>

                  <Card className="p-4">
                    <div className="flex items-center gap-3">
                      <Mail className="h-8 w-8 text-orange-500" />
                      <div>
                        <p className="text-2xl font-bold">{summary.total_email_templates}</p>
                        <p className="text-sm text-muted-foreground">Email Templates</p>
                      </div>
                    </div>
                  </Card>

                  <Card className="p-4">
                    <div className="flex items-center gap-3">
                      <Key className="h-8 w-8 text-red-500" />
                      <div>
                        <p className="text-2xl font-bold">{summary.total_api_keys}</p>
                        <p className="text-sm text-muted-foreground">API Keys</p>
                      </div>
                    </div>
                  </Card>

                  <Card className="p-4">
                    <div className="flex items-center gap-3">
                      <Globe className="h-8 w-8 text-indigo-500" />
                      <div>
                        <p className="text-2xl font-bold">{summary.recent_changes}</p>
                        <p className="text-sm text-muted-foreground">Recent Changes</p>
                      </div>
                    </div>
                  </Card>
                </div>
              ) : (
                <Alert>
                  <AlertDescription>
                    No summary data available. Please try refreshing the page.
                  </AlertDescription>
                </Alert>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default SystemConfigPage;
