'use client';

import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import { 
  BuildingOfficeIcon,
  ChartBarIcon,
  ClockIcon,
  ChevronDownIcon,
  ChevronUpIcon
} from '@heroicons/react/24/outline';
import { formatNumber, formatDate } from '@/lib/utils';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { useState } from 'react';

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#06B6D4', '#F97316', '#84CC16', '#EC4899', '#6366F1'];

interface IndustriesOverview {
  total_companies: number;
  total_industries: number;
  industry_stats: Array<{
    _id: string;
    count: number;
    indices: string[];
  }>;
}

interface IndustryCompaniesData {
  industry_name: string;
  total_companies: number;
  companies: Array<{
    'Company Name': string;
    'Industry': string;
    'Symbol': string;
    'Series': string;
    'ISIN Code': string;
    'indices': string[];
    download_timestamp?: string;
  }>;
}

interface IndustryIndicesData {
  industry_name: string;
  total_indices: number;
  indices: Array<{
    _id: string;
    count: number;
  }>;
}

interface IndustryIndexCompaniesData {
  industry_name: string;
  index_name: string;
  total_companies: number;
  companies: Array<{
    'Company Name': string;
    'Industry': string;
    'Symbol': string;
    'Series': string;
    'ISIN Code': string;
    'index_name': string;
    download_timestamp?: string;
  }>;
}

export default function IndustriesPage() {
  const [selectedIndustry, setSelectedIndustry] = useState<string | null>(null);
  const [showingIndices, setShowingIndices] = useState<string | null>(null);
  const [selectedIndexInIndustry, setSelectedIndexInIndustry] = useState<{ industry: string; index: string } | null>(null);
  
  const { data: overview, isLoading: overviewLoading, error: overviewError } = useQuery<IndustriesOverview>({
    queryKey: ['industriesOverview'],
    queryFn: () => apiClient.getIndustriesOverview(),
    refetchInterval: 30000,
  });

  const { data: industryCompanies, isLoading: companiesLoading, error: companiesError } = useQuery<IndustryCompaniesData>({
    queryKey: ['industryCompanies', selectedIndustry],
    queryFn: () => apiClient.getIndustryCompanies(selectedIndustry!),
    enabled: !!selectedIndustry,
  });

  const { data: industryIndices, isLoading: indicesLoading, error: indicesError } = useQuery<IndustryIndicesData>({
    queryKey: ['industryIndices', showingIndices],
    queryFn: () => apiClient.getIndustryIndices(showingIndices!),
    enabled: !!showingIndices,
  });

  const { data: industryIndexCompanies, isLoading: indexCompaniesLoading, error: indexCompaniesError } = useQuery<IndustryIndexCompaniesData>({
    queryKey: ['industryIndexCompanies', selectedIndexInIndustry?.industry, selectedIndexInIndustry?.index],
    queryFn: () => apiClient.getIndustryIndexCompanies(selectedIndexInIndustry!.industry, selectedIndexInIndustry!.index),
    enabled: !!selectedIndexInIndustry,
  });

  const handleIndustryClick = (industryName: string) => {
    setSelectedIndustry(selectedIndustry === industryName ? null : industryName);
    setShowingIndices(null); // Close indices view when switching industries
    setSelectedIndexInIndustry(null); // Close index companies view
  };

  const handleIndicesClick = (industryName: string) => {
    setShowingIndices(showingIndices === industryName ? null : industryName);
    setSelectedIndustry(null); // Close companies view when showing indices
    setSelectedIndexInIndustry(null); // Close index companies view
  };

  const handleIndexClick = (industryName: string, indexName: string) => {
    const newSelection = { industry: industryName, index: indexName };
    setSelectedIndexInIndustry(
      selectedIndexInIndustry?.industry === industryName && selectedIndexInIndustry?.index === indexName 
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
            <h2 className="font-semibold mb-2">Failed to load industries data</h2>
            <p>{overviewError instanceof Error ? overviewError.message : 'An unexpected error occurred'}</p>
          </div>
        </div>
      </DashboardLayout>
    );
  }

  if (!overview) {
    return null;
  }

  // Prepare chart data - top 10 industries
  const chartData = overview.industry_stats.slice(0, 10).map((stat) => ({
    name: stat._id.length > 20 ? stat._id.substring(0, 20) + '...' : stat._id,
    fullName: stat._id,
    count: stat.count,
  }));

  // Prepare pie chart data - top 8 industries
  const pieData = overview.industry_stats.slice(0, 8).map((stat) => ({
    name: stat._id.length > 15 ? stat._id.substring(0, 15) + '...' : stat._id,
    fullName: stat._id,
    count: stat.count,
  }));

  return (
    <DashboardLayout>
      <div className="space-y-6 p-6">
        <div className="flex justify-between items-center">
          <h1 className="text-3xl font-bold text-gray-900">Industries Overview</h1>
          <div className="flex items-center space-x-2 text-sm text-gray-500">
            <ClockIcon className="h-4 w-4" />
            <span>Last updated: {formatDate(new Date())}</span>
          </div>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Unique Companies</CardTitle>
              <BuildingOfficeIcon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatNumber(overview.total_companies)}</div>
              <p className="text-xs text-muted-foreground">
                Unique companies across all industries
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Industries</CardTitle>
              <ChartBarIcon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{overview.total_industries}</div>
              <p className="text-xs text-muted-foreground">
                Unique industry sectors
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Largest Industry</CardTitle>
              <ChartBarIcon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatNumber(overview.industry_stats[0]?.count || 0)}</div>
              <p className="text-xs text-muted-foreground">
                {overview.industry_stats[0]?._id || 'N/A'}
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle>Top 10 Industries by Company Count</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis 
                    dataKey="name" 
                    angle={-45}
                    textAnchor="end"
                    height={100}
                    interval={0}
                    fontSize={12}
                  />
                  <YAxis />
                  <Tooltip 
                    formatter={(value, name, props) => [value, 'Companies']}
                    labelFormatter={(label) => {
                      const item = chartData.find(d => d.name === label);
                      return item?.fullName || label;
                    }}
                  />
                  <Bar dataKey="count" fill="#3B82F6" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Industry Distribution</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name} ${((percent || 0) * 100).toFixed(1)}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="count"
                  >
                    {pieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip 
                    formatter={(value, name, props) => [value, 'Companies']}
                    labelFormatter={(label) => {
                      const item = pieData.find(d => d.name === label);
                      return item?.fullName || label;
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </div>

        {/* Industries List with Clickable Names */}
        <Card>
          <CardHeader>
            <CardTitle>All Industries</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4">
              {overview.industry_stats.map((stat) => (
                <div key={stat._id} className="border-b border-gray-200 last:border-b-0 pb-4 last:pb-0">
                  <div className="flex items-center justify-between">
                    <button
                      onClick={() => handleIndustryClick(stat._id)}
                      className="flex items-center space-x-2 text-left hover:text-blue-600 transition-colors duration-200 focus:outline-none focus:text-blue-600"
                    >
                      <span className="font-medium text-lg">{stat._id}</span>
                      {selectedIndustry === stat._id ? (
                        <ChevronUpIcon className="h-5 w-5 text-gray-500" />
                      ) : (
                        <ChevronDownIcon className="h-5 w-5 text-gray-500" />
                      )}
                    </button>
                    <div className="flex items-center space-x-4">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleIndicesClick(stat._id);
                        }}
                        className="text-sm text-blue-600 hover:text-blue-800 underline"
                      >
                        {stat.indices.length} {stat.indices.length === 1 ? 'index' : 'indices'}
                      </button>
                      <span className="text-2xl font-bold text-blue-600">{formatNumber(stat.count)}</span>
                    </div>
                  </div>
                  
                  {/* Indices List */}
                  {showingIndices === stat._id && (
                    <div className="mt-4 pl-4 border-l-2 border-green-200">
                      {indicesLoading ? (
                        <div className="text-gray-500">Loading indices...</div>
                      ) : indicesError ? (
                        <div className="text-red-500">
                          Error loading indices: {indicesError instanceof Error ? indicesError.message : 'Unknown error'}
                        </div>
                      ) : industryIndices ? (
                        <div className="space-y-2">
                          <div className="text-sm text-gray-600 mb-3">
                            {stat._id} appears in {industryIndices.total_indices} {industryIndices.total_indices === 1 ? 'index' : 'indices'}
                          </div>
                          <div className="grid gap-2">
                            {industryIndices.indices.map((index, idx) => (
                              <div key={idx} className="bg-green-50 p-3 rounded border">
                                <div className="flex justify-between items-center">
                                  <button
                                    onClick={() => handleIndexClick(stat._id, index._id)}
                                    className="font-medium text-gray-900 hover:text-blue-600 transition-colors duration-200 focus:outline-none focus:text-blue-600"
                                  >
                                    {index._id}
                                  </button>
                                  <span className="text-sm text-gray-600">{index.count} companies</span>
                                </div>
                                
                                {/* Index Companies List */}
                                {selectedIndexInIndustry?.industry === stat._id && selectedIndexInIndustry?.index === index._id && (
                                  <div className="mt-3 pl-4 border-l-2 border-blue-200">
                                    {indexCompaniesLoading ? (
                                      <div className="text-gray-500 text-sm">Loading companies...</div>
                                    ) : indexCompaniesError ? (
                                      <div className="text-red-500 text-sm">
                                        Error loading companies: {indexCompaniesError instanceof Error ? indexCompaniesError.message : 'Unknown error'}
                                      </div>
                                    ) : industryIndexCompanies ? (
                                      <div className="space-y-2">
                                        <div className="text-xs text-gray-600 mb-2">
                                          {industryIndexCompanies.total_companies} companies in {stat._id} from {index._id}
                                        </div>
                                        <div className="max-h-64 overflow-y-auto space-y-1">
                                          {industryIndexCompanies.companies.map((company, companyIdx) => (
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
                  
                  {/* Companies List */}
                  {selectedIndustry === stat._id && (
                    <div className="mt-4 pl-4 border-l-2 border-blue-200">
                      {companiesLoading ? (
                        <div className="text-gray-500">Loading companies...</div>
                      ) : companiesError ? (
                        <div className="text-red-500">
                          Error loading companies: {companiesError instanceof Error ? companiesError.message : 'Unknown error'}
                        </div>
                      ) : industryCompanies ? (
                        <div className="space-y-3">
                          <div className="text-sm text-gray-600 mb-3">
                            Showing {industryCompanies.total_companies} unique companies in {stat._id}
                          </div>
                          <div className="max-h-96 overflow-y-auto space-y-2">
                            {industryCompanies.companies.map((company, idx) => (
                              <div key={idx} className="bg-gray-50 p-3 rounded border">
                                <div className="flex justify-between items-start">
                                  <div className="flex-1">
                                    <h4 className="font-medium text-gray-900">{company['Company Name']}</h4>
                                    <div className="text-sm text-gray-600 mt-1">
                                      <span className="inline-block mr-4">Symbol: {company.Symbol}</span>
                                      <span className="inline-block">Series: {company.Series}</span>
                                    </div>
                                    {company['ISIN Code'] && (
                                      <div className="text-xs text-gray-500 mt-1">
                                        ISIN: {company['ISIN Code']}
                                      </div>
                                    )}
                                    <div className="text-xs text-blue-600 mt-1">
                                      Present in: {company.indices.join(', ')}
                                    </div>
                                  </div>
                                </div>
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
