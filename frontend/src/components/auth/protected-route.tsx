import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '@/context/auth';
import { Spinner } from '@/components/ui/spinner';

interface ProtectedRouteProps {
  children: React.ReactNode;
  allowedRoles?: ('developer' | 'member' | 'agent')[];
  redirectTo?: string;
}

export function ProtectedRoute({ 
  children, 
  allowedRoles,
  redirectTo = '/login' 
}: ProtectedRouteProps) {
  const { isAuthenticated, user, isLoading } = useAuthStore();
  const location = useLocation();

  // Show loading spinner while checking auth status
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated || !user) {
    return <Navigate to={redirectTo} state={{ from: location }} replace />;
  }

  // Check role-based access
  if (allowedRoles && !allowedRoles.includes(user.role)) {
    // Redirect to appropriate dashboard based on user role
    const roleRedirectMap = {
      developer: '/developer/dashboard',
      member: '/member/dashboard',
      agent: '/agent/dashboard'
    };
    
    return <Navigate to={roleRedirectMap[user.role]} replace />;
  }

  return <>{children}</>;
}

// Convenient wrapper components for each role
export function DeveloperRoute({ children }: { children: React.ReactNode }) {
  return (
    <ProtectedRoute allowedRoles={['developer']}>
      {children}
    </ProtectedRoute>
  );
}

export function MemberRoute({ children }: { children: React.ReactNode }) {
  return (
    <ProtectedRoute allowedRoles={['member']}>
      {children}
    </ProtectedRoute>
  );
}

export function AgentRoute({ children }: { children: React.ReactNode }) {
  return (
    <ProtectedRoute allowedRoles={['agent']}>
      {children}
    </ProtectedRoute>
  );
}