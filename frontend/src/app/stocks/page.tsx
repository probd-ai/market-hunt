'use client';

import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { SymbolMapping, SymbolMappingResponse, StockDataStatistics, DownloadStockDataRequest, ProgressUpdate, HistoricalProcessing, DataGapInfo } from '@/types';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { StockChart } from '@/components/stocks/StockChart';
import { SymbolSearch } from '@/components/stocks/SymbolSearch';
import { 
  CurrencyDollarIcon, 
  CloudArrowDownIcon, 
  ClockIcon, 
  ChartBarIcon,
  TrashIcon,
  ArrowPathIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  PlayIcon
} from '@heroicons/react/24/outline';

type LoadMode = 'symbol' | 'index' | 'industry';
type SyncMode = 'load' | 'sync' | 'refresh' | 'delete';

export default function StocksPage() {
  const [selectedSymbol, setSelectedSymbol] = useState<string>('');
  const [downloadSymbol, setDownloadSymbol] = useState<string>('');
  const [startDate, setStartDate] = useState<string>('2020-01-01');
  const [endDate, setEndDate] = useState<string>(new Date().toISOString().split('T')[0]);
  const [selectedIndex, setSelectedIndex] = useState<string>('');
  const [selectedIndustry, setSelectedIndustry] = useState<string>('');
  const [mappedOnly, setMappedOnly] = useState<boolean>(true);
  const [loadMode, setLoadMode] = useState<LoadMode>('symbol');
  const [syncMode, setSyncMode] = useState<SyncMode>('load');
  const [activeTaskId, setActiveTaskId] = useState<string>('');
  const [showProgress, setShowProgress] = useState<boolean>(false);
  const [showHistory, setShowHistory] = useState<boolean>(false);
  const [dataGaps, setDataGaps] = useState<DataGapInfo[]>([]);
  const [showGaps, setShowGaps] = useState<boolean>(false);
  
  const queryClient = useQueryClient();

  // Fetch symbol mappings
  const { data: symbolMappingsResponse, isLoading: mappingsLoading, error: mappingsError } = useQuery({
    queryKey: ['symbolMappings', { index_name: selectedIndex, mapped_only: mappedOnly }],
    queryFn: () => api.getSymbolMappings({ 
      index_name: selectedIndex || undefined, 
      mapped_only: mappedOnly 
    }),
  });

  const symbolMappings = symbolMappingsResponse?.mappings || [];

  // Fetch stock statistics
  const { data: statistics, isLoading: statsLoading } = useQuery({
    queryKey: ['stockStatistics'],
    queryFn: () => api.getStockDataStatistics(),
  });

  // Fetch stock price data
  const { data: priceDataResponse, isLoading: priceLoading } = useQuery({
    queryKey: ['stockData', selectedSymbol, startDate, endDate],
    queryFn: () => api.getStockData(selectedSymbol, startDate, endDate),
    enabled: !!selectedSymbol,
  });

  const priceData = priceDataResponse?.data || [];

  // Fetch historical processing
  const { data: processingHistory = [] } = useQuery({
    queryKey: ['processingHistory'],
    queryFn: () => api.getHistoricalProcessing(10),
    enabled: showHistory,
  });

  // Fetch progress updates for active task
  const { data: progressData } = useQuery({
    queryKey: ['taskProgress', activeTaskId],
    queryFn: () => api.getTaskProgress(activeTaskId),
    enabled: !!activeTaskId && showProgress,
    refetchInterval: 2000, // Poll every 2 seconds
  });

  // Refresh symbol mappings mutation
  const refreshMappingsMutation = useMutation({
    mutationFn: () => api.refreshSymbolMappings(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['symbolMappings'] });
    },
  });

  // Check data gaps mutation
  const checkGapsMutation = useMutation({
    mutationFn: (request: { symbol?: string; symbols?: string[]; index_name?: string; industry?: string; start_date: string; end_date: string }) => 
      api.checkDataGaps(request),
    onSuccess: (gaps) => {
      setDataGaps(gaps);
      setShowGaps(gaps.length > 0);
    },
    onError: (error) => {
      console.error('Gap analysis error:', error);
      setDataGaps([]);
      setShowGaps(false);
    },
  });

  // Load stock data mutation
  const loadDataMutation = useMutation({
    mutationFn: (request: DownloadStockDataRequest) => api.downloadStockData(request),
    onSuccess: (response) => {
      setActiveTaskId(response.task_id);
      setShowProgress(true);
      queryClient.invalidateQueries({ queryKey: ['stockStatistics'] });
      queryClient.invalidateQueries({ queryKey: ['processingHistory'] });
    },
  });

  // Delete stock data mutation
  const deleteDataMutation = useMutation({
    mutationFn: (request: { symbol?: string; symbols?: string[]; index_name?: string; industry?: string }) => 
      api.deleteStockData(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['stockStatistics'] });
      queryClient.invalidateQueries({ queryKey: ['stockData'] });
    },
  });

  // Get unique indices and industries from mappings
  const uniqueIndices = Array.from(
    new Set((symbolMappings || []).flatMap(mapping => mapping.index_names || []))
  ).sort();

  const uniqueIndustries = Array.from(
    new Set((symbolMappings || []).map(mapping => mapping.industry))
  ).filter(Boolean).sort();

  const handleCheckGaps = async () => {
    const request: any = {
      start_date: startDate,
      end_date: endDate,
    };

    if (loadMode === 'symbol' && downloadSymbol) {
      request.symbol = downloadSymbol;
    } else if (loadMode === 'index' && selectedIndex) {
      request.index_name = selectedIndex;
    } else if (loadMode === 'industry' && selectedIndustry) {
      request.industry = selectedIndustry;
    }

    checkGapsMutation.mutate(request);
  };

  const handleLoadData = async () => {
    const request: DownloadStockDataRequest = {
      start_date: startDate,
      end_date: endDate,
      sync_mode: syncMode,
    };

    if (loadMode === 'symbol' && downloadSymbol) {
      request.symbol = downloadSymbol;
    } else if (loadMode === 'index' && selectedIndex) {
      request.index_name = selectedIndex;
    } else if (loadMode === 'industry' && selectedIndustry) {
      request.industry = selectedIndustry;
    }

    // Auto-check gaps if in sync mode
    if (syncMode === 'sync' || syncMode === 'load') {
      await handleCheckGaps();
    }

    loadDataMutation.mutate(request);
  };

  const handleDeleteData = async () => {
    if (!confirm('Are you sure you want to delete this data? This action cannot be undone.')) {
      return;
    }

    const request: any = {};

    if (loadMode === 'symbol' && downloadSymbol) {
      request.symbol = downloadSymbol;
    } else if (loadMode === 'index' && selectedIndex) {
      request.index_name = selectedIndex;
    } else if (loadMode === 'industry' && selectedIndustry) {
      request.industry = selectedIndustry;
    }

    deleteDataMutation.mutate(request);
  };

  const handleRefreshMappings = () => {
    refreshMappingsMutation.mutate();
  };

  const isFormValid = () => {
    if (loadMode === 'symbol') return !!downloadSymbol;
    if (loadMode === 'index') return !!selectedIndex;
    if (loadMode === 'industry') return !!selectedIndustry;
    return false;
  };

  const getCurrentSelection = () => {
    if (loadMode === 'symbol') return downloadSymbol;
    if (loadMode === 'index') return selectedIndex;
    if (loadMode === 'industry') return selectedIndustry;
    return '';
  };

  // Close progress panel when task completes
  useEffect(() => {
    if (progressData && (progressData.status === 'completed' || progressData.status === 'failed')) {
      const timer = setTimeout(() => {
        setShowProgress(false);
        setActiveTaskId('');
        queryClient.invalidateQueries({ queryKey: ['stockStatistics'] });
        queryClient.invalidateQueries({ queryKey: ['stockData'] });
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [progressData, queryClient]);

  // Error handling for symbol mappings
  if (mappingsError) {
    return (
      <div className="space-y-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center">
            <ExclamationTriangleIcon className="h-5 w-5 text-red-400 mr-2" />
            <h3 className="text-red-800 font-medium">Error Loading Symbol Mappings</h3>
          </div>
          <p className="text-red-700 mt-2">
            {mappingsError instanceof Error ? mappingsError.message : 'Failed to load symbol mappings'}
          </p>
          <Button 
            onClick={handleRefreshMappings}
            className="mt-3 bg-red-600 hover:bg-red-700"
            disabled={refreshMappingsMutation.isPending}
          >
            {refreshMappingsMutation.isPending ? 'Refreshing...' : 'Retry'}
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Stock Data Management</h1>
          <p className="text-gray-600 mt-2">
            Load stock data by symbol, index, or industry with intelligent synchronization
          </p>
        </div>
        <div className="flex gap-3">
          <Button
            onClick={() => setShowHistory(!showHistory)}
            variant="outline"
            className="bg-purple-50 hover:bg-purple-100 border-purple-200"
          >
            <ClockIcon className="h-4 w-4 mr-2" />
            {showHistory ? 'Hide' : 'Show'} History
          </Button>
          <Button
            onClick={handleRefreshMappings}
            disabled={refreshMappingsMutation.isPending}
            className="bg-blue-600 hover:bg-blue-700"
          >
            <ArrowPathIcon className="h-4 w-4 mr-2" />
            {refreshMappingsMutation.isPending ? 'Refreshing...' : 'Refresh Mappings'}
          </Button>
        </div>
      </div>

      {/* Statistics Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card className="p-6">
          <div className="text-2xl font-bold text-blue-600">
            {statistics?.total_records.toLocaleString() || '0'}
          </div>
          <div className="text-sm text-gray-600">Total Price Records</div>
        </Card>
        <Card className="p-6">
          <div className="text-2xl font-bold text-green-600">
            {statistics?.unique_symbols_count || '0'}
          </div>
          <div className="text-sm text-gray-600">Symbols with Data</div>
        </Card>
        <Card className="p-6">
          <div className="text-2xl font-bold text-purple-600">
            {symbolMappingsResponse?.total_mappings || '0'}
          </div>
          <div className="text-sm text-gray-600">Total Symbols</div>
        </Card>
        <Card className="p-6">
          <div className="text-2xl font-bold text-green-600">
            {symbolMappingsResponse?.mapped_count || '0'}
          </div>
          <div className="text-sm text-gray-600">Mapped Symbols</div>
        </Card>
        <Card className="p-6">
          <div className="text-2xl font-bold text-orange-600">
            {statistics ? new Date(statistics.date_range.latest).getFullYear() - new Date(statistics.date_range.earliest).getFullYear() + 1 : '0'}
          </div>
          <div className="text-sm text-gray-600">Years of Data</div>
        </Card>
      </div>

      {/* Progress Panel */}
      {showProgress && progressData && (
        <Card className="p-6 border-l-4 border-l-blue-500">
          <div className="flex justify-between items-start mb-4">
            <div>
              <h3 className="text-lg font-semibold">Loading Progress</h3>
              <p className="text-sm text-gray-600">{progressData.current_item || 'Processing...'}</p>
            </div>
            <Button
              onClick={() => setShowProgress(false)}
              size="sm"
              variant="outline"
            >
              ×
            </Button>
          </div>
          
          <div className="space-y-3">
            <div className="flex justify-between text-sm">
              <span>Progress: {progressData.current_count} / {progressData.total_count}</span>
              <span className={`font-medium ${
                progressData.status === 'completed' ? 'text-green-600' :
                progressData.status === 'failed' ? 'text-red-600' :
                'text-blue-600'
              }`}>
                {progressData.status === 'running' ? `${progressData.progress_percentage}%` : progressData.status}
              </span>
            </div>
            
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div 
                className={`h-2 rounded-full transition-all duration-300 ${
                  progressData.status === 'completed' ? 'bg-green-500' :
                  progressData.status === 'failed' ? 'bg-red-500' :
                  'bg-blue-500'
                }`}
                style={{ width: `${progressData.progress_percentage}%` }}
              />
            </div>

            {progressData.message && (
              <p className="text-sm text-gray-600">{progressData.message}</p>
            )}

            {progressData.error && (
              <p className="text-sm text-red-600">Error: {progressData.error}</p>
            )}
          </div>
        </Card>
      )}

      {/* Historical Processing */}
      {showHistory && (
        <Card className="p-6">
          <h2 className="text-xl font-semibold mb-4">Processing History</h2>
          <div className="space-y-2">
            {processingHistory.length === 0 ? (
              <p className="text-gray-500 text-center py-4">No processing history found</p>
            ) : (
              processingHistory.map((process, index) => (
                <div key={process._id || `process-${index}`} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center space-x-3">
                    {process.status === 'completed' ? (
                      <CheckCircleIcon className="h-5 w-5 text-green-600" />
                    ) : process.status === 'failed' ? (
                      <ExclamationTriangleIcon className="h-5 w-5 text-red-600" />
                    ) : (
                      <PlayIcon className="h-5 w-5 text-blue-600" />
                    )}
                    <div>
                      <div className="font-medium">
                        {process.request_type} - {
                          process.request_params.symbol || 
                          process.request_params.index_name || 
                          process.request_params.industry
                        }
                      </div>
                      <div className="text-sm text-gray-600">
                        {new Date(process.started_at).toLocaleString()}
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-medium">
                      {process.items_processed} / {process.total_items}
                    </div>
                    <div className={`text-xs ${
                      process.status === 'completed' ? 'text-green-600' :
                      process.status === 'failed' ? 'text-red-600' :
                      'text-blue-600'
                    }`}>
                      {process.status}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </Card>
      )}

      {/* Data Loading Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="p-6">
          <h2 className="text-xl font-semibold mb-4">Load Historical Data</h2>
          <div className="space-y-4">
            {/* Load Mode Selection */}
            <div>
              <label className="block text-sm font-medium mb-2">Load by</label>
              <div className="grid grid-cols-3 gap-2">
                <Button
                  onClick={() => setLoadMode('symbol')}
                  variant={loadMode === 'symbol' ? 'primary' : 'outline'}
                  size="sm"
                  className="w-full"
                >
                  Stock Symbol
                </Button>
                <Button
                  onClick={() => setLoadMode('index')}
                  variant={loadMode === 'index' ? 'primary' : 'outline'}
                  size="sm"
                  className="w-full"
                >
                  Index Name
                </Button>
                <Button
                  onClick={() => setLoadMode('industry')}
                  variant={loadMode === 'industry' ? 'primary' : 'outline'}
                  size="sm"
                  className="w-full"
                >
                  Industry
                </Button>
              </div>
            </div>

            {/* Selection Input */}
            {loadMode === 'symbol' && (
              <div>
                <label className="block text-sm font-medium mb-2">Search & Select Symbol</label>
                <SymbolSearch
                  symbols={symbolMappings}
                  onSelect={setDownloadSymbol}
                  selectedSymbol={downloadSymbol}
                />
              </div>
            )}

            {loadMode === 'index' && (
              <div>
                <label className="block text-sm font-medium mb-2">Select Index</label>
                <select
                  value={selectedIndex}
                  onChange={(e) => setSelectedIndex(e.target.value)}
                  className="w-full border rounded px-3 py-2"
                >
                  <option value="">Choose an index...</option>
                  {uniqueIndices.map(index => (
                    <option key={index} value={index}>{index}</option>
                  ))}
                </select>
              </div>
            )}

            {loadMode === 'industry' && (
              <div>
                <label className="block text-sm font-medium mb-2">Select Industry</label>
                <select
                  value={selectedIndustry}
                  onChange={(e) => setSelectedIndustry(e.target.value)}
                  className="w-full border rounded px-3 py-2"
                >
                  <option value="">Choose an industry...</option>
                  {uniqueIndustries.map(industry => (
                    <option key={industry} value={industry}>{industry}</option>
                  ))}
                </select>
              </div>
            )}

            {/* Date Range */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">Start Date</label>
                <Input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="w-full"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">End Date</label>
                <Input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="w-full"
                />
              </div>
            </div>

            {/* Sync Mode Selection */}
            <div>
              <label className="block text-sm font-medium mb-2">Action</label>
              <div className="grid grid-cols-2 gap-2">
                <Button
                  onClick={() => setSyncMode('load')}
                  variant={syncMode === 'load' ? 'primary' : 'outline'}
                  size="sm"
                  className="w-full bg-green-50 hover:bg-green-100 border-green-200"
                >
                  <CloudArrowDownIcon className="h-4 w-4 mr-2" />
                  Load
                </Button>
                <Button
                  onClick={() => setSyncMode('sync')}
                  variant={syncMode === 'sync' ? 'primary' : 'outline'}
                  size="sm"
                  className="w-full bg-blue-50 hover:bg-blue-100 border-blue-200"
                >
                  <ArrowPathIcon className="h-4 w-4 mr-2" />
                  Sync
                </Button>
                <Button
                  onClick={() => setSyncMode('refresh')}
                  variant={syncMode === 'refresh' ? 'primary' : 'outline'}
                  size="sm"
                  className="w-full bg-yellow-50 hover:bg-yellow-100 border-yellow-200"
                >
                  <ArrowPathIcon className="h-4 w-4 mr-2" />
                  Refresh
                </Button>
                <Button
                  onClick={() => setSyncMode('delete')}
                  variant={syncMode === 'delete' ? 'primary' : 'outline'}
                  size="sm"
                  className="w-full bg-red-50 hover:bg-red-100 border-red-200"
                >
                  <TrashIcon className="h-4 w-4 mr-2" />
                  Delete
                </Button>
              </div>
              <div className="text-xs text-gray-500 mt-1">
                {syncMode === 'load' && 'Download new data (skip existing)'}
                {syncMode === 'sync' && 'Fill missing dates automatically'}
                {syncMode === 'refresh' && 'Delete and reload all data'}
                {syncMode === 'delete' && 'Remove existing data only'}
              </div>
            </div>

            {/* Action Buttons */}
            <div className="space-y-2">
              <Button
                onClick={handleCheckGaps}
                disabled={!isFormValid() || checkGapsMutation.isPending}
                variant="outline"
                className="w-full"
                title="Analyzes complete data from 2005-01-01 to present and shows all missing trading days"
              >
                {checkGapsMutation.isPending ? 'Analyzing Complete History...' : '🔍 Complete Historical Gap Analysis'}
              </Button>
              <div className="text-xs text-gray-500 text-center">
                Shows ALL missing data from 2005 to present, grouped by year for easy viewing
              </div>
              
              <Button
                onClick={syncMode === 'delete' ? handleDeleteData : handleLoadData}
                disabled={!isFormValid() || loadDataMutation.isPending || deleteDataMutation.isPending}
                className={`w-full ${
                  syncMode === 'load' ? 'bg-green-600 hover:bg-green-700' :
                  syncMode === 'sync' ? 'bg-blue-600 hover:bg-blue-700' :
                  syncMode === 'refresh' ? 'bg-yellow-600 hover:bg-yellow-700' :
                  'bg-red-600 hover:bg-red-700'
                }`}
              >
                {loadDataMutation.isPending || deleteDataMutation.isPending ? 'Processing...' : 
                 syncMode === 'load' ? 'Load Data' :
                 syncMode === 'sync' ? 'Sync Data' :
                 syncMode === 'refresh' ? 'Refresh Data' :
                 'Delete Data'}
              </Button>
            </div>

            {/* Status Messages */}
            {loadDataMutation.isSuccess && (
              <div className="text-green-600 text-sm">
                ✓ Load started successfully! Track progress above.
              </div>
            )}
            {loadDataMutation.isError && (
              <div className="text-red-600 text-sm">
                ✗ Load failed: {loadDataMutation.error?.message}
              </div>
            )}
            {deleteDataMutation.isSuccess && (
              <div className="text-green-600 text-sm">
                ✓ Data deleted successfully!
              </div>
            )}
            {deleteDataMutation.isError && (
              <div className="text-red-600 text-sm">
                ✗ Delete failed: {deleteDataMutation.error?.message}
              </div>
            )}
          </div>
        </Card>

        <Card className="p-6">
          <h2 className="text-xl font-semibold mb-4">Selection Summary</h2>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="text-center p-4 bg-blue-50 rounded-lg">
                <div className="text-2xl font-bold text-blue-600">
                  {loadMode === 'symbol' ? '1' :
                   loadMode === 'index' ? (symbolMappings || []).filter(m => m.index_names && m.index_names.includes(selectedIndex)).length :
                   loadMode === 'industry' ? (symbolMappings || []).filter(m => m.industry === selectedIndustry).length :
                   '0'}
                </div>
                <div className="text-sm text-gray-600">Symbols Selected</div>
              </div>
              <div className="text-center p-4 bg-green-50 rounded-lg">
                <div className="text-2xl font-bold text-green-600">
                  {startDate && endDate ? 
                    Math.ceil((new Date(endDate).getTime() - new Date(startDate).getTime()) / (1000 * 60 * 60 * 24)) + 1 :
                    '0'}
                </div>
                <div className="text-sm text-gray-600">Days Range</div>
              </div>
            </div>

            {getCurrentSelection() && (
              <div className="p-4 bg-gray-50 rounded-lg">
                <h4 className="font-medium mb-2">Current Selection</h4>
                <div className="text-sm space-y-1">
                  <div><strong>Type:</strong> {loadMode}</div>
                  <div><strong>Selection:</strong> {getCurrentSelection()}</div>
                  <div><strong>Date Range:</strong> {startDate} to {endDate}</div>
                  <div><strong>Action:</strong> {syncMode}</div>
                </div>
              </div>
            )}

            {/* Enhanced Data Gaps Display with Yearly Breakdown */}
            {showGaps && dataGaps.length > 0 && (
              <div className="space-y-4">
                {dataGaps.slice(0, 3).map((gap, index) => (
                  <div key={index} className="p-4 bg-yellow-50 rounded-lg border border-yellow-200">
                    <div className="flex justify-between items-start mb-3">
                      <h4 className="font-medium text-yellow-800">⚠️ Data Gaps for {gap.symbol}</h4>
                      <div className="text-xs text-yellow-600">
                        Total: {gap.total_data_points || 0} records available
                      </div>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-4 text-sm mb-4">
                      <div>
                        <div className="text-yellow-700 mb-2">
                          <strong>Complete Period Analysis (2005-Present):</strong>
                        </div>
                        <div className="space-y-1 text-xs">
                          <div>• Missing trading days: <span className="font-medium text-red-600">{gap.downloadable_gaps?.toLocaleString() || 0}</span></div>
                          <div>• Data available: {gap.data_available_from || 'None'} to {gap.data_available_until || 'None'}</div>
                          <div>• Available records: <span className="font-medium text-green-600">{gap.total_data_points?.toLocaleString() || 0}</span></div>
                          <div className="text-blue-600">• ✓ Comprehensive gap analysis from 2005</div>
                        </div>
                      </div>
                      
                      <div>
                        <div className="text-yellow-700 mb-2">
                          <strong>Your Selected Range:</strong>
                        </div>
                        <div className="space-y-1 text-xs">
                          <div>• Range: {gap.user_range_start} to {gap.user_range_end}</div>
                          <div>• Missing in your range: <span className="font-medium text-orange-600">{gap.user_range_gaps || 0} days</span></div>
                          {gap.user_range_gaps && gap.user_range_gaps > 0 && (
                            <div className="text-orange-600">• ⚠️ Your range has missing data!</div>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Yearly Gap Breakdown */}
                    {gap.gaps_by_year && Object.keys(gap.gaps_by_year).length > 0 && (
                      <div className="p-3 bg-red-50 rounded text-xs mb-3 border border-red-200">
                        <div className="text-red-700 mb-2 font-medium">📊 Missing Trading Days by Year (2005-Present):</div>
                        <div className="text-xs text-red-600 mb-2">
                          ⚠️ Large gaps detected! This symbol needs significant data download.
                        </div>
                        <div className="grid grid-cols-4 gap-2 max-h-32 overflow-y-auto">
                          {Object.entries(gap.gaps_by_year)
                            .sort(([a], [b]) => parseInt(b) - parseInt(a)) // Sort by year descending
                            .slice(0, 16) // Show more years since we expect many
                            .map(([year, count]) => (
                              <div key={year} className="bg-white px-2 py-1 rounded border border-red-200">
                                <div className="font-medium text-red-800">{year}</div>
                                <div className="text-red-600">{count} days</div>
                              </div>
                            ))}
                        </div>
                        {Object.keys(gap.gaps_by_year).length > 16 && (
                          <div className="text-red-600 mt-2">
                            ...and {Object.keys(gap.gaps_by_year).length - 16} more years with gaps
                          </div>
                        )}
                        <div className="text-blue-600 mt-2 text-xs bg-blue-50 p-2 rounded">
                          💡 Tip: Use "Sync All Missing Data" to download complete historical data
                        </div>
                      </div>
                    )}

                    {/* Sync Options - Enhanced */}
                    <div className="flex flex-wrap gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => {
                          // Set start date to 2005 for complete historical data sync
                          setStartDate('2005-01-01');
                          setEndDate(new Date().toISOString().split('T')[0]);
                          setSyncMode('sync');
                        }}
                        className="text-xs bg-red-50 hover:bg-red-100 border-red-200"
                        disabled={!gap.downloadable_gaps || gap.downloadable_gaps === 0}
                      >
                        🔄 Sync All Missing Data
                        {gap.downloadable_gaps && (
                          <span className="ml-1 px-1 bg-red-200 rounded">
                            {gap.downloadable_gaps.toLocaleString()} days
                          </span>
                        )}
                      </Button>
                      
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => {
                          // Only sync missing data in user's range
                          setSyncMode('sync');
                        }}
                        className="text-xs bg-green-50 hover:bg-green-100 border-green-200"
                        disabled={!gap.user_range_gaps || gap.user_range_gaps === 0}
                      >
                        📅 Sync Range Only
                        {gap.user_range_gaps && (
                          <span className="ml-1 px-1 bg-green-200 rounded">
                            {gap.user_range_gaps} days
                          </span>
                        )}
                      </Button>
                      
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => {
                          // Skip this symbol - remove from gaps
                          setDataGaps(prev => prev.filter((_, i) => i !== index));
                        }}
                        className="text-xs text-gray-500"
                      >
                        ⏭️ Skip Symbol
                      </Button>
                    </div>
                  </div>
                ))}
                
                {dataGaps.length > 3 && (
                  <div className="p-3 bg-gray-50 rounded-lg border border-gray-200 text-center">
                    <div className="text-sm text-gray-600 mb-2">
                      ...and {dataGaps.length - 3} more symbols with data gaps
                    </div>
                    <div className="text-xs text-gray-500 mb-3">
                      Total downloadable gaps: {dataGaps.slice(3).reduce((sum, gap) => sum + (gap.downloadable_gaps || 0), 0)} days
                    </div>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        // Batch sync all missing data for all symbols based on their discovered periods
                        setStartDate('2005-01-01'); // Start from 2005 to trigger discovery
                        setEndDate(new Date().toISOString().split('T')[0]);
                        setSyncMode('sync');
                        handleLoadData();
                      }}
                      className="text-xs bg-blue-50 hover:bg-blue-100 border-blue-200"
                    >
                      🔄 Discover & Sync All Symbols
                    </Button>
                  </div>
                )}
              </div>
            )}

            {showGaps && dataGaps.length === 0 && checkGapsMutation.isSuccess && (
              <div className="p-4 bg-green-50 rounded-lg border border-green-200">
                <h4 className="font-medium mb-2 text-green-800">✅ Intelligent Discovery Complete</h4>
                <div className="text-sm text-green-700 space-y-1">
                  <p>No data gaps found for the selected symbol(s) in their discoverable period!</p>
                  <p className="text-xs text-green-600">
                    ℹ️ We attempted download from 2005-01-01 to discover the actual downloadable range, 
                    then verified no gaps exist in that period.
                  </p>
                  <p className="text-xs text-green-600">
                    Your selected range: {startDate} to {endDate} ✓
                  </p>
                </div>
              </div>
            )}
          </div>
        </Card>
      </div>

      {/* Symbol Mappings Section */}
      <Card className="p-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold">Symbol Mappings</h2>
          <div className="flex gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Filter by Index</label>
              <select
                value={selectedIndex}
                onChange={(e) => setSelectedIndex(e.target.value)}
                className="border rounded px-3 py-2 text-sm"
              >
                <option value="">All Indices</option>
                {uniqueIndices.map(index => (
                  <option key={index} value={index}>{index}</option>
                ))}
              </select>
            </div>
            <div className="flex items-end">
              <label className="flex items-center text-sm">
                <input
                  type="checkbox"
                  checked={mappedOnly}
                  onChange={(e) => setMappedOnly(e.target.checked)}
                  className="mr-2"
                />
                Mapped only
              </label>
            </div>
          </div>
        </div>

        {mappingsLoading ? (
          <div className="flex justify-center py-8">
            <div className="text-gray-500">Loading symbol mappings...</div>
          </div>
        ) : mappingsError ? (
          <div className="text-red-600 py-4">
            Error loading mappings: {String(mappingsError)}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full border-collapse border border-gray-300">
              <thead>
                <tr className="bg-gray-50">
                  <th className="border border-gray-300 px-4 py-2 text-left">Symbol</th>
                  <th className="border border-gray-300 px-4 py-2 text-left">Company</th>
                  <th className="border border-gray-300 px-4 py-2 text-left">Industry</th>
                  <th className="border border-gray-300 px-4 py-2 text-left">Indices</th>
                  <th className="border border-gray-300 px-4 py-2 text-left">NSE Code</th>
                  <th className="border border-gray-300 px-4 py-2 text-left">Confidence</th>
                  <th className="border border-gray-300 px-4 py-2 text-left">Actions</th>
                </tr>
              </thead>
              <tbody>
                {(symbolMappings || []).map((mapping, index) => (
                  <tr key={`${mapping.symbol}-${index}`} className="hover:bg-gray-50">
                    <td className="border border-gray-300 px-4 py-2 font-medium">
                      {mapping.symbol}
                    </td>
                    <td className="border border-gray-300 px-4 py-2">
                      {mapping.company_name}
                    </td>
                    <td className="border border-gray-300 px-4 py-2">
                      {mapping.industry}
                    </td>
                    <td className="border border-gray-300 px-4 py-2">
                      <div className="flex flex-wrap gap-1">
                        {mapping.index_names.map(index => (
                          <span
                            key={index}
                            className="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded"
                          >
                            {index}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="border border-gray-300 px-4 py-2">
                      {mapping.nse_scrip_code}
                    </td>
                    <td className="border border-gray-300 px-4 py-2">
                      <span className={`text-sm ${mapping.match_confidence && mapping.match_confidence >= 1 ? 'text-green-600' : 'text-orange-600'}`}>
                        {mapping.match_confidence ? (mapping.match_confidence * 100).toFixed(0) + '%' : 'N/A'}
                      </span>
                    </td>
                    <td className="border border-gray-300 px-4 py-2">
                      <Button
                        onClick={() => setSelectedSymbol(mapping.symbol)}
                        size="sm"
                        variant="outline"
                      >
                        View Data
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Stock Price Data Section */}
      {selectedSymbol && (
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          <div className="xl:col-span-2">
            <Card className="p-6">
              <StockChart data={priceData} symbol={selectedSymbol} />
            </Card>
          </div>
          
          <Card className="p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold">
                {selectedSymbol} Details
              </h2>
              <Button
                onClick={() => setSelectedSymbol('')}
                size="sm"
                variant="outline"
              >
                Clear
              </Button>
            </div>
            
            {priceData.length > 0 && (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="text-center p-3 bg-blue-50 rounded">
                    <div className="text-lg font-bold text-blue-600">
                      ₹{priceData[priceData.length - 1]?.close_price.toFixed(2)}
                    </div>
                    <div className="text-xs text-gray-600">Latest Close</div>
                  </div>
                  <div className="text-center p-3 bg-green-50 rounded">
                    <div className="text-lg font-bold text-green-600">
                      {priceData.length}
                    </div>
                    <div className="text-xs text-gray-600">Records</div>
                  </div>
                </div>
                
                <div className="p-3 bg-gray-50 rounded">
                  <h4 className="font-medium mb-2">Price Range</h4>
                  <div className="space-y-1 text-sm">
                    <div className="flex justify-between">
                      <span>High:</span>
                      <span className="font-medium">₹{Math.max(...priceData.map(p => p.high_price)).toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Low:</span>
                      <span className="font-medium">₹{Math.min(...priceData.map(p => p.low_price)).toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Avg Volume:</span>
                      <span className="font-medium">{Math.round(priceData.reduce((acc, p) => acc + p.volume, 0) / priceData.length).toLocaleString()}</span>
                    </div>
                  </div>
                </div>
                
                <div className="flex gap-2">
                  <Input
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    className="text-sm"
                  />
                  <Input
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    className="text-sm"
                  />
                </div>
              </div>
            )}
          </Card>
        </div>
      )}

      {/* Historical Data Table */}
      {selectedSymbol && priceData.length > 0 && (
        <Card className="p-6">
          <h2 className="text-xl font-semibold mb-4">Historical Data - {selectedSymbol}</h2>

          {priceLoading ? (
            <div className="flex justify-center py-8">
              <div className="text-gray-500">Loading price data...</div>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full border-collapse border border-gray-300">
                <thead>
                  <tr className="bg-gray-50">
                    <th className="border border-gray-300 px-4 py-2 text-left">Date</th>
                    <th className="border border-gray-300 px-4 py-2 text-right">Open</th>
                    <th className="border border-gray-300 px-4 py-2 text-right">High</th>
                    <th className="border border-gray-300 px-4 py-2 text-right">Low</th>
                    <th className="border border-gray-300 px-4 py-2 text-right">Close</th>
                    <th className="border border-gray-300 px-4 py-2 text-right">Volume</th>
                  </tr>
                </thead>
                <tbody>
                  {priceData.slice(0, 100).map((record, index) => (
                    <tr key={record._id || `${record.symbol}-${record.date}-${index}`} className="hover:bg-gray-50">
                      <td className="border border-gray-300 px-4 py-2">
                        {new Date(record.date).toLocaleDateString()}
                      </td>
                      <td className="border border-gray-300 px-4 py-2 text-right">
                        ₹{record.open_price.toFixed(2)}
                      </td>
                      <td className="border border-gray-300 px-4 py-2 text-right">
                        ₹{record.high_price.toFixed(2)}
                      </td>
                      <td className="border border-gray-300 px-4 py-2 text-right">
                        ₹{record.low_price.toFixed(2)}
                      </td>
                      <td className="border border-gray-300 px-4 py-2 text-right">
                        ₹{record.close_price.toFixed(2)}
                      </td>
                      <td className="border border-gray-300 px-4 py-2 text-right">
                        {record.volume.toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {priceData.length > 100 && (
                <div className="text-gray-500 text-center py-4">
                  Showing first 100 records of {priceData.length} total records
                </div>
              )}
            </div>
          )}
        </Card>
      )}

      {/* Show message when no symbol selected */}
      {!selectedSymbol && (
        <Card className="p-8">
          <div className="text-center text-gray-500">
            <ChartBarIcon className="h-12 w-12 mx-auto mb-4 text-gray-300" />
            <h3 className="text-lg font-medium mb-2">No Symbol Selected</h3>
            <p>Select a symbol from the mappings table above to view its price data and charts.</p>
          </div>
        </Card>
      )}
    </div>
  );
}
