import React from 'react';
import { Link } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Plane, ArrowLeft } from 'lucide-react';

export default function ForgotPasswordPage() {
  return (
    <div className="min-h-screen flex items-center justify-center p-4 login-bg">
      <Card className="w-full max-w-md shadow-elevated">
        <CardHeader className="text-center">
          <div className="flex items-center justify-center gap-2 mb-4">
            <Plane className="h-6 w-6 text-primary" />
            <span className="gradient-text text-xl font-semibold">Nahd Travels</span>
          </div>
          <CardTitle>Forgot Password</CardTitle>
          <CardDescription>
            Enter your email address and we'll send you a link to reset your password.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-2">
            <label htmlFor="email" className="text-sm font-medium">
              Email Address
            </label>
            <Input
              id="email"
              type="email"
              placeholder="Enter your email address"
              autoComplete="email"
            />
          </div>

          <Button className="w-full" variant="gradient">
            Send Reset Link
          </Button>

          <div className="text-center">
            <Link
              to="/login"
              className="text-sm text-primary hover:text-primary-light transition-colors inline-flex items-center gap-1"
            >
              <ArrowLeft className="h-3 w-3" />
              Back to Login
            </Link>
          </div>

          <div className="text-center text-sm text-muted-foreground">
            <p>Remember your password?</p>
            <p>
              Don't have an account?{' '}
              <span className="text-foreground font-medium">
                Contact your agency administrator
              </span>
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}