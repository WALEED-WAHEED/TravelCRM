import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useAuthStore } from '@/context/auth';
import { User, Mail, Building2, Shield } from 'lucide-react';

export default function ProfilePage() {
  const { user } = useAuthStore();

  if (!user) {
    return null;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-foreground">Profile & Settings</h1>
        <p className="text-muted-foreground">Manage your account information and preferences</p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <User className="h-5 w-5" />
              Personal Information
            </CardTitle>
            <CardDescription>
              Update your personal details and contact information
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <label className="text-sm font-medium">First Name</label>
                <Input defaultValue={user.first_name} placeholder="First name" />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Last Name</label>
                <Input defaultValue={user.last_name} placeholder="Last name" />
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Email Address</label>
              <Input type="email" defaultValue={user.email} placeholder="Email address" />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Username</label>
              <Input defaultValue={user.username} placeholder="Username" disabled />
            </div>
            <Button className="w-full">Update Profile</Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5" />
              Account Information
            </CardTitle>
            <CardDescription>
              View your account details and role information
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Role</label>
              <div className="p-3 bg-muted rounded-md">
                <span className="text-sm font-medium capitalize">{user.role}</span>
              </div>
            </div>
            {user.agency && (
              <div className="space-y-2">
                <label className="text-sm font-medium">Agency</label>
                <div className="p-3 bg-muted rounded-md flex items-center gap-2">
                  <Building2 className="h-4 w-4" />
                  <span className="text-sm">{user.agency.name}</span>
                </div>
              </div>
            )}
            <div className="space-y-2">
              <label className="text-sm font-medium">Account Status</label>
              <div className="p-3 bg-muted rounded-md">
                <span className={`text-sm font-medium ${user.is_active ? 'text-success' : 'text-destructive'}`}>
                  {user.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Change Password</CardTitle>
            <CardDescription>
              Update your account password for security
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Current Password</label>
              <Input type="password" placeholder="Enter current password" />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">New Password</label>
              <Input type="password" placeholder="Enter new password" />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Confirm New Password</label>
              <Input type="password" placeholder="Confirm new password" />
            </div>
            <Button className="w-full">Change Password</Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Profile – Coming Soon</CardTitle>
            <CardDescription>
              Enhanced profile features and settings
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-sm text-muted-foreground space-y-2">
              <p>Additional features will include:</p>
              <ul className="ml-4 space-y-1">
                <li>• Profile photo upload</li>
                <li>• Notification preferences</li>
                <li>• Two-factor authentication</li>
                <li>• API access keys</li>
                <li>• Activity log and audit trail</li>
              </ul>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}