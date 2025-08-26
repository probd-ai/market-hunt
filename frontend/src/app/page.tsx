'use client';

import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import { 
  ChartBarIcon, 
  LinkIcon, 
  DocumentTextIcon,
  ClockIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon
} from '@heroicons/react/24/outline';
import { formatNumber, formatDate } from '@/lib/utils';
import Link from 'next/link';
import { useState } from 'react';

export default function DashboardPage() {
  const queryClient = useQueryClient();
  const [refreshStatus, setRefreshStatus] = useState<string>('');

  const { data: dataOverview, isLoading } = useQuery({
    queryKey: ['dataOverview'],
    queryFn: () => apiClient.getDataOverview(),
  });

  const { data: urls } = useQuery({
    queryKey: ['urls'],
    queryFn: () => apiClient.getUrls(),
  });

  const refreshDataMutation = useMutation({
    mutationFn: async () => {
      const activeUrls = urls?.filter(url => url.is_active) || [];
      if (activeUrls.length === 0) {
        throw new Error('No active URLs found to process');
      }
      
      const urlIds = activeUrls.map(url => url._id);
      return apiClient.processUrls(urlIds);
    },
    onSuccess: (data) => {
      setRefreshStatus(`✅ Successfully processed ${data.processed_count}/${data.total_count} URLs`);
      // Invalidate and refetch both data overview and URLs
      queryClient.invalidateQueries({ queryKey: ['dataOverview'] });
      queryClient.invalidateQueries({ queryKey: ['urls'] });
      
      // Clear status after 5 seconds
      setTimeout(() => setRefreshStatus(''), 5000);
    },
    onError: (error) => {
      setRefreshStatus(`❌ Error: ${error instanceof Error ? error.message : 'Unknown error'}`);
      setTimeout(() => setRefreshStatus(''), 5000);
    },
  });

  const stats = [
    {
      name: 'Total Documents',
      value: dataOverview?.total_documents || 0,
      icon: DocumentTextIcon,
      color: 'text-blue-600 bg-blue-100',
    },
    {
      name: 'Active URLs',
      value: urls?.filter(url => url.is_active).length || 0,
      icon: LinkIcon,
      color: 'text-green-600 bg-green-100',
    },
    {
      name: 'Indices Tracked',
      value: dataOverview?.index_stats?.length || 0,
      icon: ChartBarIcon,
      color: 'text-purple-600 bg-purple-100',
    },
    {
      name: 'Last Update',
      value: dataOverview?.index_stats?.[0]?.last_update 
        ? formatDate(dataOverview.index_stats[0].last_update)
        : 'Never',
      icon: ClockIcon,
      color: 'text-orange-600 bg-orange-100',
      isDate: true,
    },
  ];

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Page Header */}
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="mt-1 text-sm text-gray-600">
            Welcome to your financial data management platform
          </p>
          {refreshStatus && (
            <div className="mt-2 p-3 rounded-md bg-blue-50 border border-blue-200">
              <p className="text-sm text-blue-800">{refreshStatus}</p>
            </div>
          )}
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {stats.map((stat) => (
            <Card key={stat.name}>
              <CardContent className="p-6">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <div className={`inline-flex items-center justify-center p-3 rounded-lg ${stat.color}`}>
                      <stat.icon className="h-6 w-6" />
                    </div>
                  </div>
                  <div className="ml-5 w-0 flex-1">
                    <dl>
                      <dt className="text-sm font-medium text-gray-500 truncate">
                        {stat.name}
                      </dt>
                      <dd className="text-lg font-semibold text-gray-900">
                        {stat.isDate ? stat.value : formatNumber(Number(stat.value))}
                      </dd>
                    </dl>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Recent Index Updates */}
          <Card>
            <CardHeader>
              <CardTitle>Recent Index Updates</CardTitle>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="space-y-3">
                  {[...Array(3)].map((_, i) => (
                    <div key={i} className="animate-pulse">
                      <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                      <div className="h-3 bg-gray-200 rounded w-1/2 mt-2"></div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="space-y-4">
                  {dataOverview?.index_stats?.slice(0, 5).map((index) => (
                    <div key={index._id} className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-gray-900">{index._id}</p>
                        <p className="text-xs text-gray-500">
                          {formatNumber(index.count)} companies
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-xs text-gray-500">
                          {formatDate(index.last_update)}
                        </p>
                        <div className="flex items-center mt-1">
                          <CheckCircleIcon className="h-3 w-3 text-green-500 mr-1" />
                          <span className="text-xs text-green-600">Updated</span>
                        </div>
                      </div>
                    </div>
                  )) || (
                    <p className="text-sm text-gray-500">No index data available</p>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          {/* URL Status */}
          <Card>
            <CardHeader>
              <CardTitle>URL Status</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {urls?.slice(0, 5).map((url) => (
                  <div key={url._id} className="flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {url.index_name}
                      </p>
                      <p className="text-xs text-gray-500 truncate">
                        {url.url}
                      </p>
                    </div>
                    <div className="flex items-center space-x-2">
                      {url.is_active ? (
                        <CheckCircleIcon className="h-4 w-4 text-green-500" />
                      ) : (
                        <ExclamationTriangleIcon className="h-4 w-4 text-gray-400" />
                      )}
                      <span className={`text-xs px-2 py-1 rounded-full ${
                        url.is_valid 
                          ? 'bg-green-100 text-green-800' 
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {url.is_valid ? 'Valid' : 'Invalid'}
                      </span>
                    </div>
                  </div>
                )) || (
                  <p className="text-sm text-gray-500">No URLs configured</p>
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Quick Actions */}
        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <Link href="/urls">
                <Button className="w-full justify-start h-auto p-4" variant="outline">
                  <LinkIcon className="h-5 w-5 mr-3" />
                  <div className="text-left">
                    <div className="font-medium">Manage URLs</div>
                    <div className="text-xs text-gray-500">Add or edit data sources</div>
                  </div>
                </Button>
              </Link>
              
              <Link href="/data">
                <Button className="w-full justify-start h-auto p-4" variant="outline">
                  <ChartBarIcon className="h-5 w-5 mr-3" />
                  <div className="text-left">
                    <div className="font-medium">View Data</div>
                    <div className="text-xs text-gray-500">Explore index constituents</div>
                  </div>
                </Button>
              </Link>
              
              <Button 
                className="w-full justify-start h-auto p-4" 
                variant="primary"
                onClick={() => refreshDataMutation.mutate()}
                disabled={refreshDataMutation.isPending}
              >
                <DocumentTextIcon className="h-5 w-5 mr-3" />
                <div className="text-left">
                  <div className="font-medium">
                    {refreshDataMutation.isPending ? 'Processing...' : 'Refresh Data'}
                  </div>
                  <div className="text-xs opacity-90">Update all active sources</div>
                </div>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}
