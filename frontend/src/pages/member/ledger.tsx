import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Calendar } from '@/components/ui/calendar';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { toast } from '@/hooks/use-toast';
import { Plus, Download, Edit, Trash2, Calendar as CalendarIcon, TrendingUp, TrendingDown, DollarSign, Search } from 'lucide-react';
import { format } from 'date-fns';
import { cn } from '@/lib/utils';
import {
  fetchLedgerEntries,
  fetchMonthlySummary,
  createLedgerEntry,
  updateLedgerEntry,
  deleteLedgerEntry,
  exportLedger,
  LedgerEntry,
  LedgerSummary,
  LedgerFilters,
  CreateLedgerEntry,
} from '@/services/ledgerService';

export default function MemberLedger() {
  const [entries, setEntries] = useState<LedgerEntry[]>([]);
  const [summary, setSummary] = useState<LedgerSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [totalCount, setTotalCount] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  
  // Filters
  const [startDate, setStartDate] = useState<Date>();
  const [endDate, setEndDate] = useState<Date>();
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  
  // Modal states
  const [isEntryModalOpen, setIsEntryModalOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [editingEntry, setEditingEntry] = useState<LedgerEntry | null>(null);
  const [deletingEntryId, setDeletingEntryId] = useState<number | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  
  // Form data
  const [formData, setFormData] = useState<CreateLedgerEntry>({
    entry_type: 'income',
    description: '',
    amount: '',
    date: format(new Date(), 'yyyy-MM-dd'),
  });

  // Fetch entries
  const loadEntries = async () => {
    setLoading(true);
    try {
      const filters: LedgerFilters = {
        page: currentPage,
        search: searchQuery || undefined,
        type: typeFilter === 'all' ? undefined : typeFilter,
        start_date: startDate ? format(startDate, 'yyyy-MM-dd') : undefined,
        end_date: endDate ? format(endDate, 'yyyy-MM-dd') : undefined,
      };
      
      const data = await fetchLedgerEntries(filters);
      setEntries(data.results);
      setTotalCount(data.count);
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to load ledger entries',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  // Fetch summary
  const loadSummary = async () => {
    try {
      const now = new Date();
      const data = await fetchMonthlySummary(now.getFullYear(), now.getMonth() + 1);
      setSummary(data);
    } catch (error) {
      console.error('Failed to load summary:', error);
    }
  };

  useEffect(() => {
    loadEntries();
    loadSummary();
  }, [currentPage, startDate, endDate, typeFilter, searchQuery]);

  // Handle create/update
  const handleSubmit = async () => {
    if (!formData.description || !formData.amount || !formData.date) {
      toast({
        title: 'Validation Error',
        description: 'Please fill in all required fields',
        variant: 'destructive',
      });
      return;
    }

    setIsSaving(true);
    try {
      if (editingEntry) {
        await updateLedgerEntry(editingEntry.id, formData);
        toast({
          title: 'Success',
          description: 'Ledger entry updated successfully',
        });
      } else {
        await createLedgerEntry(formData);
        toast({
          title: 'Success',
          description: 'Ledger entry created successfully',
        });
      }
      setIsEntryModalOpen(false);
      resetForm();
      loadEntries();
      loadSummary();
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.response?.data?.message || 'Failed to save entry',
        variant: 'destructive',
      });
    } finally {
      setIsSaving(false);
    }
  };

  // Handle delete
  const handleDelete = async () => {
    if (!deletingEntryId) return;

    try {
      await deleteLedgerEntry(deletingEntryId);
      toast({
        title: 'Success',
        description: 'Ledger entry deleted successfully',
      });
      setIsDeleteDialogOpen(false);
      setDeletingEntryId(null);
      loadEntries();
      loadSummary();
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to delete entry',
        variant: 'destructive',
      });
    }
  };

  // Handle export
  const handleExport = async (exportFormat: 'csv' | 'xlsx') => {
    setIsExporting(true);
    try {
      const filters: LedgerFilters = {
        start_date: startDate ? format(startDate, 'yyyy-MM-dd') : undefined,
        end_date: endDate ? format(endDate, 'yyyy-MM-dd') : undefined,
        type: typeFilter === 'all' ? undefined : typeFilter,
      };
      
      const blob = await exportLedger(exportFormat, filters);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const dateStr = format(new Date(), 'yyyy-MM-dd');
      a.download = `ledger_export_${exportFormat}_${dateStr}.${exportFormat}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      toast({
        title: 'Success',
        description: `Ledger exported as ${exportFormat.toUpperCase()}`,
      });
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to export ledger',
        variant: 'destructive',
      });
    } finally {
      setIsExporting(false);
    }
  };

  // Reset form
  const resetForm = () => {
    setFormData({
      entry_type: 'income',
      description: '',
      amount: '',
      date: format(new Date(), 'yyyy-MM-dd'),
    });
    setEditingEntry(null);
  };

  // Open edit modal
  const openEditModal = (entry: LedgerEntry) => {
    setEditingEntry(entry);
    setFormData({
      entry_type: entry.entry_type,
      description: entry.description,
      amount: entry.amount,
      date: entry.date,
      booking: entry.booking,
      agent: entry.agent?.id,
    });
    setIsEntryModalOpen(true);
  };

  // Open add modal
  const openAddModal = () => {
    resetForm();
    setIsEntryModalOpen(true);
  };

  // Format currency
  const formatCurrency = (amount: string) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'SAR',
    }).format(parseFloat(amount));
  };

  // Get entry type badge
  const getTypeBadge = (type: string) => {
    const variants: Record<string, any> = {
      income: { label: 'Income', className: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300' },
      expense: { label: 'Expense', className: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300' },
      supplier_payment: { label: 'Supplier Payment', className: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-300' },
    };
    const config = variants[type] || variants.income;
    return <Badge className={config.className}>{config.label}</Badge>;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Financial Ledger</h1>
          <p className="text-muted-foreground">Track and manage financial transactions</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button onClick={openAddModal} className="gap-2">
            <Plus className="h-4 w-4" />
            Add Entry
          </Button>
          <Button
            variant="outline"
            onClick={() => handleExport('csv')}
            disabled={isExporting}
            className="gap-2"
          >
            <Download className="h-4 w-4" />
            Export CSV
          </Button>
          <Button
            variant="outline"
            onClick={() => handleExport('xlsx')}
            disabled={isExporting}
            className="gap-2"
          >
            <Download className="h-4 w-4" />
            Export XLSX
          </Button>
        </div>
      </div>

      {/* KPI Summary Cards */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Income</CardTitle>
              <TrendingUp className="h-4 w-4 text-green-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">{formatCurrency(summary.income)}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Expense</CardTitle>
              <TrendingDown className="h-4 w-4 text-red-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-600">{formatCurrency(summary.expense)}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Supplier Payments</CardTitle>
              <DollarSign className="h-4 w-4 text-orange-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-orange-600">{formatCurrency(summary.supplier_payments)}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Net Balance</CardTitle>
              <DollarSign className="h-4 w-4 text-primary" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-primary">{formatCurrency(summary.net)}</div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle>Filters</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="space-y-2">
              <Label>Start Date</Label>
              <Popover>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    className={cn(
                      'w-full justify-start text-left font-normal',
                      !startDate && 'text-muted-foreground'
                    )}
                  >
                    <CalendarIcon className="mr-2 h-4 w-4" />
                    {startDate ? format(startDate, 'PPP') : 'Pick a date'}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0" align="start">
                  <Calendar
                    mode="single"
                    selected={startDate}
                    onSelect={setStartDate}
                    initialFocus
                    className="pointer-events-auto"
                  />
                </PopoverContent>
              </Popover>
            </div>

            <div className="space-y-2">
              <Label>End Date</Label>
              <Popover>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    className={cn(
                      'w-full justify-start text-left font-normal',
                      !endDate && 'text-muted-foreground'
                    )}
                  >
                    <CalendarIcon className="mr-2 h-4 w-4" />
                    {endDate ? format(endDate, 'PPP') : 'Pick a date'}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0" align="start">
                  <Calendar
                    mode="single"
                    selected={endDate}
                    onSelect={setEndDate}
                    initialFocus
                    className="pointer-events-auto"
                  />
                </PopoverContent>
              </Popover>
            </div>

            <div className="space-y-2">
              <Label>Type</Label>
              <Select value={typeFilter} onValueChange={setTypeFilter}>
                <SelectTrigger>
                  <SelectValue placeholder="All Types" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Types</SelectItem>
                  <SelectItem value="income">Income</SelectItem>
                  <SelectItem value="expense">Expense</SelectItem>
                  <SelectItem value="supplier_payment">Supplier Payment</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Search</Label>
              <div className="relative">
                <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search description..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-8"
                />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Ledger Table */}
      <Card>
        <CardHeader>
          <CardTitle>Ledger Entries</CardTitle>
          <CardDescription>Total: {totalCount} entries</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="space-y-2">
              {[...Array(5)].map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : entries.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              No ledger entries found. Click "Add Entry" to create one.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Date</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Description</TableHead>
                    <TableHead className="text-right">Amount</TableHead>
                    <TableHead>Agent</TableHead>
                    <TableHead>Booking</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {entries.map((entry) => (
                    <TableRow key={entry.id}>
                      <TableCell>{format(new Date(entry.date), 'PP')}</TableCell>
                      <TableCell>{getTypeBadge(entry.entry_type)}</TableCell>
                      <TableCell>{entry.description}</TableCell>
                      <TableCell
                        className={cn(
                          'text-right font-medium',
                          entry.entry_type === 'income'
                            ? 'text-green-600'
                            : 'text-red-600'
                        )}
                      >
                        {formatCurrency(entry.amount)}
                      </TableCell>
                      <TableCell>{entry.agent?.username || '-'}</TableCell>
                      <TableCell>{entry.booking ? `#${entry.booking}` : '-'}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-2">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => openEditModal(entry)}
                          >
                            <Edit className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              setDeletingEntryId(entry.id);
                              setIsDeleteDialogOpen(true);
                            }}
                          >
                            <Trash2 className="h-4 w-4 text-destructive" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}

          {/* Pagination */}
          {totalCount > 10 && (
            <div className="flex justify-center gap-2 mt-4">
              <Button
                variant="outline"
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                disabled={currentPage === 1}
              >
                Previous
              </Button>
              <span className="flex items-center px-4">
                Page {currentPage} of {Math.ceil(totalCount / 10)}
              </span>
              <Button
                variant="outline"
                onClick={() => setCurrentPage((p) => p + 1)}
                disabled={currentPage >= Math.ceil(totalCount / 10)}
              >
                Next
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Add/Edit Entry Modal */}
      <Dialog open={isEntryModalOpen} onOpenChange={setIsEntryModalOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>{editingEntry ? 'Edit Entry' : 'Add New Entry'}</DialogTitle>
            <DialogDescription>
              {editingEntry ? 'Update the ledger entry details' : 'Create a new ledger entry'}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Date *</Label>
              <Input
                type="date"
                value={formData.date}
                onChange={(e) => setFormData({ ...formData, date: e.target.value })}
              />
            </div>

            <div className="space-y-2">
              <Label>Type *</Label>
              <Select
                value={formData.entry_type}
                onValueChange={(value: any) => setFormData({ ...formData, entry_type: value })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="income">Income</SelectItem>
                  <SelectItem value="expense">Expense</SelectItem>
                  <SelectItem value="supplier_payment">Supplier Payment</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Amount *</Label>
              <Input
                type="number"
                step="0.01"
                placeholder="0.00"
                value={formData.amount}
                onChange={(e) => setFormData({ ...formData, amount: e.target.value })}
              />
            </div>

            <div className="space-y-2">
              <Label>Description *</Label>
              <Input
                placeholder="Enter description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setIsEntryModalOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSubmit} disabled={isSaving}>
              {isSaving ? 'Saving...' : editingEntry ? 'Update' : 'Create'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Ledger Entry?</AlertDialogTitle>
            <AlertDialogDescription>
              This action cannot be undone. This will permanently delete the ledger entry from the system.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
