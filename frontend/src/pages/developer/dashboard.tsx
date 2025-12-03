import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';
import { Building2, Users, Settings, Activity, Plus, UserPlus, AlertCircle } from 'lucide-react';
import { apiClient } from '@/api/client';
import { useToast } from '@/hooks/use-toast';

interface DashboardKPIs {
  total_agencies: number;
  total_users: number;
  active_sessions: number;
  system_health: number;
  agencies_change: string;
  users_change: string;
  sessions_change: string;
}

// interface LedgerData {
//   month: string;
//   income: number;
//   expenses: number;
// }

// interface VoucherStats {
//   status: string;
//   count: number;
// }

interface RecentAgency {
  id: number;
  name: string;
  contact_email: string;
  created_at: string;
  is_active: boolean;
}

export default function DeveloperDashboard() {
  const [kpis, setKpis] = useState<DashboardKPIs | null>(null);
  // const [ledgerData, setLedgerData] = useState<LedgerData[]>([]);
  // const [voucherStats, setVoucherStats] = useState<VoucherStats[]>([]);
  const [recentAgencies, setRecentAgencies] = useState<RecentAgency[]>([]);
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

      // const [kpisRes, ledgerRes, vouchersRes, agenciesRes] = await Promise.all([
      const [kpisRes, agenciesRes] = await Promise.all([
        apiClient.get('/api/v1/dashboard/developer/'),
        // apiClient.get('/api/v1/ledger/summary/'),
        // apiClient.get('/api/v1/vouchers/stats/'),
        apiClient.get('/api/v1/agencies/?ordering=-created_at&limit=5')
      ]);

      setKpis(kpisRes.data);
      // setLedgerData(ledgerRes.data);
      // setVoucherStats(vouchersRes.data);
      setRecentAgencies(agenciesRes.data.results || agenciesRes.data);
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
          <h1 className="text-3xl font-bold text-foreground">Developer Dashboard</h1>
          <p className="text-muted-foreground">System overview and management tools</p>
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
        <h1 className="text-3xl font-bold text-foreground">Developer Dashboard</h1>
        <p className="text-muted-foreground">System overview and management tools</p>
      </div>

      {/* KPIs */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Agencies</CardTitle>
            <Building2 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {loading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <div className="text-2xl font-bold bg-gradient-to-r from-primary to-primary/80 bg-clip-text text-transparent">
                {kpis?.total_agencies || 0}
              </div>
            )}
            <p className="text-xs text-muted-foreground">
              {loading ? <Skeleton className="h-4 w-20" /> : kpis?.agencies_change || '+0 from last month'}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Users</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {loading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <div className="text-2xl font-bold bg-gradient-to-r from-primary to-primary/80 bg-clip-text text-transparent">
                {kpis?.total_users || 0}
              </div>
            )}
            <p className="text-xs text-muted-foreground">
              {loading ? <Skeleton className="h-4 w-20" /> : kpis?.users_change || '+0 from last month'}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Sessions</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {loading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <div className="text-2xl font-bold bg-gradient-to-r from-primary to-primary/80 bg-clip-text text-transparent">
                {kpis?.active_sessions || 0}
              </div>
            )}
            <p className="text-xs text-muted-foreground">
              {loading ? <Skeleton className="h-4 w-20" /> : kpis?.sessions_change || '+0% from last hour'}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">System Health</CardTitle>
            <Settings className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {loading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <div className="text-2xl font-bold text-success">
                {kpis?.system_health ? `${kpis.system_health}%` : '99.9%'}
              </div>
            )}
            <p className="text-xs text-muted-foreground">
              Uptime this month
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Charts */}
      {/* <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Income vs Expenses</CardTitle>
            <CardDescription>Monthly financial overview</CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <Skeleton className="h-64 w-full" />
            ) : (
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={ledgerData}>
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
                  <Line type="monotone" dataKey="income" stroke="hsl(var(--primary))" strokeWidth={2} />
                  <Line type="monotone" dataKey="expenses" stroke="hsl(var(--destructive))" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Vouchers by Status</CardTitle>
            <CardDescription>Current voucher distribution</CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <Skeleton className="h-64 w-full" />
            ) : (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={voucherStats}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis dataKey="status" className="text-muted-foreground" />
                  <YAxis className="text-muted-foreground" />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: 'hsl(var(--background))', 
                      border: '1px solid hsl(var(--border))',
                      borderRadius: '6px'
                    }} 
                  />
                  <Bar dataKey="count" fill="hsl(var(--primary))" />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div> */}

      {/* Recent Agencies and Quick Actions */}
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Recent Agencies</CardTitle>
            <CardDescription>Latest agency registrations</CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="space-y-2">
                {[1, 2, 3, 4, 5].map((i) => (
                  <Skeleton key={i} className="h-12 w-full" />
                ))}
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Email</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {recentAgencies.map((agency) => (
                    <TableRow key={agency.id} className="hover:bg-muted/50">
                      <TableCell className="font-medium">
                        <Link 
                          to={`/developer/agencies`} 
                          className="text-primary hover:underline"
                        >
                          {agency.name}
                        </Link>
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {agency.contact_email}
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {new Date(agency.created_at).toLocaleDateString()}
                      </TableCell>
                      <TableCell>
                        <Badge variant={agency.is_active ? "default" : "secondary"}>
                          {agency.is_active ? "Active" : "Inactive"}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
            <CardDescription>Common developer tasks</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-3">
              <Button 
                asChild 
                variant="outline" 
                className="justify-start h-auto p-4"
              >
                <Link to="/developer/agencies">
                  <Plus className="mr-2 h-4 w-4" />
                  <div className="text-left">
                    <div className="font-medium">Create New Agency</div>
                    <div className="text-xs text-muted-foreground">Add a new travel agency</div>
                  </div>
                </Link>
              </Button>

              <Button 
                asChild 
                variant="outline" 
                className="justify-start h-auto p-4"
              >
                <Link to="/developer/users">
                  <UserPlus className="mr-2 h-4 w-4" />
                  <div className="text-left">
                    <div className="font-medium">Add System User</div>
                    <div className="text-xs text-muted-foreground">Create new user account</div>
                  </div>
                </Link>
              </Button>

              <Button 
                asChild 
                variant="outline" 
                className="justify-start h-auto p-4"
              >
                <Link to="/developer/settings">
                  <Settings className="mr-2 h-4 w-4" />
                  <div className="text-left">
                    <div className="font-medium">Configure Settings</div>
                    <div className="text-xs text-muted-foreground">System branding & configuration</div>
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