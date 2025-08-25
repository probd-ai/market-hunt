'use client'

import { useState, useEffect, useRef, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { createChart, IChartApi, CandlestickData, LineData, ISeriesApi, UTCTimestamp, CandlestickSeries, LineSeries } from 'lightweight-charts';
import { apiClient } from '@/lib/api';

interface StockData {
  scrip_code: number;
  symbol: string;
  date: string;
  open_price: number;
  high_price: number;
  low_price: number;
  close_price: number;
  volume: number;
  value: number;
}

interface IndicatorData {
  date: string;
  value?: number;
  crs_open?: number;
  crs_high?: number;
  crs_low?: number;
  crs_close?: number;
  indicator: string;
  period?: number;
  base_symbol?: string;
}

interface CrsApiResponse {
  data: IndicatorData[];
  total_points: number;
  symbol: string;
  indicator_type: string;
}

interface StockApiResponse {
  data: StockData[];
}

interface StockMapping {
  symbol: string;
  company_name: string;
  industry: string;
}

const CHART_OPTIONS = {
  layout: {
    background: { color: '#1a1a1a' },
    textColor: '#d1d5db',
  },
  grid: {
    vertLines: { color: '#2d3748' },
    horzLines: { color: '#2d3748' },
  },
  rightPriceScale: {
    borderColor: '#4a5568',
  },
  timeScale: {
    borderColor: '#4a5568',
    timeVisible: true,
    secondsVisible: false,
  },
  crosshair: {
    mode: 1,
  },
  watermark: {
    visible: false,
  },
  handleScroll: {
    mouseWheel: true,
    pressedMouseMove: true,
  },
  handleScale: {
    axisPressedMouseMove: true,
    mouseWheel: true,
    pinch: true,
  },
};

// Available indicators for overlay
const AVAILABLE_INDICATORS = [
  { type: 'sma', label: 'SMA', color: '#ef4444', periods: [5, 10, 20, 50, 200] },
  { type: 'ema', label: 'EMA', color: '#06b6d4', periods: [5, 10, 20, 50] },
];

function DualChartContent() {
  const searchParams = useSearchParams();
  const [symbol, setSymbol] = useState(searchParams.get('symbol') || 'RELIANCE');
  const [stockData, setStockData] = useState<StockData[]>([]);
  const [crsData, setCrsData] = useState<IndicatorData[]>([]);
  const [stockMappings, setStockMappings] = useState<StockMapping[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isCrsLoading, setIsCrsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [showDropdown, setShowDropdown] = useState(false);
  const [timeframe, setTimeframe] = useState('ALL');
  
  // Chart references
  const priceChartRef = useRef<HTMLDivElement>(null);
  const crsChartRef = useRef<HTMLDivElement>(null);
  const priceChartInstance = useRef<IChartApi | null>(null);
  const crsChartInstance = useRef<IChartApi | null>(null);
  const priceSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const crsSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  
  // Indicator state
  const [priceIndicators, setPriceIndicators] = useState<{[key: string]: {enabled: boolean, period: number, series?: any}}>({});
  const [crsIndicators, setCrsIndicators] = useState<{[key: string]: {enabled: boolean, period: number, series?: any}}>({});

  // Initialize chart instances
  useEffect(() => {
    if (priceChartRef.current && !priceChartInstance.current) {
      priceChartInstance.current = createChart(priceChartRef.current, {
        ...CHART_OPTIONS,
        height: 400,
      });
      
      priceSeriesRef.current = priceChartInstance.current.addSeries(CandlestickSeries, {
        upColor: '#26a69a',
        downColor: '#ef5350',
        borderVisible: false,
        wickUpColor: '#26a69a',
        wickDownColor: '#ef5350',
      });
    }

    if (crsChartRef.current && !crsChartInstance.current) {
      crsChartInstance.current = createChart(crsChartRef.current, {
        ...CHART_OPTIONS,
        height: 400,
      });
      
      crsSeriesRef.current = crsChartInstance.current.addSeries(CandlestickSeries, {
        upColor: '#26a69a',
        downColor: '#ef5350',
        borderVisible: false,
        wickUpColor: '#26a69a',
        wickDownColor: '#ef5350',
      });
    }

    // Cleanup function
    return () => {
      if (priceChartInstance.current) {
        priceChartInstance.current.remove();
        priceChartInstance.current = null;
      }
      if (crsChartInstance.current) {
        crsChartInstance.current.remove();
        crsChartInstance.current = null;
      }
    };
  }, []);

  // Handle chart resize
  useEffect(() => {
    const handleResize = () => {
      if (priceChartInstance.current) {
        priceChartInstance.current.applyOptions({ width: priceChartRef.current?.clientWidth });
      }
      if (crsChartInstance.current) {
        crsChartInstance.current.applyOptions({ width: crsChartRef.current?.clientWidth });
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Load stock mappings
  useEffect(() => {
    const loadMappings = async () => {
      try {
        const response = await apiClient.getStockMappings();
        setStockMappings(response.mappings);
      } catch (error) {
        console.error('Failed to load stock mappings:', error);
      }
    };
    loadMappings();
  }, []);

  // Convert timestamp for TradingView
  const convertToTimestamp = (dateString: string): UTCTimestamp => {
    const date = new Date(dateString);
    return Math.floor(date.getTime() / 1000) as UTCTimestamp;
  };

  // Transform stock data for candlestick chart
  const transformToCandlestickData = (data: StockData[]): CandlestickData[] => {
    return data
      .filter((item, index, self) => 
        index === self.findIndex(t => t.date === item.date)
      )
      .map(item => ({
        time: convertToTimestamp(item.date),
        open: item.open_price,
        high: item.high_price,
        low: item.low_price,
        close: item.close_price,
      }))
      .sort((a, b) => a.time - b.time);
  };

  // Transform CRS data for candlestick chart
  const transformCrsToCandlestickData = (data: IndicatorData[]): CandlestickData[] => {
    return data
      .filter(item => item.crs_open !== undefined)
      .filter((item, index, self) => 
        index === self.findIndex(t => t.date === item.date)
      )
      .map(item => ({
        time: convertToTimestamp(item.date),
        open: item.crs_open!,
        high: item.crs_high!,
        low: item.crs_low!,
        close: item.crs_close!,
      }))
      .sort((a, b) => a.time - b.time);
  };

  // Load stock data
  const loadData = async (selectedSymbol: string, timeframeParam: string) => {
    setIsLoading(true);
    setError(null);

    try {
      const dateRanges = {
        '1Y': { 
          start: new Date(Date.now() - 365 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
          end: new Date().toISOString().split('T')[0]
        },
        '5Y': { 
          start: new Date(Date.now() - 5 * 365 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
          end: new Date().toISOString().split('T')[0]
        },
        'ALL': { start: '2005-01-01', end: new Date().toISOString().split('T')[0] }
      };

      const range = dateRanges[timeframeParam as keyof typeof dateRanges];
      const response = await apiClient.getStockData(selectedSymbol, range.start, range.end, 10000);
      const data = response.data;

      console.log(`Loaded ${data.length} price data points for ${selectedSymbol}`);
      setStockData(data);

      // Update price chart
      if (priceSeriesRef.current && data.length > 0) {
        const chartData = transformToCandlestickData(data);
        priceSeriesRef.current.setData(chartData);
        priceChartInstance.current?.timeScale().fitContent();
      }

    } catch (error) {
      console.error('Error loading data:', error);
      setError('Failed to load price data');
    } finally {
      setIsLoading(false);
    }
  };

  // Load CRS data
  const loadCrsData = async (selectedSymbol: string, timeframeParam: string, baseSymbol: string = "Nifty 500") => {
    setIsCrsLoading(true);
    setError(null);

    try {
      const dateRanges = {
        '1Y': { 
          start: new Date(Date.now() - 365 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
          end: new Date().toISOString().split('T')[0]
        },
        '5Y': { 
          start: new Date(Date.now() - 5 * 365 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
          end: new Date().toISOString().split('T')[0]
        },
        'ALL': { start: '2005-01-01', end: new Date().toISOString().split('T')[0] }
      };

      const range = dateRanges[timeframeParam as keyof typeof dateRanges];
      
      const response = await fetch('/api/proxy/indicators', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbol: selectedSymbol,
          indicator_type: 'crs',
          base_symbol: baseSymbol,
          start_date: range.start,
          end_date: range.end
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const result = await response.json();

      console.log(`Loaded ${result.data.length} CRS data points for ${selectedSymbol} vs ${baseSymbol}`);
      setCrsData(result.data);

      // Update CRS chart
      if (crsSeriesRef.current && result.data.length > 0) {
        const chartData = transformCrsToCandlestickData(result.data);
        crsSeriesRef.current.setData(chartData);
        crsChartInstance.current?.timeScale().fitContent();
      }

    } catch (error) {
      console.error('Error loading CRS data:', error);
      setError('Failed to load CRS data');
    } finally {
      setIsCrsLoading(false);
    }
  };

  // Load indicator data
  const loadIndicatorData = async (selectedSymbol: string, indicatorType: string, period: number, chartType: 'price' | 'crs') => {
    try {
      const dateRanges = {
        '1Y': { 
          start: new Date(Date.now() - 365 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
          end: new Date().toISOString().split('T')[0]
        },
        '5Y': { 
          start: new Date(Date.now() - 5 * 365 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
          end: new Date().toISOString().split('T')[0]
        },
        'ALL': { start: '2005-01-01', end: new Date().toISOString().split('T')[0] }
      };

      const range = dateRanges[timeframe as keyof typeof dateRanges];
      
      // For CRS chart, use CRS data; for price chart, use original symbol
      const targetSymbol = chartType === 'crs' ? symbol : selectedSymbol;
      
      const response = await fetch('/api/proxy/indicators', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbol: targetSymbol,
          indicator_type: indicatorType,
          period: period,
          start_date: range.start,
          end_date: range.end
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const result = await response.json();
      return result.data;
    } catch (error) {
      console.error('Error loading indicator data:', error);
      throw error;
    }
  };

  // Toggle indicator
  const toggleIndicator = async (indicatorType: string, chartType: 'price' | 'crs') => {
    const indicatorState = chartType === 'price' ? priceIndicators : crsIndicators;
    const setIndicatorState = chartType === 'price' ? setPriceIndicators : setCrsIndicators;
    const chartInstance = chartType === 'price' ? priceChartInstance.current : crsChartInstance.current;
    
    const key = `${indicatorType}_${indicatorState[indicatorType]?.period || 20}`;
    const isCurrentlyEnabled = indicatorState[key]?.enabled || false;

    if (isCurrentlyEnabled) {
      // Remove indicator
      if (indicatorState[key]?.series) {
        chartInstance?.removeSeries(indicatorState[key].series!);
      }
      setIndicatorState(prev => ({
        ...prev,
        [key]: { ...prev[key], enabled: false, series: undefined }
      }));
    } else {
      // Add indicator
      try {
        const period = indicatorState[key]?.period || 20;
        const indicatorData = await loadIndicatorData(symbol, indicatorType, period, chartType);
        
        if (indicatorData && indicatorData.length > 0 && chartInstance) {
          // Convert to line data
          const lineData: LineData[] = indicatorData
            .filter((item: any) => item.value !== undefined)
            .map((item: any) => ({
              time: convertToTimestamp(item.date),
              value: item.value,
            }))
            .sort((a: any, b: any) => a.time - b.time);

          const indicatorConfig = AVAILABLE_INDICATORS.find(ind => ind.type === indicatorType);
          const lineSeries = chartInstance.addSeries(LineSeries, {
            color: indicatorConfig?.color || '#ffffff',
            lineWidth: 2,
            title: `${indicatorConfig?.label || indicatorType.toUpperCase()}(${period})`,
          });

          lineSeries.setData(lineData);

          setIndicatorState(prev => ({
            ...prev,
            [key]: { enabled: true, period, series: lineSeries }
          }));
        }
      } catch (error) {
        console.error('Error adding indicator:', error);
      }
    }
  };

  // Initial load and when symbol/timeframe changes
  useEffect(() => {
    if (symbol) {
      loadData(symbol, timeframe);
      loadCrsData(symbol, timeframe);
    }
  }, [symbol, timeframe]);

  // Filter stock mappings for autocomplete
  const filteredMappings = stockMappings
    .filter(mapping => 
      mapping.symbol.toLowerCase().includes(searchTerm.toLowerCase()) ||
      mapping.company_name.toLowerCase().includes(searchTerm.toLowerCase())
    )
    .slice(0, 10);

  const handleSymbolSelect = (selectedSymbol: string) => {
    setSymbol(selectedSymbol);
    setSearchTerm('');
    setShowDropdown(false);
    
    // Update URL
    const newUrl = new URL(window.location.href);
    newUrl.searchParams.set('symbol', selectedSymbol);
    window.history.pushState({}, '', newUrl.toString());
  };

  return (
    <DashboardLayout>
      <div className="p-6 bg-gray-900 min-h-screen">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-4">
            <h1 className="text-2xl font-bold text-white">Dual Chart - Price vs CRS</h1>
            <div className="text-sm text-gray-400">
              {stockData.length > 0 && `${stockData.length} price records`}
              {crsData.length > 0 && ` | ${crsData.length} CRS records`}
            </div>
          </div>

          {/* Controls */}
          <div className="flex items-center gap-4 mb-4">
            {/* Symbol Search */}
            <div className="relative">
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => {
                  setSearchTerm(e.target.value);
                  setShowDropdown(true);
                }}
                onFocus={() => setShowDropdown(true)}
                placeholder="Search symbol or company..."
                className="px-4 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white w-64"
              />
              
              {showDropdown && filteredMappings.length > 0 && (
                <div className="absolute top-full left-0 right-0 bg-gray-800 border border-gray-600 rounded-lg mt-1 max-h-60 overflow-y-auto z-10">
                  {filteredMappings.map((mapping) => (
                    <div
                      key={mapping.symbol}
                      onClick={() => handleSymbolSelect(mapping.symbol)}
                      className="px-4 py-2 hover:bg-gray-700 cursor-pointer text-white"
                    >
                      <div className="font-medium">{mapping.symbol}</div>
                      <div className="text-sm text-gray-400">{mapping.company_name}</div>
                      <div className="text-xs text-gray-500">{mapping.industry}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Current Symbol */}
            <div className="px-4 py-2 bg-blue-600 rounded-lg text-white font-medium">
              {symbol}
            </div>

            {/* Timeframe Buttons */}
            <div className="flex gap-2">
              {['1Y', '5Y', 'ALL'].map((tf) => (
                <button
                  key={tf}
                  onClick={() => setTimeframe(tf)}
                  className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                    timeframe === tf
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                  }`}
                >
                  {tf}
                </button>
              ))}
            </div>
          </div>

          {/* Error Display */}
          {error && (
            <div className="bg-red-600 text-white p-3 rounded-lg mb-4">
              {error}
            </div>
          )}

          {/* Loading State */}
          {(isLoading || isCrsLoading) && (
            <div className="bg-blue-600 text-white p-3 rounded-lg mb-4">
              Loading {isLoading ? 'price' : ''} {isCrsLoading ? 'CRS' : ''} data...
            </div>
          )}
        </div>

        {/* Charts Container */}
        <div className="grid grid-rows-2 gap-4 h-[calc(100vh-300px)]">
          {/* Price Chart */}
          <div className="bg-gray-800 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-lg font-semibold text-white">Price Chart - {symbol}</h2>
              
              {/* Price Chart Indicators */}
              <div className="flex items-center gap-4">
                {AVAILABLE_INDICATORS.map((indicator) => (
                  <div key={`price_${indicator.type}`} className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      id={`price_${indicator.type}`}
                      checked={priceIndicators[`${indicator.type}_20`]?.enabled || false}
                      onChange={() => toggleIndicator(indicator.type, 'price')}
                      className="rounded"
                    />
                    <label htmlFor={`price_${indicator.type}`} className="text-sm text-gray-300">
                      <span className="inline-block w-3 h-3 rounded mr-1" style={{backgroundColor: indicator.color}}></span>
                      {indicator.label}(20)
                    </label>
                  </div>
                ))}
              </div>
            </div>
            <div ref={priceChartRef} className="w-full h-full min-h-[350px]" />
          </div>

          {/* CRS Chart */}
          <div className="bg-gray-800 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-lg font-semibold text-white">CRS Chart - {symbol} vs NIFTY 500</h2>
              
              {/* CRS Chart Indicators */}
              <div className="flex items-center gap-4">
                {AVAILABLE_INDICATORS.map((indicator) => (
                  <div key={`crs_${indicator.type}`} className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      id={`crs_${indicator.type}`}
                      checked={crsIndicators[`${indicator.type}_20`]?.enabled || false}
                      onChange={() => toggleIndicator(indicator.type, 'crs')}
                      className="rounded"
                    />
                    <label htmlFor={`crs_${indicator.type}`} className="text-sm text-gray-300">
                      <span className="inline-block w-3 h-3 rounded mr-1" style={{backgroundColor: indicator.color}}></span>
                      {indicator.label}(20)
                    </label>
                  </div>
                ))}
              </div>
            </div>
            <div ref={crsChartRef} className="w-full h-full min-h-[350px]" />
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}

export default function DualChartPage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <DualChartContent />
    </Suspense>
  );
}
