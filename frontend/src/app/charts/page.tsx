'use client';

import React, { useState, useEffect, useMemo } from 'react';
import { useSearchParams } from 'next/navigation';
import { TradingViewChart } from '@/components/charts/TradingViewChart';
import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';

export default function ChartsPage() {
  const searchParams = useSearchParams();
  const [selectedSymbol, setSelectedSymbol] = useState<string>(searchParams.get('symbol') || 'TCS');
  const [startDate, setStartDate] = useState<string>('2005-01-01'); // Full historical range
  const [endDate, setEndDate] = useState<string>('2025-08-17');
  const [chartType, setChartType] = useState<'candlestick' | 'line' | 'area'>('candlestick');
  const [loadFullData, setLoadFullData] = useState<boolean>(true); // Load all data by default

  // Fetch stock data for the selected symbol
  const { data: stockData, isLoading, error, refetch } = useQuery({
    queryKey: ['stockData', selectedSymbol, startDate, endDate, loadFullData],
    queryFn: async () => {
      console.log('🔄 Fetching stock data for:', selectedSymbol, startDate, endDate, loadFullData ? 50000 : 5000);
      const result = await api.getStockData(selectedSymbol, startDate, endDate, loadFullData ? 50000 : 5000);
      console.log('✅ Stock data received:', result);
      return result;
    },
    enabled: !!selectedSymbol,
    staleTime: 0, // Disable caching temporarily for debugging
    gcTime: 0, // Clear cache immediately
    retry: 1,
  });

  // Fetch available symbol mappings
  const { data: symbolMappings } = useQuery({
    queryKey: ['symbolMappings'],
    queryFn: () => api.getSymbolMappings(),
  });

  const handleSymbolSelect = (symbol: string) => {
    setSelectedSymbol(symbol);
    // Update URL without page reload
    const url = new URL(window.location.href);
    url.searchParams.set('symbol', symbol);
    window.history.pushState({}, '', url.toString());
  };

  const handleDateChange = () => {
    refetch();
  };

  const loadFullHistoricalData = () => {
    setStartDate('2005-01-01');
    setEndDate('2025-08-17');
    setLoadFullData(true);
  };

  const loadRecentData = (months: number) => {
    const end = new Date();
    const start = new Date();
    start.setMonth(start.getMonth() - months);
    
    setStartDate(start.toISOString().split('T')[0]);
    setEndDate(end.toISOString().split('T')[0]);
    setLoadFullData(false);
  };

  // Calculate basic statistics
  // Debug logging
  console.log('📊 Charts page render:', {
    selectedSymbol,
    stockData,
    isLoading,
    error,
    hasData: stockData?.data?.length,
    startDate,
    endDate,
    enabled: !!selectedSymbol
  });    const statistics = useMemo(() => {
      if (!stockData?.data || stockData.data.length === 0) {
        return {
          current: 0,
          change: 0,
          changePercent: 0,
          high52w: 0,
          low52w: 0,
          avgVolume: 0,
          earliestDate: null,
          latestDate: null,
          totalRecords: 0
        };
      }

      // Sort data by date to ensure chronological order
      const sortedData = [...stockData.data].sort((a, b) => 
        new Date(a.date).getTime() - new Date(b.date).getTime()
      );

      const latest = sortedData[sortedData.length - 1];
      const earliest = sortedData[0];
      const previous = sortedData[sortedData.length - 2];

      const current = latest.close_price;
      const previousClose = previous ? previous.close_price : current;
      const change = current - previousClose;
      const changePercent = previousClose !== 0 ? (change / previousClose) * 100 : 0;

      const high52w = Math.max(...sortedData.map(d => d.high_price));
      const low52w = Math.min(...sortedData.map(d => d.low_price));
      const avgVolume = sortedData.reduce((sum, d) => sum + d.volume, 0) / sortedData.length;

      return {
        current,
        change,
        changePercent,
        high52w,
        low52w,
        avgVolume,
        earliestDate: earliest.date,
        latestDate: latest.date,
        totalRecords: sortedData.length
      };
    }, [stockData]);  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Stock Charts</h1>
        <p className="text-gray-600">Interactive candlestick charts powered by TradingView</p>
      </div>

      {/* Controls */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4 mb-6">
        {/* Symbol Selection */}
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-sm font-medium text-gray-700 mb-2">Select Symbol</h3>
          <select 
            value={selectedSymbol}
            onChange={(e) => handleSymbolSelect(e.target.value)}
            className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
          >
            {symbolMappings?.mappings?.slice(0, 20).map((mapping) => (
              <option key={mapping.symbol} value={mapping.symbol}>
                {mapping.symbol} - {mapping.company_name}
              </option>
            ))}
            {!symbolMappings && (
              <>
                <option value="TCS">TCS - Tata Consultancy Services</option>
                <option value="RELIANCE">RELIANCE - Reliance Industries</option>
                <option value="HDFCBANK">HDFCBANK - HDFC Bank</option>
                <option value="INFY">INFY - Infosys</option>
                <option value="ICICIBANK">ICICIBANK - ICICI Bank</option>
              </>
            )}
          </select>
        </div>

        {/* Data Range Presets */}
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-sm font-medium text-gray-700 mb-2">Quick Range</h3>
          <div className="grid grid-cols-2 gap-1">
            <button
              onClick={() => loadRecentData(6)}
              className="px-2 py-1 text-xs rounded bg-gray-100 text-gray-700 hover:bg-gray-200"
            >
              6M
            </button>
            <button
              onClick={() => loadRecentData(12)}
              className="px-2 py-1 text-xs rounded bg-gray-100 text-gray-700 hover:bg-gray-200"
            >
              1Y
            </button>
            <button
              onClick={() => loadRecentData(60)}
              className="px-2 py-1 text-xs rounded bg-gray-100 text-gray-700 hover:bg-gray-200"
            >
              5Y
            </button>
            <button
              onClick={loadFullHistoricalData}
              className={`px-2 py-1 text-xs rounded ${
                loadFullData 
                  ? 'bg-blue-600 text-white' 
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              All (20Y)
            </button>
          </div>
        </div>

        {/* Date Range */}
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-sm font-medium text-gray-700 mb-2">Custom Range</h3>
          <div className="space-y-2">
            <div>
              <label className="text-xs text-gray-500">Start Date</label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => {setStartDate(e.target.value); setLoadFullData(false);}}
                className="block w-full px-3 py-1 border border-gray-300 rounded-md text-sm focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div>
              <label className="text-xs text-gray-500">End Date</label>
              <input
                type="date"
                value={endDate}
                onChange={(e) => {setEndDate(e.target.value); setLoadFullData(false);}}
                className="block w-full px-3 py-1 border border-gray-300 rounded-md text-sm focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>
        </div>

        {/* Chart Type */}
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-sm font-medium text-gray-700 mb-2">Chart Type</h3>
          <div className="grid grid-cols-3 gap-1">
            <button
              onClick={() => setChartType('candlestick')}
              className={`px-2 py-1 text-xs rounded ${
                chartType === 'candlestick' 
                  ? 'bg-blue-600 text-white' 
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              📊 Candle
            </button>
            <button
              onClick={() => setChartType('line')}
              className={`px-2 py-1 text-xs rounded ${
                chartType === 'line' 
                  ? 'bg-blue-600 text-white' 
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              📈 Line
            </button>
            <button
              onClick={() => setChartType('area')}
              className={`px-2 py-1 text-xs rounded ${
                chartType === 'area' 
                  ? 'bg-blue-600 text-white' 
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              📈 Area
            </button>
          </div>
        </div>

        {/* Data Info & Actions */}
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-sm font-medium text-gray-700 mb-2">Data Info</h3>
          <div className="space-y-2">
            <div className="text-xs text-gray-600">
              <div>Records: {stockData?.data?.length || 0}</div>
              <div>Range: {loadFullData ? '20 Years' : 'Custom'}</div>
            </div>
            <button
              onClick={handleDateChange}
              disabled={isLoading}
              className="w-full px-3 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 disabled:opacity-50"
            >
              {isLoading ? 'Loading...' : 'Update Chart'}
            </button>
          </div>
        </div>
      </div>

      {/* Statistics */}
      {statistics && (
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center justify-between">
            <span>📈 {selectedSymbol} - Key Statistics</span>
            <span className="text-sm font-normal text-gray-500">
              {stockData?.data?.length || 0} data points 
              {loadFullData && <span className="text-blue-600 ml-2">• Full History (20+ Years)</span>}
              {isLoading && <span className="text-orange-600 ml-2">• Loading...</span>}
              {error && <span className="text-red-600 ml-2">• Error: {error.message}</span>}
            </span>
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
            <div>
              <div className="text-sm text-gray-500">Current Price</div>
              <div className="text-lg font-semibold">₹{statistics.current.toFixed(2)}</div>
              {statistics.latestDate && (
                <div className="text-xs text-gray-400">
                  {new Date(statistics.latestDate).toLocaleDateString()}
                </div>
              )}
            </div>
            <div>
              <div className="text-sm text-gray-500">Change</div>
              <div className={`text-lg font-semibold ${statistics.change >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {statistics.change >= 0 ? '+' : ''}₹{statistics.change.toFixed(2)} ({statistics.changePercent.toFixed(2)}%)
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-500">Period High</div>
              <div className="text-lg font-semibold">₹{statistics.high52w.toFixed(2)}</div>
            </div>
            <div>
              <div className="text-sm text-gray-500">Period Low</div>
              <div className="text-lg font-semibold">₹{statistics.low52w.toFixed(2)}</div>
            </div>
            <div>
              <div className="text-sm text-gray-500">Avg Volume</div>
              <div className="text-lg font-semibold">{(statistics.avgVolume / 1000000).toFixed(2)}M</div>
            </div>
            <div>
              <div className="text-sm text-gray-500">Data Range</div>
              <div className="text-sm font-semibold">
                {statistics.earliestDate && statistics.latestDate && (
                  <>
                    {new Date(statistics.earliestDate).getFullYear()} - {new Date(statistics.latestDate).getFullYear()}
                  </>
                )}
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-500">Total Records</div>
              <div className="text-lg font-semibold">{statistics.totalRecords.toLocaleString()}</div>
            </div>
          </div>
        </div>
      )}

      {/* Chart */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4 flex items-center">
          📊 {selectedSymbol} Price Chart
        </h3>
        
        {isLoading && (
          <div className="flex items-center justify-center h-96">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
              <p className="mt-4 text-gray-600">Loading chart data...</p>
              <p className="mt-2 text-sm text-gray-500">Symbol: {selectedSymbol} | Dates: {startDate} to {endDate} | Limit: {loadFullData ? 50000 : 5000}</p>
            </div>
          </div>
        )}
        
        {error && (
          <div className="flex items-center justify-center h-96">
            <div className="text-center">
              <div className="text-red-600 mb-2">⚠️ Error loading data</div>
              <p className="text-gray-600">{error.message}</p>
              <button 
                onClick={() => refetch()}
                className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
              >
                Retry
              </button>
            </div>
          </div>
        )}
        
        {stockData?.data && !isLoading && !error && (
          <div className="h-[500px] w-full">
            <TradingViewChart
              data={stockData.data}
              symbol={selectedSymbol}
              chartType={chartType}
              height={500}
            />
          </div>
        )}
        
        {stockData?.data?.length === 0 && !isLoading && !error && (
          <div className="flex items-center justify-center h-96">
            <div className="text-center">
              <div className="text-gray-400 mb-2">📊</div>
              <p className="text-gray-600">No data available for {selectedSymbol}</p>
              <p className="text-sm text-gray-500 mt-2">Try selecting a different symbol or date range</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
