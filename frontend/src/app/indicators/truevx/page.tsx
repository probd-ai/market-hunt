'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { 
  Play, 
  Square, 
  RefreshCw, 
  Database, 
  TrendingUp, 
  Clock, 
  CheckCircle, 
  XCircle, 
  AlertCircle,
  Trash2,
  Download,
  ArrowLeft,
  Search,
  Users,
  User,
  Calendar,
  Settings,
  Grid,
  List,
  Eye,
  Home,
  Menu,
  X,
  LayoutDashboard,
  ChartBar
} from 'lucide-react';
import Link from 'next/link';

// Types
interface BatchJob {
  job_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  symbols?: string[];
  indicator_type: string;
  base_symbol: string;
  parameters: Record<string, any>;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  completion_percentage?: number;
  error_message?: string;
  is_active: boolean;
  total_points?: number;
}

interface StoredIndicator {
  symbol: string;
  symbol_name?: string;
  indicator_type: string;
  base_symbol: string;
  parameters: Record<string, any>;
  total_points: number;
  date_range: {
    start: string;
    end: string;
  };
  last_updated: string;
  status: string;
  latest_values?: {
    date: string;
    truevx_score: number;
    mean_short: number;
    mean_mid: number;
    mean_long: number;
    structural_score: number;
    trend_score: number;
  };
}

interface AvailableSymbol {
  symbol: string;
  name: string;
  sector?: string;
  last_updated?: string;
}

// Simple UI Components
const Label = ({ children, htmlFor }: { children: React.ReactNode; htmlFor?: string }) => (
  <label htmlFor={htmlFor} className="block text-sm font-medium text-gray-700 mb-1">
    {children}
  </label>
);

const Badge = ({ 
  children, 
  variant = 'default',
  className 
}: { 
  children: React.ReactNode; 
  variant?: 'default' | 'secondary' | 'outline';
  className?: string;
}) => {
  const baseClasses = 'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium';
  const variantClasses = {
    default: 'bg-blue-100 text-blue-800',
    secondary: 'bg-gray-100 text-gray-800',
    outline: 'border border-gray-300 text-gray-700'
  };
  
  return (
    <span className={`${baseClasses} ${variantClasses[variant]} ${className || ''}`}>
      {children}
    </span>
  );
};

const Progress = ({ value, className }: { value: number; className?: string }) => (
  <div className={`w-full bg-gray-200 rounded-full h-2 ${className || ''}`}>
    <div 
      className="bg-blue-600 h-full rounded-full transition-all duration-300" 
      style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
    />
  </div>
);

const Alert = ({ 
  children, 
  variant = 'default' 
}: { 
  children: React.ReactNode; 
  variant?: 'default' | 'destructive';
}) => {
  const baseClasses = 'p-4 rounded-md border';
  const variantClasses = {
    default: 'bg-blue-50 border-blue-200 text-blue-800',
    destructive: 'bg-red-50 border-red-200 text-red-800'
  };
  
  return (
    <div className={`${baseClasses} ${variantClasses[variant]}`}>
      {children}
    </div>
  );
};

const AlertDescription = ({ children }: { children: React.ReactNode }) => (
  <div className="flex items-center gap-2">
    {children}
  </div>
);

const TrueVXManagementPage = () => {
  // State management
  const [activeTab, setActiveTab] = useState<'calculate' | 'jobs' | 'stored'>('calculate');
  const [calculationType, setCalculationType] = useState<'single' | 'all'>('single');
  const [viewMode, setViewMode] = useState<'grid' | 'table'>('grid'); // New state for view toggle
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  
  // Data states
  const [batchJobs, setBatchJobs] = useState<BatchJob[]>([]);
  const [storedIndicators, setStoredIndicators] = useState<StoredIndicator[]>([]);
  const [availableSymbols, setAvailableSymbols] = useState<AvailableSymbol[]>([]);
  
  // Form states
  const [selectedSymbol, setSelectedSymbol] = useState('');
  const [symbolSearch, setSymbolSearch] = useState('');
  const [baseSymbol, setBaseSymbol] = useState('Nifty 50');
  const [dateRange, setDateRange] = useState<'full' | 'custom'>('full');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [s1, setS1] = useState(22);
  const [m2, setM2] = useState(66);
  const [l3, setL3] = useState(222);

  // Auto-refresh for active jobs
  useEffect(() => {
    const interval = setInterval(() => {
      if (batchJobs.some(job => job.is_active)) {
        fetchBatchJobs();
      }
    }, 3000);
    
    return () => clearInterval(interval);
  }, [batchJobs]);

  // Initial data fetch
  useEffect(() => {
    fetchBatchJobs();
    fetchStoredIndicators();
    fetchAvailableSymbols();
    
    // Set default date range to last 2 years
    const endDate = new Date();
    const startDate = new Date();
    startDate.setFullYear(endDate.getFullYear() - 2);
    
    setStartDate(startDate.toISOString().split('T')[0]);
    setEndDate(endDate.toISOString().split('T')[0]);
  }, []);

  // API calls
  const fetchBatchJobs = async () => {
    try {
      const response = await fetch('/api/indicators/batch');
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      setBatchJobs(data.jobs || []);
      if (error?.includes('fetch batch jobs')) setError(null);
    } catch (error) {
      console.error('Failed to fetch batch jobs:', error);
      setError('Failed to fetch batch jobs. Please check if the backend is running.');
      setBatchJobs([]);
    }
  };

  const fetchStoredIndicators = async () => {
    try {
      const response = await fetch('/api/indicators/stored');
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      setStoredIndicators(data.indicators || []);
      if (error?.includes('fetch stored indicators')) setError(null);
    } catch (error) {
      console.error('Failed to fetch stored indicators:', error);
      setError('Failed to fetch stored indicators. Please check if the backend is running.');
      setStoredIndicators([]);
    }
  };

  const fetchAvailableSymbols = async () => {
    try {
      const response = await fetch('/api/stock/available');
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      
      const data = await response.json();
      if (data.success && data.symbols) {
        setAvailableSymbols(data.symbols);
        console.log(`Loaded ${data.symbols.length} symbols from backend`);
        return;
      }
      
      throw new Error('Invalid response format');
    } catch (error) {
      console.error('Failed to fetch available symbols:', error);
      // Use fallback mock data
      const mockSymbols = [
        { symbol: 'TCS', name: 'Tata Consultancy Services', sector: 'IT' },
        { symbol: 'INFY', name: 'Infosys Ltd', sector: 'IT' },
        { symbol: 'RELIANCE', name: 'Reliance Industries', sector: 'Oil & Gas' },
        { symbol: 'HDFCBANK', name: 'HDFC Bank', sector: 'Banking' },
        { symbol: 'ICICIBANK', name: 'ICICI Bank', sector: 'Banking' },
        { symbol: 'KOTAKBANK', name: 'Kotak Mahindra Bank', sector: 'Banking' },
        { symbol: 'HINDUNILVR', name: 'Hindustan Unilever', sector: 'FMCG' },
        { symbol: 'ITC', name: 'ITC Ltd', sector: 'FMCG' },
        { symbol: 'LT', name: 'Larsen & Toubro', sector: 'Engineering' },
        { symbol: 'SBIN', name: 'State Bank of India', sector: 'Banking' }
      ];
      setAvailableSymbols(mockSymbols);
      console.log('Using fallback mock data due to API error');
    }
  };

  const submitCalculation = async () => {
    setIsLoading(true);
    setError(null);
    setSuccess(null);
    
    try {
      let symbols: string[] = [];
      
      if (calculationType === 'single') {
        if (!selectedSymbol) {
          throw new Error('Please select a symbol');
        }
        symbols = [selectedSymbol];
      } else {
        // For 'all', use all available symbols
        symbols = availableSymbols.map(s => s.symbol);
        if (symbols.length === 0) {
          throw new Error('No symbols available for calculation');
        }
      }

      const requestData = {
        symbols,
        indicator_type: 'truevx',
        base_symbol: baseSymbol,
        start_date: dateRange === 'full' ? '' : startDate,
        end_date: dateRange === 'full' ? '' : endDate,
        parameters: { s1, m2, l3 }
      };

      const response = await fetch('/api/indicators/batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestData),
      });
      
      if (!response.ok) {
        throw new Error(`Failed to submit calculation: ${response.statusText}`);
      }
      
      const result = await response.json();
      setSuccess(
        `TrueValueX calculation started for ${symbols.length} symbol${symbols.length > 1 ? 's' : ''}! Job ID: ${result.job_id}`
      );
      fetchBatchJobs();
      setActiveTab('jobs'); // Switch to jobs tab to see progress
      
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Failed to submit calculation');
    } finally {
      setIsLoading(false);
    }
  };

  const cancelJob = async (jobId: string) => {
    try {
      const response = await fetch(`/api/indicators/batch/${jobId}`, {
        method: 'DELETE',
      });
      
      if (response.ok) {
        setSuccess('Job cancelled successfully');
        fetchBatchJobs();
      } else {
        throw new Error('Failed to cancel job');
      }
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Failed to cancel job');
    }
  };

  // Filter symbols based on search
  const filteredSymbols = availableSymbols.filter(symbol =>
    symbol.symbol.toLowerCase().includes(symbolSearch.toLowerCase()) ||
    symbol.name.toLowerCase().includes(symbolSearch.toLowerCase())
  );

  // Helper functions
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-green-500 text-white';
      case 'running': return 'bg-blue-500 text-white';
      case 'failed': return 'bg-red-500 text-white';
      case 'cancelled': return 'bg-gray-500 text-white';
      default: return 'bg-yellow-500 text-white';
    }
  };
  
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return <CheckCircle className="h-4 w-4" />;
      case 'running': return <RefreshCw className="h-4 w-4 animate-spin" />;
      case 'failed': return <XCircle className="h-4 w-4" />;
      case 'cancelled': return <Square className="h-4 w-4" />;
      default: return <Clock className="h-4 w-4" />;
    }
  };
  
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="flex gap-2">
            <Link href="/">
              <Button variant="outline" size="sm">
                <Home className="h-4 w-4 mr-1" />
                Dashboard
              </Button>
            </Link>
            <Link href="/indicators">
              <Button variant="outline" size="sm">
                <ArrowLeft className="h-4 w-4 mr-1" />
                Back to Indicators
              </Button>
            </Link>
          </div>
          <div>
            <h1 className="text-3xl font-bold flex items-center gap-2">
              <TrendingUp className="h-8 w-8 text-blue-600" />
              TrueValueX Management
            </h1>
            <p className="text-gray-600 mt-2">
              Calculate and manage TrueValueX indicator for individual stocks or entire portfolios
            </p>
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex gap-2">
        <Button
          variant={activeTab === 'calculate' ? 'primary' : 'outline'}
          onClick={() => setActiveTab('calculate')}
          className="flex items-center gap-2"
        >
          <Settings className="h-4 w-4" />
          Calculate
        </Button>
        <Button
          variant={activeTab === 'jobs' ? 'primary' : 'outline'}
          onClick={() => setActiveTab('jobs')}
          className="flex items-center gap-2"
        >
          <RefreshCw className="h-4 w-4" />
          Jobs
          <Badge variant="secondary">{batchJobs.length}</Badge>
        </Button>
        <Button
          variant={activeTab === 'stored' ? 'primary' : 'outline'}
          onClick={() => setActiveTab('stored')}
          className="flex items-center gap-2"
        >
          <Database className="h-4 w-4" />
          Stored Data
          <Badge variant="secondary">{storedIndicators.length}</Badge>
        </Button>
      </div>

      {/* Alerts */}
      {error && (
        <Alert variant="destructive">
          <AlertDescription>
            <AlertCircle className="h-4 w-4" />
            {error}
          </AlertDescription>
        </Alert>
      )}
      
      {success && (
        <Alert>
          <AlertDescription>
            <CheckCircle className="h-4 w-4" />
            {success}
          </AlertDescription>
        </Alert>
      )}

      {/* Calculate Tab */}
      {activeTab === 'calculate' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Calculation Configuration */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Settings className="h-5 w-5" />
                Calculation Configuration
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Calculation Type */}
              <div>
                <Label>Calculation Type</Label>
                <div className="grid grid-cols-2 gap-4 mt-2">
                  <Button
                    variant={calculationType === 'single' ? 'primary' : 'outline'}
                    onClick={() => setCalculationType('single')}
                    className="flex items-center gap-2 h-auto p-4"
                  >
                    <User className="h-5 w-5" />
                    <div className="text-left">
                      <div className="font-medium">Single Symbol</div>
                      <div className="text-xs opacity-70">Calculate for one stock</div>
                    </div>
                  </Button>
                  <Button
                    variant={calculationType === 'all' ? 'primary' : 'outline'}
                    onClick={() => setCalculationType('all')}
                    className="flex items-center gap-2 h-auto p-4"
                  >
                    <Users className="h-5 w-5" />
                    <div className="text-left">
                      <div className="font-medium">All Symbols</div>
                      <div className="text-xs opacity-70">Calculate for all stocks</div>
                    </div>
                  </Button>
                </div>
              </div>

              {/* Symbol Selection (for single) */}
              {calculationType === 'single' && (
                <div>
                  <Label htmlFor="symbolSearch">Select Symbol</Label>
                  <div className="space-y-2">
                    <div className="relative">
                      <Search className="h-4 w-4 absolute left-3 top-3 text-gray-400" />
                      <Input
                        id="symbolSearch"
                        placeholder="Search symbols..."
                        value={symbolSearch}
                        onChange={(e) => setSymbolSearch(e.target.value)}
                        className="pl-10"
                      />
                    </div>
                    <div className="max-h-48 overflow-y-auto border rounded-md">
                      {filteredSymbols.map((symbol) => (
                        <div
                          key={symbol.symbol}
                          className={`p-3 cursor-pointer border-b last:border-b-0 hover:bg-gray-50 ${
                            selectedSymbol === symbol.symbol ? 'bg-blue-50 border-blue-200' : ''
                          }`}
                          onClick={() => {
                            setSelectedSymbol(symbol.symbol);
                            setSymbolSearch('');
                          }}
                        >
                          <div className="flex justify-between items-center">
                            <div>
                              <div className="font-medium">{symbol.symbol}</div>
                              <div className="text-sm text-gray-600">{symbol.name}</div>
                            </div>
                            {symbol.sector && (
                              <Badge variant="outline" className="text-xs">
                                {symbol.sector}
                              </Badge>
                            )}
                          </div>
                        </div>
                      ))}
                      {filteredSymbols.length === 0 && symbolSearch && (
                        <div className="p-4 text-center text-gray-500">
                          No symbols found matching "{symbolSearch}"
                        </div>
                      )}
                      {!symbolSearch && filteredSymbols.length > 0 && (
                        <div className="p-2 text-center text-gray-500 text-sm border-t">
                          Showing all {filteredSymbols.length} symbols
                        </div>
                      )}
                    </div>
                    {selectedSymbol && (
                      <div className="p-2 bg-blue-50 rounded border border-blue-200">
                        <strong>Selected:</strong> {selectedSymbol}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Summary for all symbols */}
              {calculationType === 'all' && (
                <div className="p-4 bg-green-50 rounded border border-green-200">
                  <div className="flex items-center gap-2 text-green-800">
                    <Users className="h-4 w-4" />
                    <strong>Will calculate for {availableSymbols.length} symbols</strong>
                  </div>
                  <div className="text-sm text-green-600 mt-1">
                    This will process all available stocks in the database
                  </div>
                </div>
              )}

              {/* Base Symbol */}
              <div>
                <Label htmlFor="baseSymbol">Base Symbol (Benchmark)</Label>
                <Input
                  id="baseSymbol"
                  value={baseSymbol}
                  onChange={(e) => setBaseSymbol(e.target.value)}
                  placeholder="Nifty 50"
                />
              </div>

              {/* Date Range */}
              <div>
                <Label>Date Range</Label>
                <div className="grid grid-cols-2 gap-4 mt-2">
                  <Button
                    variant={dateRange === 'full' ? 'primary' : 'outline'}
                    onClick={() => setDateRange('full')}
                    className="flex items-center gap-2 h-auto p-4"
                  >
                    <Calendar className="h-5 w-5" />
                    <div className="text-left">
                      <div className="font-medium">Full Range</div>
                      <div className="text-xs opacity-70">All available data</div>
                    </div>
                  </Button>
                  <Button
                    variant={dateRange === 'custom' ? 'primary' : 'outline'}
                    onClick={() => setDateRange('custom')}
                    className="flex items-center gap-2 h-auto p-4"
                  >
                    <Calendar className="h-5 w-5" />
                    <div className="text-left">
                      <div className="font-medium">Custom Range</div>
                      <div className="text-xs opacity-70">Select specific dates</div>
                    </div>
                  </Button>
                </div>
              </div>

              {/* Custom Date Range */}
              {dateRange === 'custom' && (
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="startDate">Start Date</Label>
                    <Input
                      id="startDate"
                      type="date"
                      value={startDate}
                      onChange={(e) => setStartDate(e.target.value)}
                    />
                  </div>
                  <div>
                    <Label htmlFor="endDate">End Date</Label>
                    <Input
                      id="endDate"
                      type="date"
                      value={endDate}
                      onChange={(e) => setEndDate(e.target.value)}
                    />
                  </div>
                </div>
              )}

              {/* Parameters */}
              <div>
                <Label>TrueValueX Parameters</Label>
                <div className="grid grid-cols-3 gap-4 mt-2">
                  <div>
                    <Label htmlFor="s1">S1 (Alpha)</Label>
                    <Input
                      id="s1"
                      type="number"
                      value={s1.toString()}
                      onChange={(e) => setS1(Number(e.target.value))}
                      min="1"
                      max="100"
                    />
                    <div className="text-xs text-gray-500 mt-1">Short-term (22)</div>
                  </div>
                  <div>
                    <Label htmlFor="m2">M2 (Beta)</Label>
                    <Input
                      id="m2"
                      type="number"
                      value={m2.toString()}
                      onChange={(e) => setM2(Number(e.target.value))}
                      min="1"
                      max="200"
                    />
                    <div className="text-xs text-gray-500 mt-1">Mid-term (66)</div>
                  </div>
                  <div>
                    <Label htmlFor="l3">L3 (Gamma)</Label>
                    <Input
                      id="l3"
                      type="number"
                      value={l3.toString()}
                      onChange={(e) => setL3(Number(e.target.value))}
                      min="1"
                      max="500"
                    />
                    <div className="text-xs text-gray-500 mt-1">Long-term (222)</div>
                  </div>
                </div>
              </div>

              {/* Submit Button */}
              <Button
                onClick={submitCalculation}
                disabled={isLoading || (calculationType === 'single' && !selectedSymbol)}
                className="w-full"
                size="lg"
              >
                {isLoading ? (
                  <>
                    <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                    Starting Calculation...
                  </>
                ) : (
                  <>
                    <Play className="h-4 w-4 mr-2" />
                    Start TrueValueX Calculation
                  </>
                )}
              </Button>
            </CardContent>
          </Card>

          {/* Information Panel */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="h-5 w-5" />
                TrueValueX Information
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <h4 className="font-medium text-gray-900 mb-2">About TrueValueX</h4>
                <p className="text-sm text-gray-600 leading-relaxed">
                  TrueValueX is an advanced ranking system that combines structural and trend analysis 
                  to evaluate stocks against benchmark indices. It uses multi-timeframe analysis with 
                  three key parameters for comprehensive market assessment.
                </p>
              </div>

              <div>
                <h4 className="font-medium text-gray-900 mb-2">Key Features</h4>
                <ul className="space-y-1 text-sm text-gray-600">
                  <li className="flex items-start gap-2">
                    <span className="text-green-500 mt-0.5">•</span>
                    Multi-timeframe analysis (Alpha, Beta, Gamma)
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-green-500 mt-0.5">•</span>
                    Structural and trend scoring methodology
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-green-500 mt-0.5">•</span>
                    Benchmark comparison against indices
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-green-500 mt-0.5">•</span>
                    Real-time calculation and storage
                  </li>
                </ul>
              </div>

              <div>
                <h4 className="font-medium text-gray-900 mb-2">Parameters</h4>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600">S1 (Alpha):</span>
                    <span className="font-medium">{s1} periods</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">M2 (Beta):</span>
                    <span className="font-medium">{m2} periods</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">L3 (Gamma):</span>
                    <span className="font-medium">{l3} periods</span>
                  </div>
                </div>
              </div>

              <div>
                <h4 className="font-medium text-gray-900 mb-2">Calculation Time</h4>
                <div className="space-y-1 text-sm text-gray-600">
                  <div>Single symbol: ~2-5 seconds</div>
                  <div>All symbols ({availableSymbols.length}): ~{Math.ceil(availableSymbols.length * 3 / 60)} minutes</div>
                </div>
              </div>

              <div className="p-3 bg-yellow-50 rounded border border-yellow-200">
                <div className="text-yellow-800 text-sm">
                  <strong>Note:</strong> Calculations run in the background. You can monitor progress 
                  in the Jobs tab and access results in the Stored Data tab once completed.
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Jobs Tab */}
      {activeTab === 'jobs' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <RefreshCw className="h-5 w-5" />
              TrueValueX Jobs
              <Badge variant="secondary">{batchJobs.length}</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {batchJobs.length === 0 ? (
                <div className="text-center py-12">
                  <RefreshCw className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-500">No calculation jobs found</p>
                  <p className="text-sm text-gray-400 mb-4">
                    Start a new calculation to see jobs here
                  </p>
                  <Button onClick={() => setActiveTab('calculate')}>
                    Start New Calculation
                  </Button>
                </div>
              ) : (
                <div className="space-y-4">
                  {batchJobs.map((job) => (
                    <div key={job.job_id} className="border rounded-lg p-4 space-y-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          {getStatusIcon(job.status)}
                          <Badge className={getStatusColor(job.status)}>
                            {job.status.toUpperCase()}
                          </Badge>
                          <span className="text-sm text-gray-500">
                            {job.symbols?.length || 0} symbols
                          </span>
                        </div>
                        {(job.is_active || job.status === 'running') && (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => cancelJob(job.job_id)}
                          >
                            <Square className="h-4 w-4 mr-1" />
                            Cancel
                          </Button>
                        )}
                      </div>
                      
                      {job.status === 'running' && (
                        <div>
                          <div className="flex justify-between text-sm text-gray-600 mb-1">
                            <span>Progress</span>
                            <span>{(job.completion_percentage || 0).toFixed(1)}%</span>
                          </div>
                          <Progress value={job.completion_percentage || 0} />
                        </div>
                      )}
                      
                      <div className="text-sm text-gray-600">
                        <p><strong>Base:</strong> {job.base_symbol}</p>
                        <p><strong>Created:</strong> {formatDate(job.created_at)}</p>
                        {job.completed_at && (
                          <p><strong>Completed:</strong> {formatDate(job.completed_at)}</p>
                        )}
                        {job.error_message && (
                          <p className="text-red-600"><strong>Error:</strong> {job.error_message}</p>
                        )}
                      </div>
                      
                      <div className="flex flex-wrap gap-1">
                        {job.symbols?.slice(0, 8).map((symbol) => (
                          <Badge key={symbol} variant="outline" className="text-xs">
                            {symbol}
                          </Badge>
                        )) || []}
                        {(job.symbols?.length || 0) > 8 && (
                          <Badge variant="outline" className="text-xs">
                            +{(job.symbols?.length || 0) - 8} more
                          </Badge>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Stored Data Tab */}
      {activeTab === 'stored' && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <Database className="h-5 w-5" />
                Stored TrueValueX Data
                <Badge variant="secondary">{storedIndicators.length}</Badge>
              </CardTitle>
              
              {/* View Toggle */}
              <div className="flex gap-2">
                <Button
                  variant={viewMode === 'grid' ? 'primary' : 'outline'}
                  size="sm"
                  onClick={() => setViewMode('grid')}
                  className="flex items-center gap-2"
                >
                  <Grid className="h-4 w-4" />
                  Grid
                </Button>
                <Button
                  variant={viewMode === 'table' ? 'primary' : 'outline'}
                  size="sm"
                  onClick={() => setViewMode('table')}
                  className="flex items-center gap-2"
                >
                  <List className="h-4 w-4" />
                  Table
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {storedIndicators.length === 0 ? (
                <div className="text-center py-12">
                  <Database className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-500">No stored TrueValueX data found</p>
                  <p className="text-sm text-gray-400 mb-4">
                    Complete calculations to see stored data here
                  </p>
                  <Button onClick={() => setActiveTab('calculate')}>
                    Start New Calculation
                  </Button>
                </div>
              ) : (
                <>
                  {/* Grid View */}
                  {viewMode === 'grid' && (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {storedIndicators.map((indicator, index) => {
                        // Get symbol name from available symbols
                        const symbolInfo = availableSymbols.find(s => s.symbol === indicator.symbol);
                        const symbolName = symbolInfo?.name || indicator.symbol_name || indicator.symbol;
                        
                        return (
                          <div key={index} className="border rounded-lg p-4 space-y-3 hover:shadow-md transition-shadow">
                            <div className="flex items-center justify-between">
                              <div>
                                <h3 className="font-semibold text-lg">{indicator.symbol}</h3>
                                <p className="text-sm text-gray-600 truncate" title={symbolName}>
                                  {symbolName}
                                </p>
                              </div>
                              <Badge className="bg-blue-500 text-white">
                                TrueVX
                              </Badge>
                            </div>
                            
                            <div className="text-sm text-gray-600 space-y-2">
                              <div className="flex justify-between">
                                <span className="font-medium">Base Symbol:</span>
                                <span>{indicator.base_symbol}</span>
                              </div>
                              
                              <div className="flex justify-between">
                                <span className="font-medium">From Date:</span>
                                <span>{new Date(indicator.date_range.start).toLocaleDateString()}</span>
                              </div>
                              
                              <div className="flex justify-between">
                                <span className="font-medium">Latest Date:</span>
                                <span>{new Date(indicator.date_range.end).toLocaleDateString()}</span>
                              </div>
                              
                              <div className="flex justify-between">
                                <span className="font-medium">Data Points:</span>
                                <span className="text-blue-600 font-medium">{indicator.total_points.toLocaleString()}</span>
                              </div>
                              
                              {/* Latest TrueValueX Components */}
                              {indicator.latest_values && (
                                <div className="bg-blue-50 rounded p-3 mt-3 space-y-2">
                                  <div className="text-blue-800 font-medium text-sm mb-2">
                                    Latest Indicators ({new Date(indicator.latest_values.date).toLocaleDateString()})
                                  </div>
                                  
                                  <div className="grid grid-cols-2 gap-2 text-xs">
                                    <div className="flex justify-between">
                                      <span className="text-blue-700">TrueVX:</span>
                                      <span className="font-bold text-blue-900">
                                        {indicator.latest_values.truevx_score?.toFixed(2) || 'N/A'}
                                      </span>
                                    </div>
                                    
                                    <div className="flex justify-between">
                                      <span className="text-blue-700">Structural:</span>
                                      <span className="font-medium text-blue-800">
                                        {indicator.latest_values.structural_score?.toFixed(2) || 'N/A'}
                                      </span>
                                    </div>
                                    
                                    <div className="flex justify-between">
                                      <span className="text-blue-700">Trend:</span>
                                      <span className="font-medium text-blue-800">
                                        {indicator.latest_values.trend_score?.toFixed(2) || 'N/A'}
                                      </span>
                                    </div>
                                    
                                    <div className="flex justify-between">
                                      <span className="text-blue-700">Short MA:</span>
                                      <span className="font-medium text-green-700">
                                        {indicator.latest_values.mean_short?.toFixed(2) || 'N/A'}
                                      </span>
                                    </div>
                                    
                                    <div className="flex justify-between">
                                      <span className="text-blue-700">Mid MA:</span>
                                      <span className="font-medium text-orange-600">
                                        {indicator.latest_values.mean_mid?.toFixed(2) || 'N/A'}
                                      </span>
                                    </div>
                                    
                                    <div className="flex justify-between">
                                      <span className="text-blue-700">Long MA:</span>
                                      <span className="font-medium text-red-600">
                                        {indicator.latest_values.mean_long?.toFixed(2) || 'N/A'}
                                      </span>
                                    </div>
                                  </div>
                                </div>
                              )}
                              
                              <div className="flex justify-between text-xs">
                                <span className="font-medium">Last Updated:</span>
                                <span>{new Date(indicator.last_updated).toLocaleString()}</span>
                              </div>
                            </div>
                            
                            <div className="flex gap-2">
                              <Button size="sm" variant="outline" className="flex-1">
                                <Eye className="h-4 w-4 mr-1" />
                                View
                              </Button>
                              <Button size="sm" variant="outline" className="flex-1">
                                <Download className="h-4 w-4 mr-1" />
                                Export
                              </Button>
                              <Button size="sm" variant="outline" className="text-red-600 hover:text-red-700">
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}

                  {/* Table View */}
                  {viewMode === 'table' && (
                    <div className="overflow-x-auto">
                      <table className="w-full border-collapse border border-gray-200 text-sm">
                        <thead>
                          <tr className="bg-gray-50">
                            <th className="border border-gray-200 px-3 py-2 text-left font-medium text-gray-900">
                              Symbol
                            </th>
                            <th className="border border-gray-200 px-3 py-2 text-left font-medium text-gray-900">
                              Symbol Name
                            </th>
                            <th className="border border-gray-200 px-3 py-2 text-left font-medium text-gray-900">
                              Base Symbol
                            </th>
                            <th className="border border-gray-200 px-3 py-2 text-left font-medium text-gray-900">
                              From Date
                            </th>
                            <th className="border border-gray-200 px-3 py-2 text-left font-medium text-gray-900">
                              Latest Date
                            </th>
                            <th className="border border-gray-200 px-3 py-2 text-left font-medium text-gray-900">
                              Data Points
                            </th>
                            <th className="border border-gray-200 px-3 py-2 text-center font-medium text-gray-900">
                              TrueVX Score
                            </th>
                            <th className="border border-gray-200 px-3 py-2 text-center font-medium text-gray-900">
                              Structural
                            </th>
                            <th className="border border-gray-200 px-3 py-2 text-center font-medium text-gray-900">
                              Trend
                            </th>
                            <th className="border border-gray-200 px-3 py-2 text-center font-medium text-gray-900">
                              Short MA
                            </th>
                            <th className="border border-gray-200 px-3 py-2 text-center font-medium text-gray-900">
                              Mid MA
                            </th>
                            <th className="border border-gray-200 px-3 py-2 text-center font-medium text-gray-900">
                              Long MA
                            </th>
                            <th className="border border-gray-200 px-3 py-2 text-left font-medium text-gray-900">
                              Last Updated
                            </th>
                            <th className="border border-gray-200 px-3 py-2 text-center font-medium text-gray-900">
                              Actions
                            </th>
                          </tr>
                        </thead>
                        <tbody>
                          {storedIndicators.map((indicator, index) => {
                            // Get symbol name from available symbols
                            const symbolInfo = availableSymbols.find(s => s.symbol === indicator.symbol);
                            const symbolName = symbolInfo?.name || indicator.symbol_name || indicator.symbol;
                            
                            return (
                              <tr key={index} className="hover:bg-gray-50">
                                <td className="border border-gray-200 px-3 py-2">
                                  <div className="flex items-center gap-2">
                                    <span className="font-medium">{indicator.symbol}</span>
                                    <Badge variant="outline" className="text-xs">TrueVX</Badge>
                                  </div>
                                </td>
                                <td className="border border-gray-200 px-3 py-2">
                                  <span className="text-sm" title={symbolName}>
                                    {symbolName.length > 25 ? `${symbolName.substring(0, 25)}...` : symbolName}
                                  </span>
                                </td>
                                <td className="border border-gray-200 px-3 py-2 text-sm">
                                  {indicator.base_symbol}
                                </td>
                                <td className="border border-gray-200 px-3 py-2 text-sm">
                                  {new Date(indicator.date_range.start).toLocaleDateString()}
                                </td>
                                <td className="border border-gray-200 px-3 py-2 text-sm">
                                  {new Date(indicator.date_range.end).toLocaleDateString()}
                                </td>
                                <td className="border border-gray-200 px-3 py-2 text-sm">
                                  <span className="text-blue-600 font-medium">
                                    {indicator.total_points.toLocaleString()}
                                  </span>
                                </td>
                                
                                {/* TrueVX Score */}
                                <td className="border border-gray-200 px-3 py-2 text-center">
                                  {indicator.latest_values?.truevx_score ? (
                                    <span className="font-bold text-blue-900">
                                      {indicator.latest_values.truevx_score.toFixed(2)}
                                    </span>
                                  ) : (
                                    <span className="text-gray-400 text-sm">N/A</span>
                                  )}
                                </td>
                                
                                {/* Structural Score */}
                                <td className="border border-gray-200 px-3 py-2 text-center">
                                  {indicator.latest_values?.structural_score ? (
                                    <span className="font-medium text-purple-700">
                                      {indicator.latest_values.structural_score.toFixed(2)}
                                    </span>
                                  ) : (
                                    <span className="text-gray-400 text-sm">N/A</span>
                                  )}
                                </td>
                                
                                {/* Trend Score */}
                                <td className="border border-gray-200 px-3 py-2 text-center">
                                  {indicator.latest_values?.trend_score ? (
                                    <span className="font-medium text-indigo-700">
                                      {indicator.latest_values.trend_score.toFixed(2)}
                                    </span>
                                  ) : (
                                    <span className="text-gray-400 text-sm">N/A</span>
                                  )}
                                </td>
                                
                                {/* Short MA */}
                                <td className="border border-gray-200 px-3 py-2 text-center">
                                  {indicator.latest_values?.mean_short ? (
                                    <span className="font-medium text-green-700">
                                      {indicator.latest_values.mean_short.toFixed(2)}
                                    </span>
                                  ) : (
                                    <span className="text-gray-400 text-sm">N/A</span>
                                  )}
                                </td>
                                
                                {/* Mid MA */}
                                <td className="border border-gray-200 px-3 py-2 text-center">
                                  {indicator.latest_values?.mean_mid ? (
                                    <span className="font-medium text-orange-600">
                                      {indicator.latest_values.mean_mid.toFixed(2)}
                                    </span>
                                  ) : (
                                    <span className="text-gray-400 text-sm">N/A</span>
                                  )}
                                </td>
                                
                                {/* Long MA */}
                                <td className="border border-gray-200 px-3 py-2 text-center">
                                  {indicator.latest_values?.mean_long ? (
                                    <span className="font-medium text-red-600">
                                      {indicator.latest_values.mean_long.toFixed(2)}
                                    </span>
                                  ) : (
                                    <span className="text-gray-400 text-sm">N/A</span>
                                  )}
                                </td>
                                
                                <td className="border border-gray-200 px-3 py-2 text-sm">
                                  <div>
                                    <div>{new Date(indicator.last_updated).toLocaleDateString()}</div>
                                    <div className="text-xs text-gray-500">
                                      {new Date(indicator.last_updated).toLocaleTimeString()}
                                    </div>
                                  </div>
                                </td>
                                <td className="border border-gray-200 px-3 py-2">
                                  <div className="flex gap-1 justify-center">
                                    <Button size="sm" variant="outline" className="h-7 w-7 p-0" title="View Details">
                                      <Eye className="h-3 w-3" />
                                    </Button>
                                    <Button size="sm" variant="outline" className="h-7 w-7 p-0" title="Export Data">
                                      <Download className="h-3 w-3" />
                                    </Button>
                                    <Button size="sm" variant="outline" className="h-7 w-7 p-0 text-red-600 hover:text-red-700" title="Delete">
                                      <Trash2 className="h-3 w-3" />
                                    </Button>
                                  </div>
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  )}
                </>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default TrueVXManagementPage;
