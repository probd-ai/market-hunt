'use client';

import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import { 
  ChartBarIcon,
  DocumentTextIcon,
  ClockIcon,
  ArrowDownTrayIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  BuildingOfficeIcon
} from '@heroicons/react/24/outline';
import { formatNumber, formatDate } from '@/lib/utils';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { DataOverview } from '@/types';
import { useState } from 'react';

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#06B6D4'];

interface IndexIndustriesData {
  index_name: string;
  total_industries: number;
  industries: Array<{
    _id: string;
    count: number;
  }>;
}

interface IndexIndustryCompaniesData {
  index_name: string;
  industry_name: string;
  total_companies: number;
  companies: Array<{
    'Company Name': string;
    'Industry': string;
    'Symbol': string;
    'Series': string;
    'ISIN Code': string;
    download_timestamp?: string;
  }>;
}

export default function IndexesPage() {
  const [selectedIndex, setSelectedIndex] = useState<string | null>(null);
  const [selectedIndustryInIndex, setSelectedIndustryInIndex] = useState<{ index: string; industry: string } | null>(null);
  
  const { data: overview, isLoading: overviewLoading, error: overviewError } = useQuery<DataOverview>({
    queryKey: ['dataOverview'],
    queryFn: () => apiClient.getDataOverview(),
    refetchInterval: 30000,
  });

  const { data: indexIndustries, isLoading: industriesLoading, error: industriesError } = useQuery<IndexIndustriesData>({
    queryKey: ['indexIndustries', selectedIndex],
    queryFn: () => apiClient.getIndexIndustries(selectedIndex!),
    enabled: !!selectedIndex,
  });

  const { data: indexIndustryCompanies, isLoading: industryCompaniesLoading, error: industryCompaniesError } = useQuery<IndexIndustryCompaniesData>({
    queryKey: ['indexIndustryCompanies', selectedIndustryInIndex?.index, selectedIndustryInIndex?.industry],
    queryFn: () => apiClient.getIndexIndustryCompanies(selectedIndustryInIndex!.index, selectedIndustryInIndex!.industry),
    enabled: !!selectedIndustryInIndex,
  });

  const handleIndexClick = (indexName: string) => {
    setSelectedIndex(selectedIndex === indexName ? null : indexName);
    setSelectedIndustryInIndex(null); // Close industry companies view
  };

  const handleIndustryClick = (indexName: string, industryName: string) => {
    const newSelection = { index: indexName, industry: industryName };
    setSelectedIndustryInIndex(
      selectedIndustryInIndex?.index === indexName && selectedIndustryInIndex?.industry === industryName 
        ? null 
        : newSelection
    );
  };

  if (overviewLoading) {
    return (
      <DashboardLayout>
        <div className="p-6">
          <div className="animate-pulse">
            <div className="h-8 bg-gray-200 rounded w-1/4 mb-6"></div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-32 bg-gray-200 rounded"></div>
              ))}
            </div>
          </div>
        </div>
      </DashboardLayout>
    );
  }

  if (overviewError) {
    return (
      <DashboardLayout>
        <div className="p-6">
          <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded">
            <h2 className="font-semibold mb-2">Failed to load indexes data</h2>
            <p>{overviewError instanceof Error ? overviewError.message : 'An unexpected error occurred'}</p>
          </div>
        </div>
      </DashboardLayout>
    );
  }

  if (!overview) {
    return null;
  }

  // Prepare chart data
  const chartData = overview.index_stats.map((stat) => ({
    name: stat._id,
    count: stat.count,
  }));

  return (
    <DashboardLayout>
      <div className="space-y-6 p-6">
        <div className="flex justify-between items-center">
          <h1 className="text-3xl font-bold text-gray-900">Indexes Overview</h1>
          <div className="flex items-center space-x-2 text-sm text-gray-500">
            <ClockIcon className="h-4 w-4" />
            <span>Last updated: {formatDate(new Date())}</span>
          </div>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Companies</CardTitle>
              <DocumentTextIcon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatNumber(overview.total_documents)}</div>
              <p className="text-xs text-muted-foreground">
                Across {overview.index_stats.length} indices
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Active Indices</CardTitle>
              <ChartBarIcon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{overview.index_stats.length}</div>
              <p className="text-xs text-muted-foreground">
                Market indices tracked
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Data Sources</CardTitle>
              <ArrowDownTrayIcon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">CSV Files</div>
              <p className="text-xs text-muted-foreground">
                Automated data collection
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle>Companies by Index</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis 
                    dataKey="name" 
                    angle={-45}
                    textAnchor="end"
                    height={80}
                    interval={0}
                  />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="count" fill="#3B82F6" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Index Distribution</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={chartData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name} ${((percent || 0) * 100).toFixed(0)}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="count"
                  >
                    {chartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </div>

        {/* Index Details with Industries and Companies */}
        <Card>
          <CardHeader>
            <CardTitle>Index Details</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4">
              {overview.index_stats.map((stat) => (
                <div key={stat._id} className="border-b border-gray-200 last:border-b-0 pb-4 last:pb-0">
                  <div className="flex items-center justify-between">
                    <button
                      onClick={() => handleIndexClick(stat._id)}
                      className="flex items-center space-x-2 text-left hover:text-blue-600 transition-colors duration-200 focus:outline-none focus:text-blue-600"
                    >
                      <span className="font-medium text-lg">{stat._id}</span>
                      {selectedIndex === stat._id ? (
                        <ChevronUpIcon className="h-5 w-5 text-gray-500" />
                      ) : (
                        <ChevronDownIcon className="h-5 w-5 text-gray-500" />
                      )}
                    </button>
                    <span className="text-2xl font-bold text-blue-600">{formatNumber(stat.count)}</span>
                  </div>
                  
                  {/* Industries List */}
                  {selectedIndex === stat._id && (
                    <div className="mt-4 pl-4 border-l-2 border-blue-200">
                      {industriesLoading ? (
                        <div className="text-gray-500">Loading industries...</div>
                      ) : industriesError ? (
                        <div className="text-red-500">
                          Error loading industries: {industriesError instanceof Error ? industriesError.message : 'Unknown error'}
                        </div>
                      ) : indexIndustries ? (
                        <div className="space-y-3">
                          <div className="text-sm text-gray-600 mb-3 flex items-center">
                            <BuildingOfficeIcon className="h-4 w-4 mr-1" />
                            {indexIndustries.total_industries} industries in {stat._id}
                          </div>
                          <div className="space-y-2">
                            {indexIndustries.industries.map((industry, idx) => (
                              <div key={idx} className="bg-green-50 p-3 rounded border">
                                <div className="flex justify-between items-center">
                                  <button
                                    onClick={() => handleIndustryClick(stat._id, industry._id)}
                                    className="flex items-center space-x-2 text-left hover:text-green-700 transition-colors duration-200 focus:outline-none focus:text-green-700"
                                  >
                                    <span className="font-medium text-gray-900">{industry._id}</span>
                                    {selectedIndustryInIndex?.index === stat._id && selectedIndustryInIndex?.industry === industry._id ? (
                                      <ChevronUpIcon className="h-4 w-4 text-gray-500" />
                                    ) : (
                                      <ChevronDownIcon className="h-4 w-4 text-gray-500" />
                                    )}
                                  </button>
                                  <span className="text-lg font-semibold text-green-600">{formatNumber(industry.count)}</span>
                                </div>
                                
                                {/* Companies List for Industry in Index */}
                                {selectedIndustryInIndex?.index === stat._id && selectedIndustryInIndex?.industry === industry._id && (
                                  <div className="mt-3 pl-4 border-l-2 border-green-300">
                                    {industryCompaniesLoading ? (
                                      <div className="text-gray-500 text-sm">Loading companies...</div>
                                    ) : industryCompaniesError ? (
                                      <div className="text-red-500 text-sm">
                                        Error loading companies: {industryCompaniesError instanceof Error ? industryCompaniesError.message : 'Unknown error'}
                                      </div>
                                    ) : indexIndustryCompanies ? (
                                      <div className="space-y-2">
                                        <div className="text-xs text-gray-600 mb-2">
                                          {indexIndustryCompanies.total_companies} companies in {industry._id} from {stat._id}
                                        </div>
                                        <div className="max-h-64 overflow-y-auto space-y-1">
                                          {indexIndustryCompanies.companies.map((company, companyIdx) => (
                                            <div key={companyIdx} className="bg-white p-2 rounded border text-sm">
                                              <div className="font-medium text-gray-900">{company['Company Name']}</div>
                                              <div className="text-xs text-gray-600 mt-1">
                                                <span className="inline-block mr-3">Symbol: {company.Symbol}</span>
                                                <span className="inline-block">Series: {company.Series}</span>
                                              </div>
                                              {company['ISIN Code'] && (
                                                <div className="text-xs text-gray-500 mt-1">
                                                  ISIN: {company['ISIN Code']}
                                                </div>
                                              )}
                                            </div>
                                          ))}
                                        </div>
                                      </div>
                                    ) : null}
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      ) : null}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}
