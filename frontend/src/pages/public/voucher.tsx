import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { QRViewer } from '@/components/ui/ui-kit';
import { Spinner } from '@/components/ui/spinner';
import { Plane, MapPin, Calendar, Users, Eye, AlertCircle } from 'lucide-react';

interface VoucherData {
  id: string;
  title: string;
  description: string;
  validity: string;
  status: 'valid' | 'expired' | 'used';
  customer: {
    name: string;
    email: string;
  };
  package: {
    name: string;
    destination: string;
    duration: string;
    participants: number;
  };
  agency: {
    name: string;
    contact: string;
  };
}

export default function PublicVoucherPage() {
  const { token } = useParams<{ token: string }>();
  const [voucher, setVoucher] = useState<VoucherData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Simulate API call to fetch voucher data
    const fetchVoucher = async () => {
      try {
        setLoading(true);
        // In real implementation, this would call: apiClient.get(`/api/v1/vouchers/public/${token}/`)
        
        // Mock data for demonstration
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        if (token === 'invalid') {
          throw new Error('Voucher not found or invalid');
        }

        const mockVoucher: VoucherData = {
          id: token || 'mock-id',
          title: 'Umrah Travel Package',
          description: 'Complete Umrah package including flights, accommodation, and guided tours',
          validity: '2024-12-31',
          status: 'valid',
          customer: {
            name: 'Ahmad Hassan',
            email: 'ahmad.hassan@email.com'
          },
          package: {
            name: 'Premium Umrah Experience',
            destination: 'Makkah & Madinah',
            duration: '14 days',
            participants: 2
          },
          agency: {
            name: 'Nahd Travels',
            contact: '+966-XX-XXXX-XXX'
          }
        };

        setVoucher(mockVoucher);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load voucher');
      } finally {
        setLoading(false);
      }
    };

    if (token) {
      fetchVoucher();
    }
  }, [token]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-sky">
        <Spinner size="lg" />
      </div>
    );
  }

  if (error || !voucher) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4 bg-gradient-sky">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-destructive">
              <AlertCircle className="h-5 w-5" />
              Voucher Not Found
            </CardTitle>
            <CardDescription>
              {error || 'The voucher you are looking for could not be found.'}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Please check the voucher link or contact the travel agency for assistance.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const statusColor = {
    valid: 'text-success',
    expired: 'text-warning',
    used: 'text-muted-foreground'
  };

  return (
    <div className="min-h-screen p-4 bg-gradient-sky">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Header */}
        <div className="text-center space-y-2">
          <div className="flex items-center justify-center gap-2 mb-4">
            <Plane className="h-8 w-8 text-primary" />
            <h1 className="text-3xl font-bold gradient-text">Travel Voucher</h1>
          </div>
          <p className="text-muted-foreground">
            <Eye className="inline h-4 w-4 mr-1" />
            Read-only voucher view
          </p>
        </div>

        <div className="grid gap-6 md:grid-cols-2">
          {/* Voucher Details */}
          <Card className="shadow-card">
            <CardHeader>
              <CardTitle>{voucher.title}</CardTitle>
              <CardDescription>{voucher.description}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Status:</span>
                  <span className={`text-sm font-medium capitalize ${statusColor[voucher.status]}`}>
                    {voucher.status}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Valid Until:</span>
                  <span className="text-sm">{voucher.validity}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Voucher ID:</span>
                  <span className="text-sm font-mono">{voucher.id}</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* QR Code */}
          <Card className="shadow-card">
            <CardHeader>
              <CardTitle>Voucher QR Code</CardTitle>
              <CardDescription>
                Scan this code for quick verification
              </CardDescription>
            </CardHeader>
            <CardContent className="flex justify-center">
              <QRViewer 
                value={`${window.location.origin}/public/voucher/${voucher.id}`}
                size={200}
              />
            </CardContent>
          </Card>

          {/* Package Information */}
          <Card className="shadow-card">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <MapPin className="h-5 w-5" />
                Package Details
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Package:</span>
                <span className="text-sm">{voucher.package.name}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Destination:</span>
                <span className="text-sm">{voucher.package.destination}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Duration:</span>
                <span className="text-sm flex items-center gap-1">
                  <Calendar className="h-3 w-3" />
                  {voucher.package.duration}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Participants:</span>
                <span className="text-sm flex items-center gap-1">
                  <Users className="h-3 w-3" />
                  {voucher.package.participants}
                </span>
              </div>
            </CardContent>
          </Card>

          {/* Customer & Agency Info */}
          <Card className="shadow-card">
            <CardHeader>
              <CardTitle>Contact Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <h4 className="text-sm font-medium mb-2">Customer:</h4>
                <div className="text-sm text-muted-foreground space-y-1">
                  <p>{voucher.customer.name}</p>
                  <p>{voucher.customer.email}</p>
                </div>
              </div>
              <div>
                <h4 className="text-sm font-medium mb-2">Travel Agency:</h4>
                <div className="text-sm text-muted-foreground space-y-1">
                  <p>{voucher.agency.name}</p>
                  <p>{voucher.agency.contact}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Footer */}
        <div className="text-center text-sm text-muted-foreground">
          This is a digital travel voucher. Please keep this page accessible during your travel.
        </div>
      </div>
    </div>
  );
}