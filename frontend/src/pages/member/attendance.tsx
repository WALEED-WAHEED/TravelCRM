import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Calendar } from '@/components/ui/calendar';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { toast } from '@/hooks/use-toast';
import { Clock, Calendar as CalendarIcon, MapPin, User, Plus, Edit, Trash2, Download, Search, Filter } from 'lucide-react';
import { format } from 'date-fns';
import { cn } from '@/lib/utils';
import apiClient from '@/api/client';

interface AttendanceLog {
  id: number;
  user: {
    id: number;
    username: string;
    email: string;
  };
  date: string;
  status: 'present' | 'absent' | 'late' | 'leave';
  check_in_time?: string;
  check_out_time?: string;
  work_hours?: number;
  location: string;
  notes: string;
  created_at: string;
  updated_at: string;
}

interface AttendanceSummary {
  total_logs: number;
  summary: {
    present?: number;
    absent?: number;
    late?: number;
    leave?: number;
  };
}

export default function MemberAttendance() {
  const [attendanceLogs, setAttendanceLogs] = useState<AttendanceLog[]>([]);
  const [summary, setSummary] = useState<AttendanceSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [dateFilter, setDateFilter] = useState<Date>();
  
  // Modal states
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [editingLog, setEditingLog] = useState<AttendanceLog | null>(null);
  const [deletingLogId, setDeletingLogId] = useState<number | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  
  // Form data
  const [formData, setFormData] = useState({
    user_id: '',
    date: '',
    status: 'present' as 'present' | 'absent' | 'late' | 'leave',
    check_in_time: '',
    check_out_time: '',
    work_hours: '',
    location: '',
    notes: '',
  });

  // Fetch attendance logs
  const fetchAttendanceLogs = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      
      if (statusFilter !== 'all') {
        params.append('status', statusFilter);
      }
      if (searchQuery) {
        params.append('search', searchQuery);
      }
      if (dateFilter) {
        params.append('date', format(dateFilter, 'yyyy-MM-dd'));
      }

      const response = await apiClient.get(`/api/v1/attendance/attendance/?${params.toString()}`);
      const logsData = Array.isArray(response.data) ? response.data : response.data.results || [];
      setAttendanceLogs(logsData);
    } catch (error) {
      console.error('Failed to fetch attendance logs:', error);
      setAttendanceLogs([]);
      toast({
        title: 'Error',
        description: 'Failed to load attendance logs',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  // Fetch summary
  const fetchSummary = async () => {
    try {
      const response = await apiClient.get('/api/v1/attendance/attendance/summary/');
      setSummary(response.data);
    } catch (error) {
      console.error('Failed to load summary:', error);
    }
  };

  useEffect(() => {
    fetchAttendanceLogs();
    fetchSummary();
  }, [statusFilter, searchQuery, dateFilter]);

  // Handle create/update
  const handleSubmit = async () => {
    try {
      setIsSaving(true);

      const payload = {
        ...formData,
        user_id: formData.user_id ? parseInt(formData.user_id) : null,
        work_hours: formData.work_hours ? parseFloat(formData.work_hours) : null,
      };

      if (editingLog) {
        await apiClient.patch(`/api/v1/attendance/attendance/${editingLog.id}/`, payload);
        toast({
          title: 'Success',
          description: 'Attendance log updated successfully',
        });
      } else {
        await apiClient.post('/api/v1/attendance/attendance/', payload);
        toast({
          title: 'Success',
          description: 'Attendance log created successfully',
        });
      }

      setIsCreateModalOpen(false);
      setIsEditModalOpen(false);
      setEditingLog(null);
      resetForm();
      fetchAttendanceLogs();
      fetchSummary();
    } catch (error: any) {
      console.error('Failed to save attendance log:', error);
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to save attendance log',
        variant: 'destructive',
      });
    } finally {
      setIsSaving(false);
    }
  };

  // Handle delete
  const handleDelete = async () => {
    if (!deletingLogId) return;

    try {
      await apiClient.delete(`/api/v1/attendance/attendance/${deletingLogId}/`);
      toast({
        title: 'Success',
        description: 'Attendance log deleted successfully',
      });
      fetchAttendanceLogs();
      fetchSummary();
    } catch (error: any) {
      console.error('Failed to delete attendance log:', error);
      toast({
        title: 'Error',
        description: 'Failed to delete attendance log',
        variant: 'destructive',
      });
    } finally {
      setIsDeleteDialogOpen(false);
      setDeletingLogId(null);
    }
  };

  // Reset form
  const resetForm = () => {
    setFormData({
      user_id: '',
      date: '',
      status: 'present',
      check_in_time: '',
      check_out_time: '',
      work_hours: '',
      location: '',
      notes: '',
    });
  };

  // Open edit modal
  const openEditModal = (log: AttendanceLog) => {
    setEditingLog(log);
    setFormData({
      user_id: log.user.id.toString(),
      date: log.date,
      status: log.status,
      check_in_time: log.check_in_time || '',
      check_out_time: log.check_out_time || '',
      work_hours: log.work_hours?.toString() || '',
      location: log.location,
      notes: log.notes,
    });
    setIsEditModalOpen(true);
  };

  // Open delete dialog
  const openDeleteDialog = (logId: number) => {
    setDeletingLogId(logId);
    setIsDeleteDialogOpen(true);
  };

  // Export data
  const handleExport = async (format: 'csv' | 'xlsx') => {
    try {
      const response = await apiClient.get(`/api/v1/attendance/attendance/export/?format=${format}`, {
        responseType: 'blob',
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `attendance.${format}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      
      toast({
        title: 'Success',
        description: `Attendance data exported as ${format.toUpperCase()}`,
      });
    } catch (error) {
      console.error('Export failed:', error);
      toast({
        title: 'Error',
        description: 'Failed to export attendance data',
        variant: 'destructive',
      });
    }
  };

  // Get status badge
  const getStatusBadge = (status: string) => {
    const variants = {
      present: 'default',
      absent: 'destructive',
      late: 'secondary',
      leave: 'outline',
    } as const;
    
    const labels = {
      present: 'Present',
      absent: 'Absent',
      late: 'Late',
      leave: 'Leave',
    };

    return (
      <Badge variant={variants[status as keyof typeof variants] || 'default'}>
        {labels[status as keyof typeof labels] || status}
      </Badge>
    );
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Attendance Tracking</h1>
          <p className="text-muted-foreground">Monitor staff attendance and schedules</p>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => setIsCreateModalOpen(true)}>
            <Plus className="w-4 h-4 mr-2" />
            Add Attendance
          </Button>
          <Button variant="outline" onClick={() => handleExport('csv')}>
            <Download className="w-4 h-4 mr-2" />
            Export CSV
          </Button>
          <Button variant="outline" onClick={() => handleExport('xlsx')}>
            <Download className="w-4 h-4 mr-2" />
            Export XLSX
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Logs</CardTitle>
              <Clock className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{summary.total_logs}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Present</CardTitle>
              <User className="h-4 w-4 text-green-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">{summary.summary.present || 0}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Absent</CardTitle>
              <User className="h-4 w-4 text-red-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-600">{summary.summary.absent || 0}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Late</CardTitle>
              <User className="h-4 w-4 text-yellow-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-yellow-600">{summary.summary.late || 0}</div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Filter className="w-5 h-5" />
            Filters
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="space-y-2">
              <Label>Search</Label>
              <div className="relative">
                <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search by user..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Status</Label>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger>
                  <SelectValue placeholder="All Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="present">Present</SelectItem>
                  <SelectItem value="absent">Absent</SelectItem>
                  <SelectItem value="late">Late</SelectItem>
                  <SelectItem value="leave">Leave</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Date</Label>
              <Popover>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    className={cn(
                      "w-full justify-start text-left font-normal",
                      !dateFilter && "text-muted-foreground"
                    )}
                  >
                    <CalendarIcon className="mr-2 h-4 w-4" />
                    {dateFilter ? format(dateFilter, "PPP") : "Pick a date"}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0" align="start">
                  <Calendar
                    mode="single"
                    selected={dateFilter}
                    onSelect={setDateFilter}
                    initialFocus
                  />
                </PopoverContent>
              </Popover>
            </div>
            <div className="space-y-2">
              <Label>&nbsp;</Label>
              <Button 
                variant="outline" 
                onClick={() => {
                  setSearchQuery('');
                  setStatusFilter('all');
                  setDateFilter(undefined);
                }}
                className="w-full"
              >
                Clear Filters
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Attendance Logs Table */}
      <Card>
        <CardHeader>
          <CardTitle>Attendance Logs</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="space-y-4">
              {[...Array(5)].map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : attendanceLogs.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              No attendance logs found. Click "Add Attendance" to create one.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>User</TableHead>
                    <TableHead>Date</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Check In</TableHead>
                    <TableHead>Check Out</TableHead>
                    <TableHead>Work Hours</TableHead>
                    <TableHead>Location</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(attendanceLogs || []).map((log) => (
                    <TableRow key={log.id}>
                      <TableCell className="font-medium">{log.user.username}</TableCell>
                      <TableCell>{format(new Date(log.date), 'PPP')}</TableCell>
                      <TableCell>{getStatusBadge(log.status)}</TableCell>
                      <TableCell>{log.check_in_time || '-'}</TableCell>
                      <TableCell>{log.check_out_time || '-'}</TableCell>
                      <TableCell>{log.work_hours ? `${log.work_hours}h` : '-'}</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1">
                          <MapPin className="w-3 h-3" />
                          {log.location || '-'}
                        </div>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => openEditModal(log)}
                          >
                            <Edit className="w-4 h-4" />
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => openDeleteDialog(log.id)}
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create/Edit Modal */}
      <Dialog open={isCreateModalOpen || isEditModalOpen} onOpenChange={(open) => {
        if (!open) {
          setIsCreateModalOpen(false);
          setIsEditModalOpen(false);
          setEditingLog(null);
          resetForm();
        }
      }}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>
              {editingLog ? 'Edit Attendance Log' : 'Add Attendance Log'}
            </DialogTitle>
          </DialogHeader>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="user_id">User ID</Label>
              <Input
                id="user_id"
                type="number"
                value={formData.user_id}
                onChange={(e) => setFormData({ ...formData, user_id: e.target.value })}
                placeholder="Enter user ID"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="date">Date</Label>
              <Input
                id="date"
                type="date"
                value={formData.date}
                onChange={(e) => setFormData({ ...formData, date: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="status">Status</Label>
              <Select value={formData.status} onValueChange={(value: any) => setFormData({ ...formData, status: value })}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="present">Present</SelectItem>
                  <SelectItem value="absent">Absent</SelectItem>
                  <SelectItem value="late">Late</SelectItem>
                  <SelectItem value="leave">Leave</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="check_in_time">Check In Time</Label>
              <Input
                id="check_in_time"
                type="time"
                value={formData.check_in_time}
                onChange={(e) => setFormData({ ...formData, check_in_time: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="check_out_time">Check Out Time</Label>
              <Input
                id="check_out_time"
                type="time"
                value={formData.check_out_time}
                onChange={(e) => setFormData({ ...formData, check_out_time: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="work_hours">Work Hours</Label>
              <Input
                id="work_hours"
                type="number"
                step="0.5"
                value={formData.work_hours}
                onChange={(e) => setFormData({ ...formData, work_hours: e.target.value })}
                placeholder="8.0"
              />
            </div>
            <div className="space-y-2 md:col-span-2">
              <Label htmlFor="location">Location</Label>
              <Input
                id="location"
                value={formData.location}
                onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                placeholder="Office, Remote, etc."
              />
            </div>
            <div className="space-y-2 md:col-span-2">
              <Label htmlFor="notes">Notes</Label>
              <Textarea
                id="notes"
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                placeholder="Additional notes..."
                rows={3}
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => {
              setIsCreateModalOpen(false);
              setIsEditModalOpen(false);
              setEditingLog(null);
              resetForm();
            }}>
              Cancel
            </Button>
            <Button onClick={handleSubmit} disabled={isSaving}>
              {isSaving ? 'Saving...' : (editingLog ? 'Update' : 'Create')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Are you sure?</AlertDialogTitle>
            <AlertDialogDescription>
              This action cannot be undone. This will permanently delete the attendance log.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete}>Delete</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}