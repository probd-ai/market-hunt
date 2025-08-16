'use client';

import { useState, useEffect, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { ProcessEntry, TaskProgress, SchedulerData } from '@/types';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { 
  ClockIcon, 
  PlayIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  ArrowPathIcon,
  TrashIcon,
  XMarkIcon,
  DocumentTextIcon,
  ChevronDownIcon,
  ChevronUpIcon
} from '@heroicons/react/24/outline';

type ProcessStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';

export default function SchedulerPage() {
  const [autoRefresh, setAutoRefresh] = useState<boolean>(true);
  const [expandedProcessId, setExpandedProcessId] = useState<string | null>(null);
  const [selectedProcessDetails, setSelectedProcessDetails] = useState<ProcessEntry | null>(null);

  console.log('SchedulerPage render, autoRefresh:', autoRefresh);

  // Fetch all processes from scheduler
  const { data: schedulerData, isLoading, refetch } = useQuery({
    queryKey: ['schedulerData'],
    queryFn: () => {
      console.log('Fetching scheduler data...');
      return api.getAllProcesses();
    },
    refetchInterval: autoRefresh ? 10000 : false, // Auto-refresh every 10 seconds
    staleTime: 5000, // Data is fresh for 5 seconds
    refetchOnWindowFocus: false, // Prevent unnecessary refetches
  });

  // Fetch process details when expanded
  const { data: processDetails, isLoading: isLoadingDetails } = useQuery({
    queryKey: ['processDetails', expandedProcessId],
    queryFn: () => expandedProcessId ? api.getProcessDetails(expandedProcessId) : null,
    enabled: !!expandedProcessId,
    staleTime: 30000, // Details are fresh for 30 seconds
  });

  // Handle expanding process details
  const handleToggleDetails = (processId: string) => {
    if (expandedProcessId === processId) {
      setExpandedProcessId(null);
      setSelectedProcessDetails(null);
    } else {
      setExpandedProcessId(processId);
    }
  };

  // Update selected process details when data changes
  useEffect(() => {
    if (processDetails) {
      setSelectedProcessDetails(processDetails);
    }
  }, [processDetails]);

  // Memoize running task IDs to prevent unnecessary re-renders
  const runningTaskIds = useMemo(() => {
    const tasks = schedulerData?.running || [];
    const ids = tasks.map(t => t.id).sort().join(',');
    console.log('runningTaskIds computed:', ids);
    return ids; // Sort and join for stable comparison
  }, [schedulerData?.running]);

  const runningTasks = schedulerData?.running || [];
  
  const { data: progressUpdates = [] } = useQuery({
    queryKey: ['progressUpdates', runningTaskIds], // Use stable string instead of array
    queryFn: async () => {
      console.log('Fetching progress updates for tasks:', runningTaskIds);
      if (runningTasks.length === 0) return [];
      const updates = await Promise.all(
        runningTasks.map(task => 
          api.getProcessProgress(task.id).catch(() => null)
        )
      );
      return updates.filter(update => update !== null) as TaskProgress[];
    },
    enabled: runningTasks.length > 0,
    refetchInterval: autoRefresh ? 5000 : false, // Refresh progress every 5 seconds
    staleTime: 2000, // Data is fresh for 2 seconds
    refetchOnWindowFocus: false, // Prevent unnecessary refetches
  });

  // Get progress data for a specific task
  const getProgressData = (taskId: string): TaskProgress | null => {
    return progressUpdates.find(p => p.task_id === taskId) || null;
  };

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="text-center py-8">
          <div className="text-gray-500">Loading scheduler data...</div>
        </div>
      </div>
    );
  }

  // Get all processes and group by status
  const allProcesses = [
    ...(schedulerData?.pending || []),
    ...(schedulerData?.running || []),
    ...(schedulerData?.completed || [])
  ];

  // Group processes by status
  const processesByStatus = {
    pending: schedulerData?.pending || [],
    running: schedulerData?.running || [],
    completed: schedulerData?.completed || [],
    failed: schedulerData?.completed?.filter(p => p.status === 'failed') || [],
  };

  const getStatusIcon = (status: ProcessStatus) => {
    switch (status) {
      case 'pending': return <ClockIcon className="h-5 w-5 text-yellow-600" />;
      case 'running': return <PlayIcon className="h-5 w-5 text-blue-600" />;
      case 'completed': return <CheckCircleIcon className="h-5 w-5 text-green-600" />;
      case 'failed': return <ExclamationTriangleIcon className="h-5 w-5 text-red-600" />;
      default: return <ClockIcon className="h-5 w-5 text-gray-600" />;
    }
  };

  const getStatusColor = (status: ProcessStatus) => {
    switch (status) {
      case 'pending': return 'bg-yellow-50 border-yellow-200';
      case 'running': return 'bg-blue-50 border-blue-200';
      case 'completed': return 'bg-green-50 border-green-200';
      case 'failed': return 'bg-red-50 border-red-200';
      default: return 'bg-gray-50 border-gray-200';
    }
  };

  const formatDuration = (startTime: string, endTime?: string) => {
    if (!startTime) return 'Unknown';
    const start = new Date(startTime);
    const end = endTime ? new Date(endTime) : new Date();
    const diff = end.getTime() - start.getTime();
    const minutes = Math.floor(diff / 60000);
    const seconds = Math.floor((diff % 60000) / 1000);
    return `${minutes}m ${seconds}s`;
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Stock Data Scheduler</h1>
          <p className="text-gray-600 mt-2">Monitor and manage stock data processing tasks</p>
        </div>
        <div className="flex items-center space-x-4">
          <Button
            onClick={() => setAutoRefresh(!autoRefresh)}
            variant={autoRefresh ? "primary" : "outline"}
            size="sm"
          >
            <ArrowPathIcon className="h-4 w-4 mr-2" />
            {autoRefresh ? 'Auto-Refresh ON' : 'Auto-Refresh OFF'}
          </Button>
          <Button onClick={() => refetch()} variant="outline" size="sm">
            Refresh Now
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-2xl font-bold text-yellow-600">
                {processesByStatus.pending.length}
              </div>
              <div className="text-sm text-gray-600">Pending</div>
            </div>
            <ClockIcon className="h-8 w-8 text-yellow-600" />
          </div>
        </Card>
        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-2xl font-bold text-blue-600">
                {processesByStatus.running.length}
              </div>
              <div className="text-sm text-gray-600">Running</div>
            </div>
            <PlayIcon className="h-8 w-8 text-blue-600" />
          </div>
        </Card>
        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-2xl font-bold text-green-600">
                {processesByStatus.completed.length}
              </div>
              <div className="text-sm text-gray-600">Completed</div>
            </div>
            <CheckCircleIcon className="h-8 w-8 text-green-600" />
          </div>
        </Card>
        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-2xl font-bold text-red-600">
                {processesByStatus.failed.length}
              </div>
              <div className="text-sm text-gray-600">Failed</div>
            </div>
            <ExclamationTriangleIcon className="h-8 w-8 text-red-600" />
          </div>
        </Card>
      </div>

      {allProcesses.length === 0 ? (
        <Card className="p-8 text-center">
          <div className="text-gray-500">
            <ClockIcon className="h-12 w-12 mx-auto mb-4 text-gray-400" />
            <h3 className="text-lg font-medium mb-2">No Processes Found</h3>
            <p>No stock data processing tasks have been started yet.</p>
            <Button 
              onClick={() => window.history.back()} 
              className="mt-4"
              variant="outline"
            >
              Go Back to Start a Process
            </Button>
          </div>
        </Card>
      ) : (
        <div className="space-y-6">
          {/* Running Processes - Priority Display */}
          {processesByStatus.running.length > 0 && (
            <Card className="p-6">
              <h2 className="text-xl font-semibold mb-4 flex items-center">
                <PlayIcon className="h-6 w-6 text-blue-600 mr-2" />
                Currently Running ({processesByStatus.running.length})
              </h2>
              <div className="space-y-4">
                {processesByStatus.running.map((process) => {
                  const progress = getProgressData(process.id);
                  return (
                    <div key={process.id} className="border rounded-lg p-4 bg-blue-50 border-blue-200">
                      <div className="flex justify-between items-start mb-3">
                        <div className="flex-1">
                          <div className="flex items-center mb-2">
                            <PlayIcon className="h-5 w-5 text-blue-600 mr-2" />
                            <span className="font-medium">
                              {process.type} - {process.symbol || process.index_name || process.industry}
                            </span>
                          </div>
                          <div className="text-sm text-gray-600">
                            Started: {process.started_at ? new Date(process.started_at).toLocaleString() : 'Unknown'}
                          </div>
                          <div className="text-sm text-gray-600">
                            Duration: {process.started_at ? formatDuration(process.started_at) : 'Unknown'}
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="text-sm font-medium text-blue-600">
                            {progress?.progress ?? (process.items_processed && process.total_items ? Math.round((process.items_processed / process.total_items) * 100) : 0)}%
                          </div>
                          <div className="text-xs text-gray-500">
                            {progress ? `${progress.items_processed}/${progress.total_items}` : 
                             `${process.items_processed}/${process.total_items}`}
                          </div>
                        </div>
                      </div>
                      
                      {/* Progress Bar */}
                      <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
                        <div 
                          className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                          style={{ width: `${progress?.progress ?? (process.items_processed && process.total_items ? Math.round((process.items_processed / process.total_items) * 100) : 0)}%` }}
                        />
                      </div>
                      
                      {/* Current Item */}
                      {progress?.current_item && (
                        <div className="text-sm text-blue-700 bg-blue-100 p-2 rounded">
                          Currently processing: <span className="font-medium">{progress.current_item}</span>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </Card>
          )}

          {/* Pending Processes */}
          {processesByStatus.pending.length > 0 && (
            <Card className="p-6">
              <h2 className="text-xl font-semibold mb-4 flex items-center">
                <ClockIcon className="h-6 w-6 text-yellow-600 mr-2" />
                Pending Queue ({processesByStatus.pending.length})
              </h2>
              <div className="space-y-3">
                {processesByStatus.pending.map((process, index) => (
                  <div key={process.id} className="border rounded-lg p-4 bg-yellow-50 border-yellow-200">
                    <div className="flex justify-between items-center">
                      <div className="flex items-center">
                        <div className="bg-yellow-100 text-yellow-800 text-xs px-2 py-1 rounded mr-3">
                          #{index + 1} in queue
                        </div>
                        <span className="font-medium">
                          {process.type} - {process.symbol || process.index_name || process.industry}
                        </span>
                      </div>
                      <div className="text-sm text-gray-500">
                        Queued: {process.started_at ? new Date(process.started_at).toLocaleString() : 'Unknown'}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* Recent Completed/Failed */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Completed */}
            {processesByStatus.completed.length > 0 && (
              <Card className="p-6">
                <h2 className="text-xl font-semibold mb-4 flex items-center">
                  <CheckCircleIcon className="h-6 w-6 text-green-600 mr-2" />
                  Recently Completed ({processesByStatus.completed.length})
                </h2>
                <div className="space-y-3 max-h-64 overflow-y-auto">
                  {processesByStatus.completed.slice(0, 10).map((process) => (
                    <div key={process.id} className="border rounded-lg bg-green-50 border-green-200">
                      <div className="p-3">
                        <div className="flex justify-between items-start">
                          <div className="flex-1">
                            <div className="font-medium text-sm">
                              {process.type} - {process.symbol || process.index_name || process.industry}
                            </div>
                            <div className="text-xs text-gray-600">
                              Completed: {process.completed_at ? new Date(process.completed_at).toLocaleString() : 'Unknown'}
                            </div>
                            <div className="text-xs text-gray-600">
                              Duration: {process.started_at && process.completed_at ? formatDuration(process.started_at, process.completed_at) : 'Unknown'}
                            </div>
                          </div>
                          <div className="flex items-center space-x-2">
                            <div className="text-xs text-green-600">
                              ✓ {process.items_processed}/{process.total_items}
                            </div>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleToggleDetails(process.id)}
                              className="text-xs"
                            >
                              <DocumentTextIcon className="h-3 w-3 mr-1" />
                              {expandedProcessId === process.id ? (
                                <>
                                  Hide Details
                                  <ChevronUpIcon className="h-3 w-3 ml-1" />
                                </>
                              ) : (
                                <>
                                  View Details
                                  <ChevronDownIcon className="h-3 w-3 ml-1" />
                                </>
                              )}
                            </Button>
                          </div>
                        </div>
                      </div>
                      
                      {/* Expandable Details Section */}
                      {expandedProcessId === process.id && (
                        <div className="border-t border-green-200 bg-green-25 p-4">
                          {isLoadingDetails ? (
                            <div className="text-center py-4">
                              <div className="text-sm text-gray-500">Loading details...</div>
                            </div>
                          ) : selectedProcessDetails ? (
                            <div className="space-y-4">
                              {/* Summary Section */}
                              {selectedProcessDetails.summary && Object.keys(selectedProcessDetails.summary).length > 0 && (
                                <div>
                                  <h4 className="text-sm font-semibold text-gray-800 mb-2">Processing Summary</h4>
                                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
                                    {Object.entries(selectedProcessDetails.summary).map(([key, value]) => (
                                      <div key={key} className="bg-white p-2 rounded border">
                                        <div className="font-medium text-gray-600 capitalize">
                                          {key.replace(/_/g, ' ')}
                                        </div>
                                        <div className="text-gray-800 font-semibold">
                                          {typeof value === 'number' ? value.toLocaleString() : String(value)}
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}
                              
                              {/* Detailed Processing Results */}
                              {selectedProcessDetails.processing_details && selectedProcessDetails.processing_details.length > 0 && (
                                <div>
                                  <h4 className="text-sm font-semibold text-gray-800 mb-2">
                                    Per-Symbol Processing Results ({selectedProcessDetails.processing_details.length} symbols)
                                  </h4>
                                  <div className="max-h-48 overflow-y-auto">
                                    <table className="w-full text-xs">
                                      <thead className="bg-gray-100 sticky top-0">
                                        <tr>
                                          <th className="text-left p-2 border">Symbol</th>
                                          <th className="text-left p-2 border">Status</th>
                                          <th className="text-right p-2 border">Added</th>
                                          <th className="text-right p-2 border">Updated</th>
                                          <th className="text-right p-2 border">Skipped</th>
                                          <th className="text-right p-2 border">Duration</th>
                                        </tr>
                                      </thead>
                                      <tbody>
                                        {selectedProcessDetails.processing_details.map((detail: any, index: number) => (
                                          <tr key={index} className="hover:bg-gray-50">
                                            <td className="p-2 border font-medium">{detail.symbol}</td>
                                            <td className="p-2 border">
                                              <span className={`px-2 py-1 rounded text-xs ${
                                                detail.status === 'success' 
                                                  ? 'bg-green-100 text-green-800' 
                                                  : detail.status === 'error'
                                                  ? 'bg-red-100 text-red-800'
                                                  : 'bg-yellow-100 text-yellow-800'
                                              }`}>
                                                {detail.status}
                                              </span>
                                            </td>
                                            <td className="p-2 border text-right text-green-600 font-medium">
                                              {detail.records_added || 0}
                                            </td>
                                            <td className="p-2 border text-right text-blue-600 font-medium">
                                              {detail.records_updated || 0}
                                            </td>
                                            <td className="p-2 border text-right text-gray-600">
                                              {detail.records_skipped || 0}
                                            </td>
                                            <td className="p-2 border text-right text-gray-600">
                                              {detail.processing_time || 'N/A'}
                                            </td>
                                          </tr>
                                        ))}
                                      </tbody>
                                    </table>
                                  </div>
                                </div>
                              )}
                              
                              {/* Error Messages */}
                              {selectedProcessDetails.error_message && (
                                <div>
                                  <h4 className="text-sm font-semibold text-red-800 mb-2">Error Details</h4>
                                  <div className="bg-red-50 border border-red-200 p-3 rounded text-xs text-red-700">
                                    {selectedProcessDetails.error_message}
                                  </div>
                                </div>
                              )}
                              
                              {/* No Details Available */}
                              {(!selectedProcessDetails.processing_details || selectedProcessDetails.processing_details.length === 0) &&
                               (!selectedProcessDetails.summary || Object.keys(selectedProcessDetails.summary).length === 0) && (
                                <div className="text-center py-4">
                                  <div className="text-sm text-gray-500">No detailed processing information available for this process.</div>
                                </div>
                              )}
                            </div>
                          ) : (
                            <div className="text-center py-4">
                              <div className="text-sm text-red-500">Failed to load process details</div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </Card>
            )}

            {/* Failed */}
            {processesByStatus.failed.length > 0 && (
              <Card className="p-6">
                <h2 className="text-xl font-semibold mb-4 flex items-center">
                  <ExclamationTriangleIcon className="h-6 w-6 text-red-600 mr-2" />
                  Failed Processes ({processesByStatus.failed.length})
                </h2>
                <div className="space-y-3 max-h-64 overflow-y-auto">
                  {processesByStatus.failed.slice(0, 10).map((process) => (
                    <div key={process.id} className="border rounded-lg p-3 bg-red-50 border-red-200">
                      <div className="flex justify-between items-start">
                        <div>
                          <div className="font-medium text-sm">
                            {process.type} - {process.symbol || process.index_name || process.industry}
                          </div>
                          <div className="text-xs text-gray-600">
                            Failed: {process.completed_at ? new Date(process.completed_at).toLocaleString() : 'Unknown'}
                          </div>
                          {process.error_message && (
                            <div className="text-xs text-red-600 mt-1">
                              Error: {process.error_message}
                            </div>
                          )}
                        </div>
                        <Button size="sm" variant="outline" className="text-xs">
                          Retry
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
