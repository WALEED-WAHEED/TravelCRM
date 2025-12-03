import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { MapPin } from 'lucide-react';

export default function AgentMutamers() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-foreground">My Mutamers</h1>
        <p className="text-muted-foreground">Manage pilgrimage participants assigned to you</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MapPin className="h-5 w-5" />
            Agent Mutamers – Coming Soon
          </CardTitle>
          <CardDescription>
            Pilgrim management for travel agents
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-sm text-muted-foreground space-y-2">
            <p>This page will include:</p>
            <ul className="ml-4 space-y-1">
              <li>• View assigned pilgrims and groups</li>
              <li>• Track visa and documentation status</li>
              <li>• Manage pilgrim communications</li>
              <li>• Update health and travel information</li>
              <li>• Generate pilgrim reports and lists</li>
            </ul>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}