'use client';

import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import { TradingViewChart } from '@/components/charts/TradingViewChart';
import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';

export default function ChartsPage() {
  const searchParams = useSearchParams();
  const [selectedSymbol, setSelectedSymbol] = useState<string>(searchParams.get('symbol') || 'TCS');
  const [startDate, setStartDate] = useState<string>('2024-01-01');
  const [endDate, setEndDate] = useState<string>('2025-08-17');
  const [chartType, setChartType] = useState<'candlestick' | 'line' | 'area'>('candlestick');

  // Fetch stock data for the selected symbol
  const { data: stockData, isLoading, error, refetch } = useQuery({
    queryKey: ['stockData', selectedSymbol, startDate, endDate],
    queryFn: () => api.getStockData(selectedSymbol, startDate, endDate),
    enabled: !!selectedSymbol,
  });

  // Fetch available symbol mappings
  const { data: symbolMappings } = useQuery({
    queryKey: ['symbolMappings'],
    queryFn: () => api.getSymbolMappings(50, 0),
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

  // Calculate basic statistics
  const statistics = React.useMemo(() => {
    if (!stockData?.data?.length) return null;
    
    const prices = stockData.data.map(d => d.close_price);
    const volumes = stockData.data.map(d => d.volume);
    
    const current = prices[prices.length - 1];
    const previous = prices[prices.length - 2];
    const change = current - previous;
    const changePercent = (change / previous) * 100;
    
    return {
      current: current,
      change: change,
      changePercent: changePercent,
      high52w: Math.max(...prices),
      low52w: Math.min(...prices),
      avgVolume: volumes.reduce((a, b) => a + b, 0) / volumes.length,
      totalRecords: stockData.data.length
    };
  }, [stockData]);

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Stock Charts</h1>
        <p className="text-gray-600">Interactive candlestick charts powered by TradingView</p>
      </div>

      {/* Controls */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 mb-6">
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

        {/* Date Range */}
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-sm font-medium text-gray-700 mb-2">Date Range</h3>
          <div className="space-y-2">
            <div>
              <label className="text-xs text-gray-500">Start Date</label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="block w-full px-3 py-1 border border-gray-300 rounded-md text-sm focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div>
              <label className="text-xs text-gray-500">End Date</label>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
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

        {/* Actions */}
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-sm font-medium text-gray-700 mb-2">Actions</h3>
          <button
            onClick={handleDateChange}
            disabled={isLoading}
            className="w-full px-3 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            {isLoading ? 'Loading...' : 'Update Chart'}
          </button>
        </div>
      </div>

      {/* Statistics */}
      {statistics && (
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center">
            📈 {selectedSymbol} - Key Statistics
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            <div>
              <div className="text-sm text-gray-500">Current Price</div>
              <div className="text-lg font-semibold">₹{statistics.current.toFixed(2)}</div>
            </div>
            <div>
              <div className="text-sm text-gray-500">Change</div>
              <div className={`text-lg font-semibold ${statistics.change >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {statistics.change >= 0 ? '+' : ''}₹{statistics.change.toFixed(2)} ({statistics.changePercent.toFixed(2)}%)
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-500">52W High</div>
              <div className="text-lg font-semibold">₹{statistics.high52w.toFixed(2)}</div>
            </div>
            <div>
              <div className="text-sm text-gray-500">52W Low</div>
              <div className="text-lg font-semibold">₹{statistics.low52w.toFixed(2)}</div>
            </div>
            <div>
              <div className="text-sm text-gray-500">Avg Volume</div>
              <div className="text-lg font-semibold">{(statistics.avgVolume / 1000000).toFixed(2)}M</div>
            </div>
            <div>
              <div className="text-sm text-gray-500">Data Points</div>
              <div className="text-lg font-semibold">{statistics.totalRecords}</div>
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
          <TradingViewChart
            data={stockData.data}
            symbol={selectedSymbol}
            chartType={chartType}
          />
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
