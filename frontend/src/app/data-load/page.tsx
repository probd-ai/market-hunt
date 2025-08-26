'use client';

import { useState, useEffect } from 'react';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import { StockGapStatus } from '@/types';
import { 
  ArrowPathIcon,
  CloudArrowDownIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  XCircleIcon,
  MagnifyingGlassIcon,
  ChartBarIcon,
  ClockIcon,
  PresentationChartLineIcon
} from '@heroicons/react/24/outline';

export default function DataLoadManagementPage() {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedIndustry, setSelectedIndustry] = useState<string>('all');
  const [selectedIndex, setSelectedIndex] = useState<string>('all');
  const [showMappedOnly, setShowMappedOnly] = useState(true);
  const [gapStatuses, setGapStatuses] = useState<StockGapStatus[]>([]);
  const [isCheckingGaps, setIsCheckingGaps] = useState(false);
  
  const queryClient = useQueryClient();

  // Fetch symbol mappings
  const { data: mappingsData, isLoading: mappingsLoading, error: mappingsError } = useQuery({
    queryKey: ['stock-mappings', selectedIndex !== 'all' ? selectedIndex : undefined, selectedIndustry !== 'all' ? selectedIndustry : undefined, showMappedOnly],
    queryFn: () => apiClient.getStockMappings(
      selectedIndex !== 'all' ? selectedIndex : undefined,
      selectedIndustry !== 'all' ? selectedIndustry : undefined,
      showMappedOnly
    ),
  });

  // Fetch stock statistics
  const { data: statsData, isLoading: statsLoading } = useQuery({
    queryKey: ['stock-statistics'],
    queryFn: () => apiClient.getStockStatistics(),
  });

  // Refresh mappings mutation
  const refreshMappingsMutation = useMutation({
    mutationFn: () => apiClient.refreshStockMappings(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['stock-mappings'] });
      alert('Symbol mappings refreshed successfully!');
    },
    onError: (error: Error) => {
      alert(`Failed to refresh mappings: ${error.message}`);
    },
  });

  // Download stock data mutation
  const downloadStockMutation = useMutation({
    mutationFn: (symbol: string) => apiClient.downloadStockData({ symbol }),
    onSuccess: (data, symbol) => {
      alert(`Stock data download initiated for ${symbol}`);
      // Refresh gap statuses after download
      handleCheckGaps();
    },
    onError: (error: Error, symbol) => {
      alert(`Failed to download data for ${symbol}: ${error.message}`);
    },
  });

  // Handle gap checking
  const handleCheckGaps = async () => {
    if (!mappingsData?.mappings) return;
    
    setIsCheckingGaps(true);
    try {
      const symbols = filteredMappings.map(m => m.symbol);
      const gaps = await apiClient.checkStockGaps(symbols);
      setGapStatuses(gaps);
    } catch (error) {
      console.error('Failed to check gaps:', error);
      alert('Failed to check data gaps');
    } finally {
      setIsCheckingGaps(false);
    }
  };

  // Filter mappings based on search and selections
  const filteredMappings = mappingsData?.mappings?.filter(mapping => {
    const matchesSearch = searchTerm === '' || 
      mapping.symbol.toLowerCase().includes(searchTerm.toLowerCase()) ||
      mapping.company_name.toLowerCase().includes(searchTerm.toLowerCase());
    
    return matchesSearch;
  }) || [];

  // Get unique industries and indices for filters
  const uniqueIndustries = Array.from(new Set(mappingsData?.mappings?.map(m => m.industry) || [])).sort();
  const uniqueIndices = Array.from(new Set(mappingsData?.mappings?.flatMap(m => m.index_names) || [])).sort();

  // Auto-check gaps when mappings load
  useEffect(() => {
    if (mappingsData?.mappings && filteredMappings.length > 0 && gapStatuses.length === 0) {
      handleCheckGaps();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mappingsData?.mappings, filteredMappings.length]);

  const getGapStatusForSymbol = (symbol: string): StockGapStatus | undefined => {
    return gapStatuses.find(gap => gap.symbol === symbol);
  };

  const getStatusIcon = (gapStatus?: StockGapStatus) => {
    if (!gapStatus) return <ClockIcon className="h-5 w-5 text-gray-400" />;
    
    if (!gapStatus.has_data) {
      return <XCircleIcon className="h-5 w-5 text-red-500" />;
    } else if (gapStatus.needs_update) {
      return <ExclamationTriangleIcon className="h-5 w-5 text-yellow-500" />;
    } else {
      return <CheckCircleIcon className="h-5 w-5 text-green-500" />;
    }
  };

  const getStatusText = (gapStatus?: StockGapStatus) => {
    if (!gapStatus) return 'Checking...';
    
    if (!gapStatus.has_data) {
      return 'No Data';
    } else if (gapStatus.needs_update) {
      return `Outdated (${gapStatus.data_freshness_days} days)`;
    } else {
      return 'Up to Date';
    }
  };

  const getStatusColor = (gapStatus?: StockGapStatus) => {
    if (!gapStatus) return 'bg-gray-50';
    
    if (!gapStatus.has_data) {
      return 'bg-red-50';
    } else if (gapStatus.needs_update) {
      return 'bg-yellow-50';
    } else {
      return 'bg-green-50';
    }
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Data Load Management</h1>
          <p className="mt-2 text-gray-600">
            Manage historical stock data downloads and monitor data freshness
          </p>
        </div>

        {/* Statistics Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center">
                <ChartBarIcon className="h-8 w-8 text-blue-500" />
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">Total Symbols</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {mappingsData?.total_mappings || 0}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center">
                <CheckCircleIcon className="h-8 w-8 text-green-500" />
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">Mapped Symbols</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {mappingsData?.mapped_count || 0}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center">
                <CloudArrowDownIcon className="h-8 w-8 text-purple-500" />
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">With Data</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {gapStatuses.filter(g => g.has_data).length}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center">
                <ExclamationTriangleIcon className="h-8 w-8 text-yellow-500" />
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">Needs Update</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {gapStatuses.filter(g => g.needs_update).length}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Controls */}
        <Card>
          <CardHeader>
            <CardTitle>Data Management Controls</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-4">
              <Button
                onClick={() => refreshMappingsMutation.mutate()}
                disabled={refreshMappingsMutation.isPending}
                className="flex items-center gap-2"
              >
                <ArrowPathIcon className={`h-4 w-4 ${refreshMappingsMutation.isPending ? 'animate-spin' : ''}`} />
                Refresh Mappings
              </Button>

              <Button
                onClick={handleCheckGaps}
                disabled={isCheckingGaps}
                variant="outline"
                className="flex items-center gap-2"
              >
                <MagnifyingGlassIcon className={`h-4 w-4 ${isCheckingGaps ? 'animate-spin' : ''}`} />
                Check All Gaps
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Filters */}
        <Card>
          <CardHeader>
            <CardTitle>Filters</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Search
                </label>
                <Input
                  type="text"
                  placeholder="Search symbols or companies..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Industry
                </label>
                <select
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  value={selectedIndustry}
                  onChange={(e) => setSelectedIndustry(e.target.value)}
                >
                  <option value="all">All Industries</option>
                  {uniqueIndustries.map(industry => (
                    <option key={industry} value={industry}>{industry}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Index
                </label>
                <select
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  value={selectedIndex}
                  onChange={(e) => setSelectedIndex(e.target.value)}
                >
                  <option value="all">All Indices</option>
                  {uniqueIndices.map(index => (
                    <option key={index} value={index}>{index}</option>
                  ))}
                </select>
              </div>

              <div className="flex items-end">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={showMappedOnly}
                    onChange={(e) => setShowMappedOnly(e.target.checked)}
                    className="mr-2"
                  />
                  Mapped Only
                </label>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Stock Data Table */}
        <Card>
          <CardHeader>
            <CardTitle>Stock Data Status ({filteredMappings.length} symbols)</CardTitle>
          </CardHeader>
          <CardContent>
            {mappingsLoading ? (
              <div className="text-center py-8">Loading stock mappings...</div>
            ) : mappingsError ? (
              <div className="text-center py-8 text-red-600">
                Error loading mappings: {mappingsError.message}
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Symbol
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Company
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Industry
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        NSE Code
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Data Status
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Records
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Coverage
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {filteredMappings.map((mapping) => {
                      const gapStatus = getGapStatusForSymbol(mapping.symbol);
                      return (
                        <tr key={mapping.symbol} className={getStatusColor(gapStatus)}>
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                            {mapping.symbol}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            <div className="max-w-xs truncate" title={mapping.company_name}>
                              {mapping.company_name}
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {mapping.industry}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {mapping.nse_scrip_code || 'Not mapped'}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            <div className="flex items-center gap-2">
                              {getStatusIcon(gapStatus)}
                              <span>{getStatusText(gapStatus)}</span>
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {gapStatus?.record_count?.toLocaleString() || '0'}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {gapStatus?.coverage_percentage ? `${gapStatus.coverage_percentage}%` : '0%'}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {mapping.nse_scrip_code && (
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => {
                                  const chartUrl = `/chart?symbol=${mapping.symbol}`;
                                  window.open(chartUrl, '_blank');
                                }}
                                className="flex items-center gap-1"
                              >
                                <PresentationChartLineIcon className="h-4 w-4" />
                                Open Chart
                              </Button>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}
