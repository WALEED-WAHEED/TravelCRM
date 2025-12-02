import React, { useState, useEffect } from 'react';
import { Navigate, Link } from 'react-router-dom';
import { useAuthStore } from '@/context/auth';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent } from '@/components/ui/card';
import { Spinner } from '@/components/ui/spinner';
import { Plane, MapPin } from 'lucide-react';
import { toast } from '@/hooks/use-toast';

export default function LoginPage() {
  const { login, isAuthenticated, isLoading, user } = useAuthStore();
  const [formData, setFormData] = useState({
    username: '',
    password: '',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Redirect if already authenticated
  if (isAuthenticated && user) {
    const redirectMap = {
      developer: '/developer/dashboard',
      member: '/member/dashboard',
      agent: '/agent/dashboard',
    };
    return <Navigate to={redirectMap[user.role]} replace />;
  }

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (!formData.username.trim()) {
      newErrors.username = 'Username is required';
    }

    if (!formData.password) {
      newErrors.password = 'Password is required';
    } else if (formData.password.length < 3) {
      newErrors.password = 'Password must be at least 3 characters';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);
    
    try {
      const success = await login(formData.username, formData.password);
      
      if (success) {
        toast({
          title: "Welcome back!",
          description: "You have been successfully logged in.",
        });
      }
    } catch (error) {
      // Error handling is done in the auth store
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    
    // Clear errors on input change
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: '' }));
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center login-bg">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 login-bg">
      <Card className="w-full max-w-4xl shadow-elevated border-0 bg-card/95 backdrop-blur-sm">
        <CardContent className="p-0">
          <div className="grid lg:grid-cols-2 min-h-[600px]">
            {/* Left Panel - Branding */}
            <div className="bg-gradient-primary p-8 lg:p-12 flex flex-col justify-center text-white relative overflow-hidden">
              <div className="absolute inset-0 bg-black/10" />
              <div className="relative z-10">
                <div className="flex items-center gap-3 mb-8">
                  <div className="bg-white/20 p-3 rounded-lg backdrop-blur-sm">
                    <Plane className="h-8 w-8" />
                  </div>
                  <div>
                    <h1 className="text-3xl font-bold">Nahd Travels</h1>
                    <p className="text-white/90 text-sm">Travel Management System</p>
                  </div>
                </div>
                
                <div className="space-y-6">
                  <div>
                    <h2 className="text-2xl font-semibold mb-3">
                      Your Journey Begins Here
                    </h2>
                    <p className="text-white/90 text-lg leading-relaxed">
                      Streamline your travel operations with our comprehensive 
                      management platform designed for travel agencies, agents, and administrators.
                    </p>
                  </div>

                  <div className="flex items-center gap-2 text-white/80">
                    <MapPin className="h-5 w-5" />
                    <span>Connecting destinations worldwide</span>
                  </div>
                </div>

                {/* Decorative elements */}
                <div className="absolute -bottom-6 -right-6 w-32 h-32 bg-white/10 rounded-full" />
                <div className="absolute -top-12 -left-6 w-24 h-24 bg-white/5 rounded-full" />
              </div>
            </div>

            {/* Right Panel - Login Form */}
            <div className="p-8 lg:p-12 flex flex-col justify-center">
              <div className="w-full max-w-sm mx-auto">
                <div className="text-center mb-8">
                  <h3 className="text-2xl font-semibold text-foreground mb-2">
                    Welcome Back
                  </h3>
                  <p className="text-muted-foreground">
                    Sign in to access your travel management dashboard
                  </p>
                </div>

                <form onSubmit={handleSubmit} className="space-y-6">
                  <div className="space-y-2">
                    <label htmlFor="username" className="text-sm font-medium text-foreground">
                      Username
                    </label>
                    <Input
                      id="username"
                      name="username"
                      type="text"
                      placeholder="Enter your username"
                      value={formData.username}
                      onChange={handleInputChange}
                      className={errors.username ? 'border-destructive' : ''}
                      disabled={isSubmitting}
                      autoComplete="username"
                    />
                    {errors.username && (
                      <p className="text-sm text-destructive">{errors.username}</p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <label htmlFor="password" className="text-sm font-medium text-foreground">
                      Password
                    </label>
                    <Input
                      id="password"
                      name="password"
                      type="password"
                      placeholder="Enter your password"
                      value={formData.password}
                      onChange={handleInputChange}
                      className={errors.password ? 'border-destructive' : ''}
                      disabled={isSubmitting}
                      showPasswordToggle
                      autoComplete="current-password"
                    />
                    {errors.password && (
                      <p className="text-sm text-destructive">{errors.password}</p>
                    )}
                  </div>

                  <Button
                    type="submit"
                    variant="gradient"
                    className="w-full"
                    disabled={isSubmitting}
                  >
                    {isSubmitting ? (
                      <>
                        <Spinner size="sm" className="mr-2" />
                        Signing In...
                      </>
                    ) : (
                      'Sign In'
                    )}
                  </Button>
                </form>

                <div className="mt-6 text-center space-y-4">
                  <Link
                    to="/forgot-password"
                    className="text-sm text-primary hover:text-primary-light transition-colors"
                  >
                    Forgot your password?
                  </Link>
                  
                  <div className="text-sm text-muted-foreground">
                    Don't have credentials?{' '}
                    <span className="text-foreground font-medium">
                      Contact your agency administrator
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}