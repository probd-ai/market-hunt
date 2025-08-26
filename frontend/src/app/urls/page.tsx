'use client';

import { useState } from 'react';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import { URLConfig, URLFormData } from '@/types';
import { 
  PlusIcon,
  PencilIcon,
  TrashIcon,
  PlayIcon,
  CheckCircleIcon,
  XCircleIcon,
  ExclamationTriangleIcon,
  LinkIcon
} from '@heroicons/react/24/outline';
import { formatDate } from '@/lib/utils';

export default function URLManagementPage() {
  const [isAddingUrl, setIsAddingUrl] = useState(false);
  const [editingUrl, setEditingUrl] = useState<URLConfig | null>(null);
  const [selectedUrls, setSelectedUrls] = useState<string[]>([]);
  
  const queryClient = useQueryClient();

  const { data: urls, isLoading } = useQuery({
    queryKey: ['urls'],
    queryFn: () => apiClient.getUrls(),
  });

  const addUrlMutation = useMutation({
    mutationFn: (data: URLFormData) => apiClient.addUrl(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['urls'] });
      setIsAddingUrl(false);
      // Show success message
      alert('URL added successfully!');
    },
    onError: (error: Error) => {
      console.error('Failed to add URL:', error.message);
      // Keep the form open so user can see the error and try again
      alert(`Failed to add URL: ${error.message}`);
    },
  });

  const updateUrlMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<URLFormData> }) => 
      apiClient.updateUrl(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['urls'] });
      setEditingUrl(null);
    },
    onError: (error: Error) => {
      console.error('Failed to update URL:', error.message);
      alert(`Failed to update URL: ${error.message}`);
    },
  });

  const deleteUrlMutation = useMutation({
    mutationFn: (id: string) => apiClient.deleteUrl(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['urls'] });
    },
    onError: (error: Error) => {
      console.error('Failed to delete URL:', error.message);
      alert(`Failed to delete URL: ${error.message}`);
    },
  });

  const processUrlsMutation = useMutation({
    mutationFn: async (urlIds: string[]) => {
      // Call FastAPI backend directly instead of frontend proxy
      const response = await fetch('http://localhost:3001/api/process', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url_ids: urlIds }),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to process URLs');
      }
      
      return response.json();
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['dataOverview'] });
      queryClient.invalidateQueries({ queryKey: ['urls'] }); // Also refresh URL list to show updated download counts
      setSelectedUrls([]);
      
      // Create detailed summary message
      let summaryMessage = `${data.message}\n\n`;
      
      if (data.results && data.results.length > 0) {
        summaryMessage += "Processing Details:\n";
        data.results.forEach((result: any) => {
          if (result.success) {
            summaryMessage += `✅ ${result.index_name}: ${result.documents_loaded} documents loaded\n`;
          } else {
            summaryMessage += `❌ ${result.index_name || 'Unknown'}: ${result.error}\n`;
          }
        });
      }
      
      alert(summaryMessage);
    },
    onError: (error: Error) => {
      console.error('Failed to process URLs:', error.message);
      alert(`Failed to process URLs: ${error.message}`);
    },
  });

  const handleSubmitForm = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    
    const urlData: URLFormData = {
      url: formData.get('url') as string,
      index_name: formData.get('index_name') as string || undefined,
      description: formData.get('description') as string,
      tags: (formData.get('tags') as string)?.split(',').map(t => t.trim()).filter(Boolean) || [],
      is_active: formData.get('is_active') === 'on',
    };

    if (editingUrl) {
      updateUrlMutation.mutate({ id: editingUrl._id, data: urlData });
    } else {
      addUrlMutation.mutate(urlData);
    }
  };

  const getStatusIcon = (url: URLConfig) => {
    if (url.last_error) {
      return <XCircleIcon className="h-5 w-5 text-red-500" />;
    }
    if (url.is_valid && url.is_active) {
      return <CheckCircleIcon className="h-5 w-5 text-green-500" />;
    }
    return <ExclamationTriangleIcon className="h-5 w-5 text-yellow-500" />;
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">URL Management</h1>
            <p className="mt-1 text-sm text-gray-600">
              Manage your CSV data sources and download configurations
            </p>
          </div>
          <Button onClick={() => setIsAddingUrl(true)}>
            <PlusIcon className="h-4 w-4 mr-2" />
            Add URL
          </Button>
        </div>

        {/* Action Bar */}
        {selectedUrls.length > 0 && (
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">
                  {selectedUrls.length} URLs selected
                </span>
                <div className="space-x-2">
                  <Button
                    size="sm"
                    onClick={() => processUrlsMutation.mutate(selectedUrls)}
                    loading={processUrlsMutation.isPending}
                  >
                    <PlayIcon className="h-4 w-4 mr-1" />
                    Process Selected
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setSelectedUrls([])}
                  >
                    Clear Selection
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Add/Edit URL Form */}
        {(isAddingUrl || editingUrl) && (
          <Card>
            <CardHeader>
              <CardTitle>
                {editingUrl ? 'Edit URL Configuration' : 'Add New URL'}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmitForm} className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <Input
                    name="url"
                    label="CSV URL *"
                    placeholder="https://example.com/data.csv"
                    defaultValue={editingUrl?.url}
                    required
                  />
                  <Input
                    name="index_name"
                    label="Index Name"
                    placeholder="Leave empty to auto-extract"
                    defaultValue={editingUrl?.index_name}
                    helperText="Will be auto-extracted from URL if not provided"
                  />
                </div>
                <Input
                  name="description"
                  label="Description"
                  placeholder="Brief description of this data source"
                  defaultValue={editingUrl?.description}
                />
                <Input
                  name="tags"
                  label="Tags"
                  placeholder="equity, large-cap, nifty (comma-separated)"
                  defaultValue={editingUrl?.tags?.join(', ')}
                  helperText="Comma-separated tags for categorization"
                />
                <div className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    name="is_active"
                    id="is_active"
                    defaultChecked={editingUrl?.is_active ?? true}
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <label htmlFor="is_active" className="text-sm text-gray-700">
                    Active (include in bulk operations)
                  </label>
                </div>
                <div className="flex space-x-2">
                  <Button
                    type="submit"
                    loading={addUrlMutation.isPending || updateUrlMutation.isPending}
                  >
                    {editingUrl ? 'Update URL' : 'Add URL'}
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => {
                      setIsAddingUrl(false);
                      setEditingUrl(null);
                    }}
                  >
                    Cancel
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        )}

        {/* URLs List */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Configured URLs</CardTitle>
              <Button
                variant="outline"
                size="sm"
                onClick={() => processUrlsMutation.mutate(
                  urls?.filter(url => url.is_active).map(url => url._id) || []
                )}
                loading={processUrlsMutation.isPending}
                disabled={!urls?.some(url => url.is_active)}
              >
                <PlayIcon className="h-4 w-4 mr-1" />
                Process All Active
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="space-y-4">
                {[...Array(3)].map((_, i) => (
                  <div key={i} className="animate-pulse border rounded-lg p-4">
                    <div className="h-4 bg-gray-200 rounded w-1/4 mb-2"></div>
                    <div className="h-3 bg-gray-200 rounded w-3/4 mb-2"></div>
                    <div className="h-3 bg-gray-200 rounded w-1/2"></div>
                  </div>
                ))}
              </div>
            ) : urls && urls.length > 0 ? (
              <div className="space-y-4">
                {urls.map((url) => (
                  <div
                    key={url._id}
                    className="border rounded-lg p-4 hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-start space-x-3">
                        <input
                          type="checkbox"
                          checked={selectedUrls.includes(url._id)}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setSelectedUrls([...selectedUrls, url._id]);
                            } else {
                              setSelectedUrls(selectedUrls.filter(id => id !== url._id));
                            }
                          }}
                          className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                        />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center space-x-2">
                            {getStatusIcon(url)}
                            <h3 className="text-lg font-medium text-gray-900">
                              {url.index_name}
                            </h3>
                            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                              url.is_active 
                                ? 'bg-green-100 text-green-800' 
                                : 'bg-gray-100 text-gray-800'
                            }`}>
                              {url.is_active ? 'Active' : 'Inactive'}
                            </span>
                          </div>
                          <p className="mt-1 text-sm text-gray-600 truncate">
                            {url.url}
                          </p>
                          {url.description && (
                            <p className="mt-1 text-sm text-gray-500">
                              {url.description}
                            </p>
                          )}
                          <div className="mt-2 flex items-center space-x-4 text-xs text-gray-500">
                            <span>Downloads: {url.download_count}</span>
                            {url.last_downloaded && (
                              <span>Last: {formatDate(url.last_downloaded)}</span>
                            )}
                            <span>Created: {formatDate(url.created_at)}</span>
                          </div>
                          {url.tags && url.tags.length > 0 && (
                            <div className="mt-2 flex flex-wrap gap-1">
                              {url.tags.map((tag) => (
                                <span
                                  key={tag}
                                  className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-blue-50 text-blue-700"
                                >
                                  {tag}
                                </span>
                              ))}
                            </div>
                          )}
                          {url.last_error && (
                            <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded-md">
                              <p className="text-xs text-red-600">
                                <strong>Last Error:</strong> {url.last_error}
                              </p>
                            </div>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center space-x-2">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => setEditingUrl(url)}
                        >
                          <PencilIcon className="h-4 w-4" />
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => processUrlsMutation.mutate([url._id])}
                          loading={processUrlsMutation.isPending}
                        >
                          <PlayIcon className="h-4 w-4" />
                        </Button>
                        <Button
                          size="sm"
                          variant="danger"
                          onClick={() => {
                            if (confirm('Are you sure you want to delete this URL?')) {
                              deleteUrlMutation.mutate(url._id);
                            }
                          }}
                          loading={deleteUrlMutation.isPending}
                        >
                          <TrashIcon className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-12">
                <LinkIcon className="mx-auto h-12 w-12 text-gray-400" />
                <h3 className="mt-2 text-sm font-medium text-gray-900">No URLs configured</h3>
                <p className="mt-1 text-sm text-gray-500">
                  Get started by adding your first CSV data source.
                </p>
                <div className="mt-6">
                  <Button onClick={() => setIsAddingUrl(true)}>
                    <PlusIcon className="h-4 w-4 mr-2" />
                    Add URL
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}
