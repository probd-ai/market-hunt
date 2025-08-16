'use client';

import { useState, useEffect } from 'react';
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
  XMarkIcon
} from '@heroicons/react/24/outline';

type ProcessStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';

export default function SchedulerPage() {
  const [autoRefresh, setAutoRefresh] = useState<boolean>(true);

  // Fetch all processes from scheduler
  const { data: schedulerData, isLoading, refetch } = useQuery({
    queryKey: ['schedulerData'],
    queryFn: () => api.getAllProcesses(),
    refetchInterval: autoRefresh ? 3000 : false, // Auto-refresh every 3 seconds
  });

  // Fetch progress for running tasks
  const runningTasks = schedulerData?.running || [];
  
  const { data: progressUpdates = [] } = useQuery({
    queryKey: ['progressUpdates', runningTasks.map(t => t.id)],
    queryFn: async () => {
      const updates = await Promise.all(
        runningTasks.map(task => 
          api.getProcessProgress(task.id).catch(() => null)
        )
      );
      return updates.filter(update => update !== null) as TaskProgress[];
    },
    enabled: runningTasks.length > 0,
    refetchInterval: autoRefresh ? 2000 : false, // Faster refresh for progress
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
                  const progress = getProgressData(process.task_id || process.id);
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
                            {progress?.progress_percentage ?? process.progress_percentage ?? 0}%
                          </div>
                          <div className="text-xs text-gray-500">
                            {progress ? `${progress.current_count}/${progress.total_count}` : 
                             `${process.items_processed}/${process.total_items}`}
                          </div>
                        </div>
                      </div>
                      
                      {/* Progress Bar */}
                      <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
                        <div 
                          className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                          style={{ width: `${progress?.progress_percentage ?? process.progress_percentage ?? 0}%` }}
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
                    <div key={process.id} className="border rounded-lg p-3 bg-green-50 border-green-200">
                      <div className="flex justify-between items-start">
                        <div>
                          <div className="font-medium text-sm">
                            {process.type} - {process.symbol || process.index_name || process.industry}
                          </div>
                          <div className="text-xs text-gray-600">
                            Completed: {process.completed_at ? new Date(process.completed_at).toLocaleString() : 'Unknown'}
                          </div>
                        </div>
                        <div className="text-xs text-green-600">
                          ✓ {process.items_processed}/{process.total_items}
                        </div>
                      </div>
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
