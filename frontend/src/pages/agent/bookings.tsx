import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { BookOpen } from 'lucide-react';

export default function AgentBookings() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-foreground">My Bookings</h1>
        <p className="text-muted-foreground">Manage your travel bookings and reservations</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BookOpen className="h-5 w-5" />
            Agent Bookings – Coming Soon
          </CardTitle>
          <CardDescription>
            Personal booking management for agents
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-sm text-muted-foreground space-y-2">
            <p>This page will include:</p>
            <ul className="ml-4 space-y-1">
              <li>• View and manage your bookings</li>
              <li>• Create new travel reservations</li>
              <li>• Track booking status and confirmations</li>
              <li>• Customer communication tools</li>
              <li>• Commission tracking per booking</li>
            </ul>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}