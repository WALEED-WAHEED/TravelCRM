import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from '@/components/ui/sidebar';
import { useAuthStore } from '@/context/auth';
import {
  LayoutDashboard,
  Building2,
  Users,
  Settings,
  Hotel,
  Plane,
  Car,
  MapPin,
  BookOpen,
  Receipt,
  CheckSquare,
  Calculator,
  ClipboardList,
  Clock,
  Contact,
  User,
  Eye,
} from 'lucide-react';

// Navigation items by role
const navigationItems = {
  developer: [
    {
      title: "Dashboard",
      url: "/developer/dashboard",
      icon: LayoutDashboard,
    },
    {
      title: "Agencies",
      url: "/developer/agencies",
      icon: Building2,
    },
    {
      title: "Users",
      url: "/developer/users",
      icon: Users,
    },
    {
      title: "Settings",
      url: "/developer/settings",
      icon: Settings,
    },
  ],
  member: [
    {
      title: "Dashboard",
      url: "/member/dashboard",
      icon: LayoutDashboard,
    },
    {
      title: "Hotels",
      url: "/member/hotels",
      icon: Hotel,
    },
    {
      title: "Flights",
      url: "/member/flights",
      icon: Plane,
    },
    {
      title: "Transports",
      url: "/member/transports",
      icon: Car,
    },
    {
      title: "Mutamers",
      url: "/member/mutamers",
      icon: MapPin,
    },
    {
      title: "Bookings",
      url: "/member/bookings",
      icon: BookOpen,
    },
    {
      title: "Vouchers",
      url: "/member/vouchers",
      icon: Receipt,
    },
    {
      title: "Approvals",
      url: "/member/approvals",
      icon: CheckSquare,
    },
    {
      title: "Ledger",
      url: "/member/ledger",
      icon: Calculator,
    },
    {
      title: "Attendance",
      url: "/member/attendance",
      icon: Clock,
    },
    {
      title: "Contacts",
      url: "/member/contacts",
      icon: Contact,
    },
  ],
  agent: [
    {
      title: "Dashboard",
      url: "/agent/dashboard",
      icon: LayoutDashboard,
    },
    {
      title: "Bookings",
      url: "/agent/bookings",
      icon: BookOpen,
    },
    {
      title: "Vouchers",
      url: "/agent/vouchers",
      icon: Receipt,
    },
    {
      title: "Mutamers",
      url: "/agent/mutamers",
      icon: MapPin,
    },
  ],
};

export function AppSidebar() {
  const { user } = useAuthStore();
  const { state } = useSidebar();
  const location = useLocation();
  
  const collapsed = state === "collapsed";

  if (!user) return null;

  const items = navigationItems[user.role] || [];
  const currentPath = location.pathname;

  const isActive = (path: string) => currentPath === path;
  const getNavClasses = ({ isActive }: { isActive: boolean }) =>
    isActive 
      ? "bg-sidebar-accent text-sidebar-accent-foreground font-medium" 
      : "hover:bg-sidebar-accent/50 text-sidebar-foreground";

  return (
    <Sidebar className={collapsed ? "w-16" : "w-64"}>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel className={collapsed ? "sr-only" : ""}>
            {user.role === 'developer' && "Developer Tools"}
            {user.role === 'member' && "Member Portal"}
            {user.role === 'agent' && "Agent Tools"}
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {items.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton asChild>
                    <NavLink 
                      to={item.url} 
                      className={getNavClasses}
                      end
                    >
                      <item.icon className="h-4 w-4 shrink-0" />
                      {!collapsed && <span>{item.title}</span>}
                    </NavLink>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        {/* Profile link */}
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton asChild>
                  <NavLink 
                    to="/profile" 
                    className={getNavClasses}
                  >
                    <User className="h-4 w-4 shrink-0" />
                    {!collapsed && <span>Profile</span>}
                  </NavLink>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
    </Sidebar>
  );
}