import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { useEffect } from "react";

// Auth
import { initializeAuth, useAuthStore } from "@/context/auth";
import { ProtectedRoute, DeveloperRoute, MemberRoute, AgentRoute } from "@/components/auth/protected-route";

// Layout
import { AppLayout } from "@/components/layout/app-layout";

// Role-based Profile Component
const RoleBasedProfile = () => {
  const { user } = useAuthStore();
  
  if (user?.role === 'developer') {
    return <DeveloperSAASProfile />;
  } else if (user?.role === 'member' || user?.role === 'agent') {
    return <MemberProfile />;
  } else {
    return <ProfilePage />;
  }
};

// Pages
import LoginPage from "@/pages/login";
import ForgotPasswordPage from "@/pages/forgot-password";
import ProfilePage from "@/pages/profile";
import PublicVoucherPage from "@/pages/public/voucher";

// Developer Pages
import DeveloperDashboard from "@/pages/developer/dashboard";
import DeveloperAgencies from "@/pages/developer/agencies";
import DeveloperUsers from "@/pages/developer/users";
import DeveloperSettings from "@/pages/developer/settings";
import SystemConfigPage from "@/pages/developer/system-config";
import DeveloperSAASProfile from "@/pages/developer/saas-profile";

// Member Pages
import MemberDashboard from "@/pages/member/dashboard";
import MemberHotels from "@/pages/member/hotels";
import MemberFlights from "@/pages/member/flights";
import MemberTransports from "@/pages/member/transports";
import MemberMutamers from "@/pages/member/mutamers";
import MemberBookings from "@/pages/member/bookings";
import MemberVouchers from "@/pages/member/vouchers";
import MemberApprovals from "@/pages/member/approvals";
import MemberLedger from "@/pages/member/ledger";
import MemberAttendance from "@/pages/member/attendance";
import MemberContacts from "@/pages/member/contacts";
import MemberProfile from "@/pages/member/profile";

// Agent Pages
import AgentDashboard from "@/pages/agent/dashboard";
import AgentBookings from "@/pages/agent/bookings";
import AgentVouchers from "@/pages/agent/vouchers";
import AgentMutamers from "@/pages/agent/mutamers";

import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

const App = () => {
  useEffect(() => {
    // Initialize authentication state on app start
    initializeAuth();
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <Toaster />
        <Sonner />
        <BrowserRouter>
          <Routes>
            {/* Public Routes */}
            <Route path="/login" element={<LoginPage />} />
            <Route path="/forgot-password" element={<ForgotPasswordPage />} />
            <Route path="/public/voucher/:token" element={<PublicVoucherPage />} />

            {/* Protected Routes with Layout */}
            <Route path="/" element={
              <ProtectedRoute>
                <AppLayout />
              </ProtectedRoute>
            }>
              {/* Root redirect to appropriate dashboard */}
              <Route index element={<Navigate to="/dashboard" replace />} />
              
              {/* Common Routes */}
              <Route path="profile" element={<RoleBasedProfile />} />
              
              {/* Auto-redirect to role-based dashboard */}
              <Route path="dashboard" element={<Navigate to="/member/dashboard" replace />} />

              {/* Developer Routes */}
              <Route path="developer">
                <Route path="dashboard" element={
                  <DeveloperRoute>
                    <DeveloperDashboard />
                  </DeveloperRoute>
                } />
                <Route path="agencies" element={
                  <DeveloperRoute>
                    <DeveloperAgencies />
                  </DeveloperRoute>
                } />
                <Route path="users" element={
                  <DeveloperRoute>
                    <DeveloperUsers />
                  </DeveloperRoute>
                } />
                <Route path="settings" element={
                  <DeveloperRoute>
                    <DeveloperSettings />
                  </DeveloperRoute>
                } />
                <Route path="system-config" element={
                  <DeveloperRoute>
                    <SystemConfigPage />
                  </DeveloperRoute>
                } />
                <Route path="saas-profile" element={
                  <DeveloperRoute>
                    <DeveloperSAASProfile />
                  </DeveloperRoute>
                } />
              </Route>

              {/* Member Routes */}
              <Route path="member">
                <Route path="dashboard" element={
                  <MemberRoute>
                    <MemberDashboard />
                  </MemberRoute>
                } />
                <Route path="hotels" element={
                  <MemberRoute>
                    <MemberHotels />
                  </MemberRoute>
                } />
                <Route path="flights" element={
                  <MemberRoute>
                    <MemberFlights />
                  </MemberRoute>
                } />
                <Route path="transports" element={
                  <MemberRoute>
                    <MemberTransports />
                  </MemberRoute>
                } />
                <Route path="mutamers" element={
                  <MemberRoute>
                    <MemberMutamers />
                  </MemberRoute>
                } />
                <Route path="bookings" element={
                  <MemberRoute>
                    <MemberBookings />
                  </MemberRoute>
                } />
                <Route path="vouchers" element={
                  <MemberRoute>
                    <MemberVouchers />
                  </MemberRoute>
                } />
                <Route path="approvals" element={
                  <MemberRoute>
                    <MemberApprovals />
                  </MemberRoute>
                } />
                <Route path="ledger" element={
                  <MemberRoute>
                    <MemberLedger />
                  </MemberRoute>
                } />
                <Route path="attendance" element={
                  <MemberRoute>
                    <MemberAttendance />
                  </MemberRoute>
                } />
                <Route path="contacts" element={
                  <MemberRoute>
                    <MemberContacts />
                  </MemberRoute>
                } />
              </Route>

              {/* Agent Routes */}
              <Route path="agent">
                <Route path="dashboard" element={
                  <AgentRoute>
                    <AgentDashboard />
                  </AgentRoute>
                } />
                <Route path="bookings" element={
                  <AgentRoute>
                    <AgentBookings />
                  </AgentRoute>
                } />
                <Route path="vouchers" element={
                  <AgentRoute>
                    <AgentVouchers />
                  </AgentRoute>
                } />
                <Route path="mutamers" element={
                  <AgentRoute>
                    <AgentMutamers />
                  </AgentRoute>
                } />
              </Route>
            </Route>

            {/* 404 Route */}
            <Route path="*" element={<NotFound />} />
          </Routes>
        </BrowserRouter>
      </TooltipProvider>
    </QueryClientProvider>
  );
};

export default App;
