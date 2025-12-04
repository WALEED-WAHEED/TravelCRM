import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { Receipt, TrendingUp, Users, MapPin, BookOpen, Calculator, CheckSquare, AlertCircle, Clock } from 'lucide-react';
import { apiClient } from '@/api/client';
import { useToast } from '@/hooks/use-toast';

interface DashboardKPIs {
  pending_vouchers: number;
  monthly_revenue: number;
  active_agents: number;
  total_mutamers: number;
  pending_vouchers_change: string;
  revenue_change: string;
  agents_change: string;
  mutamers_change: string;
}

interface RevenueData {
  month: string;
  revenue: number;
}

interface VoucherStatusData {
  status: string;
  count: number;
  [key: string]: string | number;
}

interface ActivityItem {
  id: number;
  description: string;
  timestamp: string;
  type: string;
}

const VOUCHER_COLORS = {
  Draft: 'hsl(var(--muted))',
  Pending: 'hsl(var(--warning))',
  Approved: 'hsl(var(--success))',
  Rejected: 'hsl(var(--destructive))',
};

export default function MemberDashboard() {
  const [kpis, setKpis] = useState<DashboardKPIs | null>(null);
  const [revenueData, setRevenueData] = useState<RevenueData[]>([]);
  const [voucherStats, setVoucherStats] = useState<VoucherStatusData[]>([]);
  const [activities, setActivities] = useState<ActivityItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { toast } = useToast();

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);

      const kpisRes = await apiClient.get('/api/v1/dashboard/member/');
      setKpis(kpisRes.data);
      
      // Set dummy data for other sections until APIs are implemented
      setRevenueData([
        { month: 'Jan', revenue: 15000 },
        { month: 'Feb', revenue: 18001 },
        { month: 'Mar', revenue: 22000 },
        { month: 'Apr', revenue: 19500 },
        { month: 'May', revenue: 25000 },
        { month: 'Jun', revenue: 28001 },
      ]);
      
      setVoucherStats([
        { status: 'Pending', count: kpisRes.data.pending_vouchers },
        { status: 'Approved', count: 15 },
        { status: 'Rejected', count: 3 },
      ]);
      
      setActivities([
        {
          id: 1,
          type: 'voucher',
          message: 'New voucher created for Hajj package',
          timestamp: new Date().toISOString(),
          user: 'agent1',
        },
        {
          id: 2,
          type: 'booking',
          message: 'Booking confirmed for Umrah package',
          timestamp: new Date(Date.now() - 3600000).toISOString(),
          user: 'agent2',
        },
        {
          id: 3,
          type: 'payment',
          message: 'Payment received for Hajj booking',
          timestamp: new Date(Date.now() - 7200000).toISOString(),
          user: 'system',
        },
      ]);
    } catch (err: any) {
      console.error('Dashboard fetch error:', err);
      setError('Failed to load dashboard data');
      toast({
        title: "Error",
        description: "Failed to load dashboard data. Please try again.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Member Dashboard</h1>
          <p className="text-muted-foreground">Travel operations overview and management</p>
        </div>
        <Card className="p-6">
          <div className="flex items-center space-x-2 text-destructive">
            <AlertCircle className="h-5 w-5" />
            <span>{error}</span>
          </div>
          <Button onClick={fetchDashboardData} className="mt-4">
            Retry
          </Button>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-foreground">Member Dashboard</h1>
        <p className="text-muted-foreground">Travel operations overview and management</p>
      </div>

      {/* KPI Cards */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pending Vouchers</CardTitle>
            <Receipt className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {loading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <div className="text-2xl font-bold bg-gradient-to-r from-primary to-primary/80 bg-clip-text text-transparent">
                {kpis?.pending_vouchers || 0}
              </div>
            )}
            <div className="text-xs text-muted-foreground">
              {loading ? <Skeleton className="h-4 w-20" /> : kpis?.pending_vouchers_change || 'Awaiting review'}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Monthly Revenue</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {loading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <div className="text-2xl font-bold bg-gradient-to-r from-primary to-primary/80 bg-clip-text text-transparent">
                ${(kpis?.monthly_revenue || 0).toLocaleString()}
              </div>
            )}
            <div className="text-xs text-muted-foreground">
              {loading ? <Skeleton className="h-4 w-20" /> : kpis?.revenue_change || '+0% from last month'}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Agents</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {loading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <div className="text-2xl font-bold bg-gradient-to-r from-primary to-primary/80 bg-clip-text text-transparent">
                {kpis?.active_agents || 0}
              </div>
            )}
            <div className="text-xs text-muted-foreground">
              {loading ? <Skeleton className="h-4 w-20" /> : kpis?.agents_change || 'In your agency'}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Mutamers</CardTitle>
            <MapPin className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {loading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <div className="text-2xl font-bold bg-gradient-to-r from-primary to-primary/80 bg-clip-text text-transparent">
                {kpis?.total_mutamers || 0}
              </div>
            )}
            <div className="text-xs text-muted-foreground">
              {loading ? <Skeleton className="h-4 w-20" /> : kpis?.mutamers_change || 'Total customers'}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Charts */}
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Revenue Trend</CardTitle>
            <CardDescription>Monthly revenue overview</CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <Skeleton className="h-64 w-full" />
            ) : (
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={revenueData}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis dataKey="month" className="text-muted-foreground" />
                  <YAxis className="text-muted-foreground" />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: 'hsl(var(--background))', 
                      border: '1px solid hsl(var(--border))',
                      borderRadius: '6px'
                    }} 
                  />
                  <Line type="monotone" dataKey="revenue" stroke="hsl(var(--primary))" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Vouchers by Status</CardTitle>
            <CardDescription>Distribution of voucher statuses</CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <Skeleton className="h-64 w-full" />
            ) : (
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={voucherStats}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={(entry: any) => `${entry.status}: ${(entry.percent * 100).toFixed(0)}%`}
                    outerRadius={80}
                    fill="hsl(var(--primary))"
                    dataKey="count"
                    nameKey="status"
                  >
                    {voucherStats.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={VOUCHER_COLORS[entry.status as keyof typeof VOUCHER_COLORS] || 'hsl(var(--primary))'} />
                    ))}
                  </Pie>
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: 'hsl(var(--background))', 
                      border: '1px solid hsl(var(--border))',
                      borderRadius: '6px'
                    }} 
                  />
                </PieChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Recent Activity and Quick Actions */}
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
            <CardDescription>Latest actions in your agency</CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="space-y-3">
                {[1, 2, 3, 4, 5].map((i) => (
                  <Skeleton key={i} className="h-16 w-full" />
                ))}
              </div>
            ) : activities.length > 0 ? (
              <div className="space-y-4">
                {activities.map((activity) => (
                  <div key={activity.id} className="flex items-start space-x-3 pb-3 border-b last:border-0">
                    <Clock className="h-4 w-4 text-muted-foreground mt-1" />
                    <div className="flex-1 space-y-1">
                      <p className="text-sm font-medium leading-none">
                        {activity.description}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {new Date(activity.timestamp).toLocaleString()}
                      </p>
                    </div>
                    <Badge variant="outline" className="text-xs">
                      {activity.type}
                    </Badge>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No recent activity</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
            <CardDescription>Common member tasks</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-3">
              <Button 
                asChild 
                variant="outline" 
                className="justify-start h-auto p-4"
              >
                <div className="text-left">
                  <div className="font-medium">Packages</div>
                  <div className="text-xs text-muted-foreground">Feature removed</div>
                </div>
              </Button>

              <Button 
                asChild 
                variant="outline" 
                className="justify-start h-auto p-4"
              >
                <Link to="/member/bookings">
                  <BookOpen className="mr-2 h-4 w-4" />
                  <div className="text-left">
                    <div className="font-medium">Add New Booking</div>
                    <div className="text-xs text-muted-foreground">Process customer bookings</div>
                  </div>
                </Link>
              </Button>

              <Button 
                asChild 
                variant="outline" 
                className="justify-start h-auto p-4"
              >
                <Link to="/member/ledger">
                  <Calculator className="mr-2 h-4 w-4" />
                  <div className="text-left">
                    <div className="font-medium">View Ledger Report</div>
                    <div className="text-xs text-muted-foreground">Financial overview</div>
                  </div>
                </Link>
              </Button>

              <Button 
                asChild 
                variant="outline" 
                className="justify-start h-auto p-4"
              >
                <Link to="/member/approvals">
                  <CheckSquare className="mr-2 h-4 w-4" />
                  <div className="text-left">
                    <div className="font-medium">Review Pending Vouchers</div>
                    <div className="text-xs text-muted-foreground">Approve or reject vouchers</div>
                  </div>
                </Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
