'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { 
  BarChart3,
  TrendingUp,
  Calendar,
  Play,
  Home,
  ArrowLeft,
  Settings,
  RefreshCw,
  Target,
  Activity,
  Layers
} from 'lucide-react';
import { api } from '@/lib/api';

// Types for our data structure
interface ScoreDistribution {
  date: string;
  ranges: {
    '0-20': number;
    '20-40': number;
    '40-60': number;
    '60-80': number;
    '80-100': number;
  };
  totalStocks: number;
  price?: {
    open?: number;
    high?: number;
    low?: number;
    close?: number;
    volume?: number;
  };
}

interface IndexData {
  name: string;
  code: string;
  totalStocks: number;
  lastUpdated: string;
}

const IndexDistributionPage = () => {
  const [selectedIndex, setSelectedIndex] = useState('NIFTY50');
  const [selectedTimeRange, setSelectedTimeRange] = useState('5Y');
  const [selectedMetric, setSelectedMetric] = useState('truevx_score');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [distributionData, setDistributionData] = useState<ScoreDistribution[]>([]);
  const [symbolBreakdownData, setSymbolBreakdownData] = useState<any[]>([]); // For detailed symbol breakdown - initialize as empty array
  const [baseSymbol, setBaseSymbol] = useState<string | null>(null); // Track the actual base symbol
  const [showSettings, setShowSettings] = useState(false);
  const [animationSpeed, setAnimationSpeed] = useState(100);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTimeIndex, setCurrentTimeIndex] = useState(0);
  const [availableIndices, setAvailableIndices] = useState<IndexData[]>([]);
  // New state for chart interactivity
  const [visibleRanges, setVisibleRanges] = useState<{[key: string]: boolean}>({
    '0-20': true,
    '20-40': true,
    '40-60': true,
    '60-80': true,
    '80-100': true,
  });
  const [hoveredRange, setHoveredRange] = useState<string | null>(null);
  const [chartDimensions] = useState({ width: 1200, height: 500 });
  const [showByCount, setShowByCount] = useState(false); // false = percentage, true = count
  const [selectedRatio] = useState('above60/below60'); // New state for ratio selection

  // Load available indices from the data overview endpoint
  useEffect(() => {
    const loadAvailableIndices = async () => {
      try {
        const dataOverview = await api.getDataOverview();
        
        // Transform index_stats to our format
        const indices: IndexData[] = dataOverview.index_stats.map((stat: any) => ({
          name: stat._id,
          code: stat._id.replace(/\s+/g, '').toUpperCase(),
          totalStocks: stat.count,
          lastUpdated: stat.last_update ? new Date(stat.last_update).toISOString().split('T')[0] : '2025-08-27'
        }));

        // Filter out non-main indices (keep major indices only)
        const mainIndices = indices.filter(index => 
          !index.name.includes('MARKET INDEXES') && 
          index.totalStocks > 10 // Only indices with reasonable stock count
        );

        setAvailableIndices(mainIndices);
        
        // Set default to first available index or keep NIFTY50 if available
        if (mainIndices.length > 0) {
          const nifty50 = mainIndices.find(index => index.code === 'NIFTY50');
          setSelectedIndex(nifty50 ? nifty50.name : mainIndices[0].name);
        }
      } catch (error) {
        console.error('Failed to load available indices:', error);
        // Fallback to default indices if API fails
        setAvailableIndices([
          { name: 'NIFTY50', code: 'NIFTY50', totalStocks: 50, lastUpdated: '2025-08-27' },
          { name: 'NIFTY100', code: 'NIFTY100', totalStocks: 100, lastUpdated: '2025-08-27' },
          { name: 'NIFTY 500', code: 'NIFTY500', totalStocks: 500, lastUpdated: '2025-08-27' },
        ]);
      }
    };

    loadAvailableIndices();
  }, []);

  const timeRanges = [
    { label: '5Y', value: '5Y', description: 'Last 5 Years' },
    { label: '10Y', value: '10Y', description: 'Last 10 Years' },
    { label: '15Y', value: '15Y', description: 'Last 15 Years' },
    { label: '20Y', value: '20Y', description: 'Last 20 Years' },
  ];

  const metricOptions = [
    { value: 'truevx_score', label: 'TrueVX Score', description: 'Main TrueValueX ranking score' },
    { value: 'mean_short', label: 'Short Mean', description: 'Short-term (22-period) moving average' },
    { value: 'mean_mid', label: 'Mid Mean', description: 'Mid-term (66-period) moving average' },
    { value: 'mean_long', label: 'Long Mean', description: 'Long-term (222-period) moving average' },
  ];

  const scoreRanges = [
    { range: '0-20', label: 'Weak (0-20)', color: 'bg-red-500', lightColor: 'bg-red-100', hexColor: '#ef4444' },
    { range: '20-40', label: 'Below Average (20-40)', color: 'bg-orange-500', lightColor: 'bg-orange-100', hexColor: '#f97316' },
    { range: '40-60', label: 'Average (40-60)', color: 'bg-yellow-500', lightColor: 'bg-yellow-100', hexColor: '#eab308' },
    { range: '60-80', label: 'Above Average (60-80)', color: 'bg-blue-500', lightColor: 'bg-blue-100', hexColor: '#3b82f6' },
    { range: '80-100', label: 'Strong (80-100)', color: 'bg-green-500', lightColor: 'bg-green-100', hexColor: '#22c55e' },
  ];

  // Helper function to get ratio options (bigger range / immediate lower range)
  const getRatioOptions = () => [
    { 
      value: 'above60/below60', 
      label: 'Above 60 / Below 60', 
      description: 'Stocks Above 60 (60-80 + 80-100) vs Below 60 (0-20 + 20-40 + 40-60)',
      numerator: 'Above 60',
      denominator: 'Below 60'
    }
  ];

  // Helper function to calculate ratio data with zero division protection
  const calculateRatioData = () => {
    return distributionData.map(data => {
      // Count above 60: 60-80 + 80-100
      const above60 = (data.ranges['60-80'] || 0) + (data.ranges['80-100'] || 0);
      
      // Count below 60: 0-20 + 20-40 + 40-60
      const below60 = (data.ranges['0-20'] || 0) + (data.ranges['20-40'] || 0) + (data.ranges['40-60'] || 0);
      
      // Handle division by zero - return very high value when denominator is 0 but numerator > 0
      let ratio = 0;
      if (below60 === 0) {
        ratio = above60 > 0 ? 999 : 0; // Use 999 instead of Infinity for better chart display
      } else {
        ratio = above60 / below60;
      }
      
      return {
        date: data.date,
        ratio,
        numerator: above60,
        denominator: below60
      };
    });
  };

  // Load data when parameters change
  useEffect(() => {
    const fetchDistributionData = async () => {
      setIsLoading(true);
      setError(null);
      
      try {
        // Calculate date range based on selected time range
        const endDate = new Date();
        const startDate = new Date();
        
        switch (selectedTimeRange) {
          case '5Y':
            startDate.setFullYear(endDate.getFullYear() - 5);
            break;
          case '10Y':
            startDate.setFullYear(endDate.getFullYear() - 10);
            break;
          case '15Y':
            startDate.setFullYear(endDate.getFullYear() - 15);
            break;
          case '20Y':
            startDate.setFullYear(endDate.getFullYear() - 20);
            break;
        }
        
        // Map display names to index symbols for API call
        const data = await api.getIndexDistribution({
          indexSymbol: selectedIndex, // Use the selectedIndex directly since it's already the correct name
          startDate: startDate.toISOString().split('T')[0],
          endDate: endDate.toISOString().split('T')[0],
          scoreRanges: '0-20,20-40,40-60,60-80,80-100',
          metric: selectedMetric,
          includePrice: true,  // Include base symbol price data
          includeSymbols: true  // Include detailed symbol breakdown
        });
        
        // Transform API data to match component structure
        const transformedData: ScoreDistribution[] = data.data.map((item: any) => ({
          date: item.date,
          ranges: {
            '0-20': item.distribution['0-20']?.count || 0,
            '20-40': item.distribution['20-40']?.count || 0,
            '40-60': item.distribution['40-60']?.count || 0,
            '60-80': item.distribution['60-80']?.count || 0,
            '80-100': item.distribution['80-100']?.count || 0,
          },
          totalStocks: item.total_symbols,
          price: item.price || undefined  // Include price data if available
        }));
        
        setDistributionData(transformedData);
        setBaseSymbol(data.base_symbol || null); // Set the actual base symbol used
        
        // Set symbol breakdown data with better validation
        if (data.data && Array.isArray(data.data)) {
          setSymbolBreakdownData(data.data);
          console.log('Setting symbolBreakdownData:', {
            dataType: typeof data.data,
            isArray: Array.isArray(data.data),
            length: data.data.length,
            firstItem: data.data[0]
          });
        } else {
          setSymbolBreakdownData([]);
          console.log('API data is not array, setting empty array:', data.data);
        }
        
        setCurrentTimeIndex(transformedData.length - 1);
        
        // Debug log to understand the data structure
        console.log('API Response:', {
          hasSymbols: data.include_symbols,
          dataLength: data.data?.length,
          firstDataPoint: data.data?.[0],
          sampleDistribution: data.data?.[0]?.distribution
        });
      } catch (err) {
        console.error('Failed to fetch index distribution data:', err);
        setError('Failed to load data. Please try again.');
      } finally {
        setIsLoading(false);
      }
    };

    fetchDistributionData();
  }, [selectedIndex, selectedTimeRange, selectedMetric]);

  // Animation controls
  useEffect(() => {
    if (isPlaying && distributionData.length > 0) {
      const interval = setInterval(() => {
        setCurrentTimeIndex(prev => {
          if (prev >= distributionData.length - 1) {
            setIsPlaying(false);
            return distributionData.length - 1;
          }
          return prev + 1;
        });
      }, animationSpeed);
      
      return () => clearInterval(interval);
    }
  }, [isPlaying, distributionData, animationSpeed]);

  const currentData = distributionData[currentTimeIndex] || null;

  // Helper functions for chart interactivity
  const toggleAllRanges = (visible: boolean) => {
    setVisibleRanges({
      '0-20': visible,
      '20-40': visible,
      '40-60': visible,
      '60-80': visible,
      '80-100': visible,
    });
  };

  const getVisibleRangesCount = () => {
    return Object.values(visibleRanges).filter(Boolean).length;
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Navigation */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Link href="/">
            <Button variant="outline" size="sm" className="flex items-center gap-2">
              <Home className="h-4 w-4" />
              Dashboard
            </Button>
          </Link>
          <Link href="/analytics">
            <Button variant="outline" size="sm" className="flex items-center gap-2">
              <ArrowLeft className="h-4 w-4" />
              Analytics
            </Button>
          </Link>
        </div>
        
        <Button
          variant="outline"
          size="sm"
          onClick={() => setShowSettings(!showSettings)}
          className="flex items-center gap-2"
        >
          <Settings className="h-4 w-4" />
          Settings
        </Button>
      </div>

      {/* Header */}
      <div className="text-center space-y-4">
        <div className="flex items-center justify-center gap-3">
          <BarChart3 className="h-8 w-8 text-purple-600" />
          <h1 className="text-3xl font-bold bg-gradient-to-r from-purple-600 to-blue-600 bg-clip-text text-transparent">
            Index Score Distribution Analysis
          </h1>
        </div>
        <p className="text-gray-600 max-w-3xl mx-auto">
          Interactive time-series visualization of TrueVX score distribution across index constituents. 
          Watch how market sentiment and performance evolve over time.
        </p>
      </div>

      {/* Controls Panel */}
      <Card className="bg-gradient-to-r from-blue-50 to-purple-50 border-blue-200">
        <CardContent className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {/* Index Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Select Index
              </label>
              <select 
                value={selectedIndex}
                onChange={(e) => setSelectedIndex(e.target.value)}
                className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              >
                {availableIndices.map((index) => (
                  <option key={index.code} value={index.name}>
                    {index.name} ({index.totalStocks} stocks)
                  </option>
                ))}
              </select>
            </div>

            {/* Metric Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Analysis Metric
              </label>
              <select 
                value={selectedMetric}
                onChange={(e) => setSelectedMetric(e.target.value)}
                className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              >
                {metricOptions.map((metric) => (
                  <option key={metric.value} value={metric.value} title={metric.description}>
                    {metric.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Time Range Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Time Range
              </label>
              <div className="flex gap-2">
                {timeRanges.map((range) => (
                  <Button
                    key={range.value}
                    variant={selectedTimeRange === range.value ? 'primary' : 'outline'}
                    size="sm"
                    onClick={() => setSelectedTimeRange(range.value)}
                    title={range.description}
                  >
                    {range.label}
                  </Button>
                ))}
              </div>
            </div>

            {/* Animation Controls */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Animation Controls
              </label>
              <div className="flex gap-2">
                <Button
                  variant={isPlaying ? 'primary' : 'outline'}
                  size="sm"
                  onClick={() => setIsPlaying(!isPlaying)}
                  disabled={isLoading || !distributionData.length}
                >
                  <Play className="h-4 w-4" />
                  {isPlaying ? 'Pause' : 'Play'}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setCurrentTimeIndex(0);
                    setIsPlaying(false);
                  }}
                  disabled={isLoading || !distributionData.length}
                >
                  Reset
                </Button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Settings Panel */}
      {showSettings && (
        <Card className="border-yellow-200 bg-yellow-50">
          <CardContent className="p-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Animation Speed (ms)
                </label>
                <Input
                  type="number"
                  min="50"
                  max="1000"
                  step="50"
                  value={animationSpeed}
                  onChange={(e) => setAnimationSpeed(Number(e.target.value))}
                  className="w-full"
                />
              </div>
              <div className="flex items-end">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowSettings(false)}
                >
                  Close Settings
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Current Date Display */}
      {currentData && (
        <Card className="bg-gradient-to-r from-green-50 to-blue-50 border-green-200">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Calendar className="h-5 w-5 text-green-600" />
                <span className="text-lg font-semibold text-green-800">
                  {new Date(currentData.date).toLocaleDateString('en-US', { 
                    year: 'numeric', 
                    month: 'long', 
                    day: 'numeric' 
                  })}
                </span>
              </div>
              <div className="text-sm text-gray-600">
                Day {currentTimeIndex + 1} of {distributionData.length}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Main Visualization Area */}
      <div className="space-y-6">
        {/* Distribution Chart and Summary in side-by-side layout */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Distribution Chart */}
          <Card className="h-96">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5" />
                Score Distribution
              </CardTitle>
            </CardHeader>
            <CardContent>
            {isLoading ? (
              <div className="flex items-center justify-center h-64">
                <RefreshCw className="h-8 w-8 animate-spin text-purple-600" />
                <span className="ml-2 text-gray-600">Loading distribution data...</span>
              </div>
            ) : error ? (
              <div className="flex flex-col items-center justify-center h-64 text-red-500">
                <div className="text-center">
                  <p className="text-lg font-medium">Failed to load data</p>
                  <p className="text-sm text-gray-600 mt-2">{error}</p>
                  <Button 
                    variant="outline" 
                    size="sm" 
                    onClick={() => window.location.reload()} 
                    className="mt-4"
                  >
                    Retry
                  </Button>
                </div>
              </div>
            ) : currentData ? (
              <div className="space-y-4">
                {scoreRanges.map((scoreRange) => {
                  const count = currentData.ranges[scoreRange.range as keyof typeof currentData.ranges];
                  const percentage = (count / currentData.totalStocks) * 100;
                  
                  return (
                    <div key={scoreRange.range} className="space-y-2">
                      <div className="flex justify-between items-center">
                        <span className="text-sm font-medium text-gray-700">
                          {scoreRange.label}
                        </span>
                        <span className="text-sm text-gray-600">
                          {count} stocks ({percentage.toFixed(1)}%)
                        </span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-4">
                        <div
                          className={`h-4 rounded-full transition-all duration-500 ${scoreRange.color}`}
                          style={{ width: `${percentage}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="flex items-center justify-center h-64 text-gray-500">
                No data available
              </div>
            )}
          </CardContent>
        </Card>

        {/* Summary Statistics */}
        <Card className="h-96">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Target className="h-5 w-5" />
              Market Summary
            </CardTitle>
          </CardHeader>
          <CardContent>
            {currentData ? (
              <div className="space-y-6">
                {/* Overall Statistics */}
                <div className="grid grid-cols-2 gap-4">
                  <div className={`p-4 rounded-lg ${scoreRanges[4].lightColor}`}>
                    <div className="text-2xl font-bold text-green-700">
                      {currentData.ranges['80-100']}
                    </div>
                    <div className="text-sm text-green-600">Strong Performers</div>
                  </div>
                  <div className={`p-4 rounded-lg ${scoreRanges[0].lightColor}`}>
                    <div className="text-2xl font-bold text-red-700">
                      {currentData.ranges['0-20']}
                    </div>
                    <div className="text-sm text-red-600">Weak Performers</div>
                  </div>
                </div>

                {/* Market Health Indicator */}
                <div>
                  <h4 className="font-medium text-gray-900 mb-2">Market Health</h4>
                  <div className="space-y-2">
                    {(() => {
                      const strongPercentage = (currentData.ranges['80-100'] / currentData.totalStocks) * 100;
                      const weakPercentage = (currentData.ranges['0-20'] / currentData.totalStocks) * 100;
                      const healthScore = strongPercentage - weakPercentage;
                      
                      let healthColor = 'text-gray-600';
                      let healthLabel = 'Neutral';
                      
                      if (healthScore > 10) {
                        healthColor = 'text-green-600';
                        healthLabel = 'Healthy';
                      } else if (healthScore < -10) {
                        healthColor = 'text-red-600';
                        healthLabel = 'Weak';
                      }
                      
                      return (
                        <>
                          <div className={`text-lg font-semibold ${healthColor}`}>
                            {healthLabel} ({healthScore > 0 ? '+' : ''}{healthScore.toFixed(1)}%)
                          </div>
                          <div className="w-full bg-gray-200 rounded-full h-2">
                            <div
                              className={`h-2 rounded-full transition-all duration-500 ${
                                healthScore > 10 ? 'bg-green-500' : 
                                healthScore < -10 ? 'bg-red-500' : 'bg-yellow-500'
                              }`}
                              style={{ width: `${Math.min(100, Math.abs(healthScore) * 2)}%` }}
                            />
                          </div>
                        </>
                      );
                    })()}
                  </div>
                </div>

                {/* Index Information */}
                <div className="p-4 bg-blue-50 rounded-lg">
                  <h4 className="font-medium text-blue-900 mb-2">Index Details</h4>
                  <div className="space-y-1 text-sm text-blue-700">
                    <div>Index: {selectedIndex}</div>
                    <div>Total Stocks: {currentData.totalStocks}</div>
                    <div>Time Range: {selectedTimeRange}</div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-center h-64 text-gray-500">
                Select parameters to view summary
              </div>
            )}
          </CardContent>
        </Card>
        </div> {/* End of side-by-side layout */}
      </div> {/* End of main visualization area */}

      {/* Time Slider */}
      {distributionData.length > 0 && (
        <Card>
          <CardContent className="p-6">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold">Time Navigation</h3>
                <div className="text-sm text-gray-600">
                  {distributionData.length.toLocaleString()} data points
                </div>
              </div>
              <div className="space-y-2">
                <input
                  type="range"
                  min="0"
                  max={distributionData.length - 1}
                  value={currentTimeIndex}
                  onChange={(e) => {
                    setCurrentTimeIndex(Number(e.target.value));
                    setIsPlaying(false);
                  }}
                  className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer slider"
                />
                <div className="flex justify-between text-xs text-gray-500">
                  <span>{distributionData[0]?.date}</span>
                  <span>{distributionData[distributionData.length - 1]?.date}</span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Area Chart - Time Series Distribution */}
      {distributionData.length > 0 && (
        <Card className="col-span-full">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <Activity className="h-5 w-5" />
                Distribution Trends Over Time ({metricOptions.find(m => m.value === selectedMetric)?.label})
              </CardTitle>
              <div className="flex items-center gap-4">
                {/* Display Mode Toggle */}
                <div className="flex items-center gap-2 px-3 py-1 bg-gray-50 rounded-lg">
                  <span className="text-sm text-gray-600">Display:</span>
                  <div className="flex bg-white rounded-md p-1 shadow-sm">
                    <button
                      onClick={() => setShowByCount(false)}
                      className={`px-3 py-1 text-xs font-medium rounded transition-all ${
                        !showByCount 
                          ? 'bg-blue-500 text-white shadow-sm' 
                          : 'text-gray-600 hover:bg-gray-50'
                      }`}
                    >
                      Percentage
                    </button>
                    <button
                      onClick={() => setShowByCount(true)}
                      className={`px-3 py-1 text-xs font-medium rounded transition-all ${
                        showByCount 
                          ? 'bg-blue-500 text-white shadow-sm' 
                          : 'text-gray-600 hover:bg-gray-50'
                      }`}
                    >
                      Count
                    </button>
                  </div>
                </div>
                
                <span className="text-sm text-gray-600">Toggle Ranges:</span>
                <div className="flex gap-1">
                  <button
                    onClick={() => toggleAllRanges(true)}
                    className="px-2 py-1 text-xs text-blue-600 hover:bg-blue-50 rounded transition-colors"
                  >
                    All
                  </button>
                  <button
                    onClick={() => toggleAllRanges(false)}
                    className="px-2 py-1 text-xs text-gray-600 hover:bg-gray-50 rounded transition-colors"
                  >
                    None
                  </button>
                </div>
                <div className="flex gap-2">
                  {scoreRanges.map((scoreRange) => (
                    <button
                      key={scoreRange.range}
                      onClick={() => setVisibleRanges(prev => ({
                        ...prev,
                        [scoreRange.range]: !prev[scoreRange.range]
                      }))}
                      onMouseEnter={() => setHoveredRange(scoreRange.range)}
                      onMouseLeave={() => setHoveredRange(null)}
                      className={`px-2 py-1 rounded text-xs font-medium transition-all ${
                        visibleRanges[scoreRange.range] 
                          ? 'bg-white border-2 text-gray-700 shadow-sm' 
                          : 'bg-gray-200 text-gray-400 border-2 border-gray-300'
                      }`}
                      style={{
                        borderColor: visibleRanges[scoreRange.range] ? scoreRange.hexColor : undefined,
                        backgroundColor: visibleRanges[scoreRange.range] ? `${scoreRange.hexColor}20` : undefined
                      }}
                    >
                      {scoreRange.range}
                    </button>
                  ))}
                </div>
                <span className="text-xs text-gray-500">
                  ({getVisibleRangesCount()}/5 visible)
                </span>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="h-[600px] w-full overflow-hidden">
              <svg 
                viewBox={`0 0 ${chartDimensions.width} ${chartDimensions.height}`} 
                className="w-full h-full cursor-crosshair"
                onMouseMove={(e) => {
                  const rect = e.currentTarget.getBoundingClientRect();
                  const x = ((e.clientX - rect.left) / rect.width) * chartDimensions.width;
                  if (x >= 80 && x <= chartDimensions.width - 50) {
                    const dataIndex = Math.round(((x - 80) / (chartDimensions.width - 130)) * (distributionData.length - 1));
                    if (dataIndex !== currentTimeIndex && dataIndex >= 0 && dataIndex < distributionData.length) {
                      setCurrentTimeIndex(dataIndex);
                      setIsPlaying(false);
                    }
                  }
                }}
              >
                {/* Chart background */}
                <rect 
                  width={chartDimensions.width} 
                  height={chartDimensions.height} 
                  fill="#f8fafc" 
                  stroke="#e2e8f0" 
                  strokeWidth="1" 
                />
                
                {/* Grid lines - Y axis */}
                {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map(i => {
                  // Calculate max value for count mode
                  const maxCount = Math.max(...distributionData.map(data => data.totalStocks));
                  const maxValue = showByCount ? maxCount : 100;
                  const stepValue = showByCount ? Math.ceil(maxCount / 10) : 10;
                  const currentValue = showByCount ? 
                    Math.round((maxCount - (i * maxCount / 10))) : 
                    (100 - i * 10);
                  
                  return (
                    <g key={`grid-y-${i}`}>
                      <line 
                        x1="80" 
                        y1={60 + i * (chartDimensions.height - 120) / 10} 
                        x2={chartDimensions.width - 50} 
                        y2={60 + i * (chartDimensions.height - 120) / 10} 
                        stroke="#e2e8f0" 
                        strokeWidth="1" 
                      />
                      <text 
                        x="75" 
                        y={65 + i * (chartDimensions.height - 120) / 10} 
                        fontSize="12" 
                        fill="#64748b" 
                        textAnchor="end"
                      >
                        {showByCount ? currentValue : `${currentValue}%`}
                      </text>
                    </g>
                  );
                })}
                
                {/* Grid lines - X axis */}
                {distributionData.map((_, index) => {
                  if (index % Math.ceil(distributionData.length / 12) === 0) {
                    const x = 80 + (index / (distributionData.length - 1)) * (chartDimensions.width - 130);
                    return (
                      <g key={`grid-x-${index}`}>
                        <line 
                          x1={x} 
                          y1="60" 
                          x2={x} 
                          y2={chartDimensions.height - 60} 
                          stroke="#e2e8f0" 
                          strokeWidth="1" 
                        />
                        <text 
                          x={x} 
                          y={chartDimensions.height - 40} 
                          fontSize="11" 
                          fill="#64748b" 
                          textAnchor="middle"
                        >
                          {new Date(distributionData[index].date).toLocaleDateString('en-US', { 
                            month: 'short', 
                            day: 'numeric',
                            year: distributionData.length > 365 ? '2-digit' : undefined
                          })}
                        </text>
                      </g>
                    );
                  }
                  return null;
                })}
                
                {/* Area charts for each score range - stacked */}
                {scoreRanges.map((scoreRange, rangeIndex) => {
                  if (!visibleRanges[scoreRange.range]) return null;
                  
                  // Calculate max value for scaling
                  const maxCount = Math.max(...distributionData.map(data => data.totalStocks));
                  const maxValue = showByCount ? maxCount : 100;
                  
                  // Calculate cumulative values for stacking
                  const stackedPoints = distributionData.map((data, index) => {
                    const x = 80 + (index / (distributionData.length - 1)) * (chartDimensions.width - 130);
                    
                    // Calculate cumulative value up to this range
                    let cumulativeValue = 0;
                    for (let i = 0; i <= rangeIndex; i++) {
                      const range = scoreRanges[i];
                      if (visibleRanges[range.range]) {
                        const count = data.ranges[range.range as keyof typeof data.ranges];
                        const value = showByCount ? count : (count / data.totalStocks) * 100;
                        cumulativeValue += value;
                      }
                    }
                    
                    const y = chartDimensions.height - 60 - (cumulativeValue / maxValue) * (chartDimensions.height - 120);
                    return `${x},${y}`;
                  }).join(' ');
                  
                  // Calculate base line for this layer
                  const basePoints = distributionData.map((data, index) => {
                    const x = 80 + (index / (distributionData.length - 1)) * (chartDimensions.width - 130);
                    
                    // Calculate cumulative value up to previous range
                    let cumulativeValue = 0;
                    for (let i = 0; i < rangeIndex; i++) {
                      const range = scoreRanges[i];
                      if (visibleRanges[range.range]) {
                        const count = data.ranges[range.range as keyof typeof data.ranges];
                        const value = showByCount ? count : (count / data.totalStocks) * 100;
                        cumulativeValue += value;
                      }
                    }
                    
                    const y = chartDimensions.height - 60 - (cumulativeValue / maxValue) * (chartDimensions.height - 120);
                    return `${x},${y}`;
                  }).reverse().join(' ');
                  
                  const pathData = `M ${stackedPoints} L ${basePoints} Z`;
                  
                  return (
                    <g key={scoreRange.range}>
                      <path
                        d={pathData}
                        fill={scoreRange.hexColor}
                        fillOpacity={hoveredRange === scoreRange.range ? "0.8" : "0.7"}
                        stroke={scoreRange.hexColor}
                        strokeWidth={hoveredRange === scoreRange.range ? "3" : "1"}
                        onMouseEnter={() => setHoveredRange(scoreRange.range)}
                        onMouseLeave={() => setHoveredRange(null)}
                        className="transition-all duration-200"
                      />
                    </g>
                  );
                })}
                
                {/* Current time indicator */}
                {currentData && (
                  <g>
                    <line
                      x1={80 + (currentTimeIndex / (distributionData.length - 1)) * (chartDimensions.width - 130)}
                      y1="60"
                      x2={80 + (currentTimeIndex / (distributionData.length - 1)) * (chartDimensions.width - 130)}
                      y2={chartDimensions.height - 60}
                      stroke="#7c3aed"
                      strokeWidth="3"
                      strokeDasharray="8,4"
                    />
                    {/* Current time tooltip */}
                    <g transform={`translate(${80 + (currentTimeIndex / (distributionData.length - 1)) * (chartDimensions.width - 130)}, 30)`}>
                      <rect
                        x="-50"
                        y="-15"
                        width="100"
                        height="30"
                        fill="#7c3aed"
                        rx="4"
                        fillOpacity="0.9"
                      />
                      <text
                        x="0"
                        y="2"
                        fontSize="12"
                        fill="white"
                        textAnchor="middle"
                        fontWeight="bold"
                      >
                        {new Date(currentData.date).toLocaleDateString('en-US', { 
                          month: 'short', 
                          day: 'numeric',
                          year: '2-digit'
                        })}
                      </text>
                    </g>
                  </g>
                )}
                
                {/* Interactive hover circles for data points */}
                {hoveredRange && distributionData.map((data, index) => {
                  const x = 80 + (index / (distributionData.length - 1)) * (chartDimensions.width - 130);
                  const count = data.ranges[hoveredRange as keyof typeof data.ranges];
                  const maxCount = Math.max(...distributionData.map(d => d.totalStocks));
                  const maxValue = showByCount ? maxCount : 100;
                  const value = showByCount ? count : (count / data.totalStocks) * 100;
                  const y = chartDimensions.height - 60 - (value / maxValue) * (chartDimensions.height - 120);
                  
                  return (
                    <circle
                      key={`hover-${index}`}
                      cx={x}
                      cy={y}
                      r="3"
                      fill={scoreRanges.find(r => r.range === hoveredRange)?.hexColor}
                      stroke="white"
                      strokeWidth="2"
                      className="animate-pulse"
                    />
                  );
                })}
                
                {/* Base Symbol Price Line */}
                {baseSymbol && (() => {
                  // Filter data points that have price data
                  const priceDataPoints = distributionData.filter(d => d.price?.close);
                  
                  if (priceDataPoints.length > 0) {
                    // Calculate price scale
                    const priceValues = priceDataPoints.map(d => d.price!.close!);
                    const minPrice = Math.min(...priceValues);
                    const maxPrice = Math.max(...priceValues);
                    const priceRange = maxPrice - minPrice;
                    
                    // Create price line path
                    const pricePath = priceDataPoints.map((dataPoint, index) => {
                      const dataIndex = distributionData.findIndex(d => d.date === dataPoint.date);
                      const x = 80 + (dataIndex / (distributionData.length - 1)) * (chartDimensions.width - 130);
                      // Scale price to chart height (invert Y axis for SVG)
                      const normalizedPrice = (dataPoint.price!.close! - minPrice) / priceRange;
                      const y = chartDimensions.height - 100 - (normalizedPrice * (chartDimensions.height - 200));
                      return `${index === 0 ? 'M' : 'L'} ${x} ${y}`;
                    }).join(' ');
                    
                    return (
                      <g key="price-line">
                        {/* Price line */}
                        <path
                          d={pricePath}
                          fill="none"
                          stroke="#ef4444"
                          strokeWidth="2"
                          opacity="0.8"
                        />
                        
                        {/* Price scale labels on right Y-axis */}
                        {[0, 0.25, 0.5, 0.75, 1].map(ratio => {
                          const price = minPrice + (ratio * priceRange);
                          const y = chartDimensions.height - 100 - (ratio * (chartDimensions.height - 200));
                          return (
                            <g key={ratio}>
                              <line
                                x1={chartDimensions.width - 50}
                                y1={y}
                                x2={chartDimensions.width - 45}
                                y2={y}
                                stroke="#ef4444"
                                strokeWidth="1"
                                opacity="0.6"
                              />
                              <text
                                x={chartDimensions.width - 40}
                                y={y + 4}
                                fontSize="10"
                                fill="#ef4444"
                                textAnchor="start"
                              >
                                {price.toFixed(0)}
                              </text>
                            </g>
                          );
                        })}
                        
                        {/* Right Y-axis label for price */}
                        <text 
                          x={chartDimensions.width - 15} 
                          y={chartDimensions.height / 2} 
                          fontSize="12" 
                          fill="#ef4444" 
                          textAnchor="middle" 
                          transform={`rotate(90, ${chartDimensions.width - 15}, ${chartDimensions.height / 2})`}
                        >
                          {baseSymbol} Price
                        </text>
                        
                        {/* Price data points */}
                        {priceDataPoints.map((dataPoint, index) => {
                          const dataIndex = distributionData.findIndex(d => d.date === dataPoint.date);
                          const x = 80 + (dataIndex / (distributionData.length - 1)) * (chartDimensions.width - 130);
                          const normalizedPrice = (dataPoint.price!.close! - minPrice) / priceRange;
                          const y = chartDimensions.height - 100 - (normalizedPrice * (chartDimensions.height - 200));
                          return (
                            <circle
                              key={index}
                              cx={x}
                              cy={y}
                              r="2"
                              fill="#ef4444"
                              opacity="0.7"
                            />
                          );
                        })}
                      </g>
                    );
                  }
                  return null;
                })()}
                
                {/* Chart title and axes labels */}
                <text 
                  x={chartDimensions.width / 2} 
                  y="30" 
                  fontSize="16" 
                  fill="#374151" 
                  textAnchor="middle" 
                  fontWeight="bold"
                >
                  {metricOptions.find(m => m.value === selectedMetric)?.label} Distribution Over Time
                </text>
                
                {/* Y-axis label */}
                <text 
                  x="25" 
                  y={chartDimensions.height / 2} 
                  fontSize="14" 
                  fill="#64748b" 
                  textAnchor="middle" 
                  transform={`rotate(-90, 25, ${chartDimensions.height / 2})`}
                >
                  {showByCount ? 'Number of Stocks' : 'Percentage of Stocks (%)'}
                </text>
                
                {/* X-axis label */}
                <text 
                  x={chartDimensions.width / 2} 
                  y={chartDimensions.height - 10} 
                  fontSize="14" 
                  fill="#64748b" 
                  textAnchor="middle"
                >
                  Time Period
                </text>
              </svg>
            </div>
            
            {/* Ratio Analysis Controls */}
            <div className="mt-4 space-y-3">
              <div className="p-4 bg-gradient-to-r from-purple-50 to-blue-50 rounded-lg border border-purple-200">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-semibold text-purple-800">Range Ratio Analysis</h3>
                </div>
                <p className="text-sm text-purple-700">
                  <strong>{getRatioOptions().find(r => r.value === selectedRatio)?.description}:</strong>{' '}
                  Track the relationship between different score ranges over time. 
                  Higher ratios indicate stronger relative performance of the upper range.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Ratio Chart */}
      <Card className="bg-gradient-to-r from-indigo-50 to-purple-50 border-indigo-200">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5" />
            Range Ratio Trends
            <Badge variant="outline" className="ml-2">
              {getRatioOptions().find(r => r.value === selectedRatio)?.label}
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[600px] w-full">
            <svg 
              viewBox={`0 0 ${chartDimensions.width} ${chartDimensions.height}`} 
              className="w-full h-full"
            >
              {/* Chart background */}
              <rect 
                width={chartDimensions.width} 
                height={chartDimensions.height} 
                fill="#f8fafc" 
                stroke="#e2e8f0" 
                strokeWidth="1" 
              />
              
              {/* Grid lines - Y axis */}
              {[0, 1, 2, 3, 4, 5].map(i => {
                const maxRatio = Math.max(...calculateRatioData().map(d => d.ratio), 5);
                const currentValue = maxRatio - (i * maxRatio / 5);
                
                return (
                  <g key={`ratio-grid-y-${i}`}>
                    <line 
                      x1="80" 
                      y1={60 + i * ((chartDimensions.height - 120) / 5)} 
                      x2={chartDimensions.width - 50} 
                      y2={60 + i * ((chartDimensions.height - 120) / 5)} 
                      stroke="#e2e8f0" 
                      strokeWidth="1" 
                    />
                    <text 
                      x="75" 
                      y={65 + i * ((chartDimensions.height - 120) / 5)} 
                      fontSize="12" 
                      fill="#64748b" 
                      textAnchor="end"
                    >
                      {currentValue.toFixed(2)}
                    </text>
                  </g>
                );
              })}
              
              {/* Grid lines - X axis */}
              {distributionData.map((_, index) => {
                if (index % Math.ceil(distributionData.length / 12) === 0) {
                  const x = 80 + (index / (distributionData.length - 1)) * (chartDimensions.width - 130);
                  return (
                    <g key={`ratio-grid-x-${index}`}>
                      <line 
                        x1={x} 
                        y1="60" 
                        x2={x} 
                        y2={chartDimensions.height - 60} 
                        stroke="#e2e8f0" 
                        strokeWidth="1" 
                        strokeDasharray="3,3" 
                      />
                      <text 
                        x={x} 
                        y={chartDimensions.height - 45} 
                        fontSize="11" 
                        fill="#64748b" 
                        textAnchor="middle"
                      >
                        {new Date(distributionData[index].date).toLocaleDateString('en-US', { 
                          month: 'short', 
                          year: '2-digit' 
                        })}
                      </text>
                    </g>
                  );
                }
                return null;
              })}
              
              {/* Base Symbol Price Line (if available) */}
              {distributionData.length > 0 && distributionData.some(d => d.price?.close) && (
                (() => {
                  // Filter data points that have price data
                  const priceDataPoints = distributionData.filter(d => d.price?.close);
                  
                  if (priceDataPoints.length > 0) {
                    // Calculate price scale
                    const priceValues = priceDataPoints.map(d => d.price!.close!);
                    const minPrice = Math.min(...priceValues);
                    const maxPrice = Math.max(...priceValues);
                    const priceRange = maxPrice - minPrice;
                    
                    if (priceRange > 0) {
                      // Create price line path
                      const pricePath = distributionData.map((dataPoint, index) => {
                        if (dataPoint.price?.close) {
                          const x = 80 + (index / (distributionData.length - 1)) * (chartDimensions.width - 130);
                          // Scale price to chart height (invert Y axis for SVG)
                          const normalizedPrice = (dataPoint.price.close - minPrice) / priceRange;
                          const y = 60 + ((1 - normalizedPrice) * (chartDimensions.height - 120));
                          return `${index === 0 ? 'M' : 'L'} ${x} ${y}`;
                        }
                        return null;
                      }).filter(Boolean).join(' ');
                      
                      return (
                        <g key="price-line">
                          {/* Price line */}
                          <path
                            d={pricePath}
                            fill="none"
                            stroke="#dc2626"
                            strokeWidth="2"
                            opacity="0.7"
                          />
                          
                          {/* Price scale labels on right Y-axis */}
                          {[0, 1, 2, 3, 4, 5].map(i => {
                            const currentPrice = maxPrice - (i * priceRange / 5);
                            const y = 60 + (i * ((chartDimensions.height - 120) / 5));
                            return (
                              <g key={`price-y-${i}`}>
                                <line
                                  x1={chartDimensions.width - 50}
                                  y1={y}
                                  x2={chartDimensions.width - 45}
                                  y2={y}
                                  stroke="#dc2626"
                                  strokeWidth="1"
                                  opacity="0.6"
                                />
                                <text
                                  x={chartDimensions.width - 40}
                                  y={y + 4}
                                  fontSize="10"
                                  fill="#dc2626"
                                  textAnchor="start"
                                >
                                  ₹{currentPrice.toFixed(0)}
                                </text>
                              </g>
                            );
                          })}
                          
                          {/* Right Y-axis label for price */}
                          <text
                            x={chartDimensions.width - 20}
                            y="30"
                            fontSize="12"
                            fill="#dc2626"
                            textAnchor="middle"
                            fontWeight="bold"
                          >
                            Price
                          </text>
                        </g>
                      );
                    }
                  }
                  return null;
                })()
              )}

              {/* Ratio Line */}
              {(() => {
                const ratioData = calculateRatioData();
                const maxRatio = Math.max(...ratioData.map(d => d.ratio), 5);
                
                if (ratioData.length > 1) {
                  const path = ratioData.map((data, index) => {
                    const x = 80 + (index / (ratioData.length - 1)) * (chartDimensions.width - 130);
                    const y = (chartDimensions.height - 60) - ((data.ratio / maxRatio) * (chartDimensions.height - 120));
                    return `${index === 0 ? 'M' : 'L'} ${x} ${y}`;
                  }).join(' ');
                  
                  return (
                    <g>
                      {/* Ratio line */}
                      <path
                        d={path}
                        fill="none"
                        stroke="#8b5cf6"
                        strokeWidth="3"
                        opacity="0.8"
                      />
                      
                      {/* Data points */}
                      {ratioData.map((data, index) => {
                        const x = 80 + (index / (ratioData.length - 1)) * (chartDimensions.width - 130);
                        const y = (chartDimensions.height - 60) - ((data.ratio / maxRatio) * (chartDimensions.height - 120));
                        
                        return (
                          <circle
                            key={index}
                            cx={x}
                            cy={y}
                            r="4"
                            fill="#8b5cf6"
                            stroke="white"
                            strokeWidth="2"
                            className="hover:r-6 transition-all cursor-pointer"
                          />
                        );
                      })}
                      
                      {/* Reference line at ratio = 1 */}
                      <line
                        x1="80"
                        y1={(chartDimensions.height - 60) - ((1 / maxRatio) * (chartDimensions.height - 120))}
                        x2={chartDimensions.width - 50}
                        y2={(chartDimensions.height - 60) - ((1 / maxRatio) * (chartDimensions.height - 120))}
                        stroke="#ef4444"
                        strokeWidth="2"
                        strokeDasharray="5,5"
                        opacity="0.7"
                      />
                      <text
                        x={chartDimensions.width - 45}
                        y={(chartDimensions.height - 55) - ((1 / maxRatio) * (chartDimensions.height - 120))}
                        fontSize="12"
                        fill="#ef4444"
                        fontWeight="bold"
                      >
                        1.0
                      </text>
                    </g>
                  );
                }
                
                return null;
              })()}
              
              {/* Current position indicator */}
              {(() => {
                const ratioData = calculateRatioData();
                const maxRatio = Math.max(...ratioData.map(d => d.ratio), 5);
                
                if (currentTimeIndex < ratioData.length) {
                  const x = 80 + (currentTimeIndex / (ratioData.length - 1)) * (chartDimensions.width - 130);
                  const currentRatio = ratioData[currentTimeIndex]?.ratio || 0;
                  const y = (chartDimensions.height - 60) - ((currentRatio / maxRatio) * (chartDimensions.height - 120));
                  
                  return (
                    <g>
                      {/* Vertical indicator line */}
                      <line
                        x1={x}
                        y1="60"
                        x2={x}
                        y2={chartDimensions.height - 60}
                        stroke="#7c3aed"
                        strokeWidth="2"
                        opacity="0.6"
                        strokeDasharray="3,3"
                      />
                      
                      {/* Current value indicator */}
                      <circle
                        cx={x}
                        cy={y}
                        r="6"
                        fill="#7c3aed"
                        stroke="white"
                        strokeWidth="3"
                        className="animate-pulse"
                      />
                      
                      {/* Value tooltip */}
                      <g transform={`translate(${x}, ${y - 25})`}>
                        <rect
                          x="-25"
                          y="-15"
                          width="50"
                          height="20"
                          fill="#7c3aed"
                          rx="4"
                          fillOpacity="0.9"
                        />
                        <text
                          x="0"
                          y="-2"
                          fontSize="12"
                          fill="white"
                          textAnchor="middle"
                          fontWeight="bold"
                        >
                          {currentRatio.toFixed(2)}
                        </text>
                      </g>
                    </g>
                  );
                }
                
                return null;
              })()}
              
              {/* Chart title and axes labels */}
              <text 
                x={chartDimensions.width / 2} 
                y="30" 
                fontSize="16" 
                fill="#374151" 
                textAnchor="middle" 
                fontWeight="bold"
              >
                Range Ratio Trends Over Time
              </text>
              
              {/* Y-axis label for ratio (left side) */}
              <text 
                x="25" 
                y={chartDimensions.height / 2} 
                fontSize="14" 
                fill="#8b5cf6" 
                textAnchor="middle" 
                transform={`rotate(-90, 25, ${chartDimensions.height / 2})`}
              >
                Ratio Value
              </text>
              
              {/* X-axis label */}
              <text 
                x={chartDimensions.width / 2} 
                y={chartDimensions.height - 10} 
                fontSize="14" 
                fill="#64748b" 
                textAnchor="middle"
              >
                Time Period
              </text>
            </svg>
          </div>
          
          {/* Ratio Summary */}
          <div className="mt-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {(() => {
              const ratioData = calculateRatioData();
              const currentRatio = ratioData[currentTimeIndex] || { ratio: 0, numerator: 0, denominator: 0 };
              const option = getRatioOptions().find(r => r.value === selectedRatio);
              
              return (
                <div className="p-3 bg-white rounded-lg border">
                  <div className="text-xs text-gray-600 mb-1">Current Ratio</div>
                  <div className="text-2xl font-bold text-purple-700">
                    {currentRatio.ratio === Infinity ? '∞' : currentRatio.ratio.toFixed(2)}
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    {option?.numerator}: {currentRatio.numerator} / {option?.denominator}: {currentRatio.denominator}
                  </div>
                </div>
              );
            })()}
            
            {(() => {
              const ratioData = calculateRatioData();
              const maxRatio = Math.max(...ratioData.map(d => d.ratio === Infinity ? 0 : d.ratio));
              
              return (
                <div className="p-3 bg-white rounded-lg border">
                  <div className="text-xs text-gray-600 mb-1">Maximum Ratio</div>
                  <div className="text-2xl font-bold text-green-600">
                    {maxRatio.toFixed(2)}
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    Peak performance
                  </div>
                </div>
              );
            })()}
            
            {(() => {
              const ratioData = calculateRatioData();
              const validRatios = ratioData.filter(d => d.ratio !== Infinity).map(d => d.ratio);
              const avgRatio = validRatios.length > 0 ? validRatios.reduce((a, b) => a + b, 0) / validRatios.length : 0;
              
              return (
                <div className="p-3 bg-white rounded-lg border">
                  <div className="text-xs text-gray-600 mb-1">Average Ratio</div>
                  <div className="text-2xl font-bold text-blue-600">
                    {avgRatio.toFixed(2)}
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    Historical mean
                  </div>
                </div>
              );
            })()}
            
            {(() => {
              const ratioData = calculateRatioData();
              const validRatios = ratioData.filter(d => d.ratio !== Infinity).map(d => d.ratio);
              const currentRatio = ratioData[currentTimeIndex]?.ratio || 0;
              const percentile = validRatios.length > 0 
                ? (validRatios.filter(r => r <= currentRatio).length / validRatios.length) * 100 
                : 0;
              
              return (
                <div className="p-3 bg-white rounded-lg border">
                  <div className="text-xs text-gray-600 mb-1">Current Percentile</div>
                  <div className="text-2xl font-bold text-orange-600">
                    {percentile.toFixed(0)}%
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    Historical ranking
                  </div>
                </div>
              );
            })()}
          </div>
        </CardContent>
      </Card>

      {/* Symbol Breakdown Section */}
      {symbolBreakdownData && Array.isArray(symbolBreakdownData) && symbolBreakdownData.length > 0 && distributionData.length > 0 && currentTimeIndex >= 0 && currentTimeIndex < symbolBreakdownData.length && (
        <Card className="col-span-full">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Layers className="h-5 w-5" />
              Symbol Breakdown by Score Range
              <Badge variant="outline" className="ml-2">
                {symbolBreakdownData[currentTimeIndex]?.date || distributionData[currentTimeIndex]?.date || 'No Date'}
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
              {Object.entries(symbolBreakdownData?.[currentTimeIndex]?.distribution || {}).map(([range, rangeData]: [string, any]) => {
                const symbolList = Array.isArray(rangeData?.symbols) ? rangeData.symbols : [];
                const count = symbolList.length;
                
                // Get color for range
                const getRangeColor = (range: string) => {
                  switch(range) {
                    case '0-20': return 'bg-red-50 border-red-200';
                    case '20-40': return 'bg-orange-50 border-orange-200';
                    case '40-60': return 'bg-yellow-50 border-yellow-200';
                    case '60-80': return 'bg-blue-50 border-blue-200';
                    case '80-100': return 'bg-green-50 border-green-200';
                    default: return 'bg-gray-50 border-gray-200';
                  }
                };

                const getRangeTextColor = (range: string) => {
                  switch(range) {
                    case '0-20': return 'text-red-800';
                    case '20-40': return 'text-orange-800';
                    case '40-60': return 'text-yellow-800';
                    case '60-80': return 'text-blue-800';
                    case '80-100': return 'text-green-800';
                    default: return 'text-gray-800';
                  }
                };

                return (
                  <div key={range} className={`border-2 rounded-lg p-4 ${getRangeColor(range)}`}>
                    {/* Header */}
                    <div className="mb-3">
                      <h3 className={`text-sm font-medium ${getRangeTextColor(range)}`}>
                        Score Range {range}
                      </h3>
                      <Badge variant="secondary" className="mt-1">
                        {count} symbols
                      </Badge>
                    </div>
                    
                    {/* Symbol List */}
                    <div className="space-y-2 max-h-64 overflow-y-auto">
                      {symbolList.length > 0 ? (
                        symbolList.map((symbolData: any, index: number) => (
                          <div 
                            key={index} 
                            className="flex items-center justify-between p-2 rounded bg-white/70 text-xs border border-white/50"
                          >
                            <div className="flex-1 min-w-0">
                              <div className="font-medium text-gray-900 truncate">
                                {symbolData.symbol}
                              </div>
                              {symbolData.company_name && symbolData.company_name !== symbolData.symbol && (
                                <div className="text-gray-600 truncate text-xs">
                                  {symbolData.company_name}
                                </div>
                              )}
                              {symbolData.industry && symbolData.industry !== 'Unknown' && (
                                <Badge variant="outline" className="text-xs mt-1">
                                  {symbolData.industry}
                                </Badge>
                              )}
                            </div>
                            <div className="text-right ml-2">
                              <div className={`font-medium ${getRangeTextColor(range)}`}>
                                {typeof symbolData.value === 'number' 
                                  ? symbolData.value.toFixed(2) 
                                  : symbolData.value || 'N/A'}
                              </div>
                            </div>
                          </div>
                        ))
                      ) : (
                        <div className="text-center text-gray-500 text-xs py-4">
                          No symbols in this range
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default IndexDistributionPage;
