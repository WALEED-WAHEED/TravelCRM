import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Receipt } from 'lucide-react';

export default function AgentVouchers() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-foreground">My Vouchers</h1>
        <p className="text-muted-foreground">Create and manage travel vouchers for your clients</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Receipt className="h-5 w-5" />
            Agent Vouchers – Coming Soon
          </CardTitle>
          <CardDescription>
            Agent voucher creation and management
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-sm text-muted-foreground space-y-2">
            <p>This page will include:</p>
            <ul className="ml-4 space-y-1">
              <li>• Generate travel vouchers for clients</li>
              <li>• QR code and digital voucher creation</li>
              <li>• Voucher validation and tracking</li>
              <li>• PDF export and printing options</li>
              <li>• Usage analytics and reporting</li>
            </ul>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}