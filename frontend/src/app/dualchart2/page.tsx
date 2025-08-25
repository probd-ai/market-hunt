'use client'

import { useState, useEffect, useRef, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { createChart, IChartApi, CandlestickData, LineData, UTCTimestamp, CandlestickSeries, LineSeries } from 'lightweight-charts';
import { apiClient } from '@/lib/api';

interface StockData {
  date: string;
  open_price: number;
  high_price: number;
  low_price: number;
  close_price: number;
  volume: number;
}

interface CrsData {
  date: string;
  crs_open: number;
  crs_high: number;
  crs_low: number;
  crs_close: number;
  indicator: string;
  base_symbol: string;
}

interface IndicatorData {
  date: string;
  value: number;
  indicator: string;
  period: number;
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

function DualChartContent() {
  const searchParams = useSearchParams();
  const [symbol, setSymbol] = useState(searchParams.get('symbol') || 'RELIANCE');
  const [stockData, setStockData] = useState<StockData[]>([]);
  const [crsData, setCrsData] = useState<CrsData[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isCrsLoading, setIsCrsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [timeframe, setTimeframe] = useState('1Y');
  
  // Chart references
  const priceChartRef = useRef<HTMLDivElement>(null);
  const crsChartRef = useRef<HTMLDivElement>(null);
  const priceChartInstance = useRef<IChartApi | null>(null);
  const crsChartInstance = useRef<IChartApi | null>(null);
  const priceSeriesRef = useRef<any>(null);
  const crsSeriesRef = useRef<any>(null);

  // Initialize charts
  useEffect(() => {
    if (priceChartRef.current && !priceChartInstance.current) {
      priceChartInstance.current = createChart(priceChartRef.current, {
        ...CHART_OPTIONS,
        height: 350,
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
        height: 350,
      });
      
      crsSeriesRef.current = crsChartInstance.current.addSeries(CandlestickSeries, {
        upColor: '#26a69a',
        downColor: '#ef5350',
        borderVisible: false,
        wickUpColor: '#26a69a',
        wickDownColor: '#ef5350',
      });
    }

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

  // Handle resize
  useEffect(() => {
    const handleResize = () => {
      if (priceChartInstance.current && priceChartRef.current) {
        priceChartInstance.current.applyOptions({ width: priceChartRef.current.clientWidth });
      }
      if (crsChartInstance.current && crsChartRef.current) {
        crsChartInstance.current.applyOptions({ width: crsChartRef.current.clientWidth });
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
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
  const transformCrsToCandlestickData = (data: CrsData[]): CandlestickData[] => {
    return data
      .filter((item, index, self) => 
        index === self.findIndex(t => t.date === item.date)
      )
      .map(item => ({
        time: convertToTimestamp(item.date),
        open: item.crs_open,
        high: item.crs_high,
        low: item.crs_low,
        close: item.crs_close,
      }))
      .sort((a, b) => a.time - b.time);
  };

  // Load stock data
  const loadPriceData = async (selectedSymbol: string, timeframeParam: string) => {
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
      console.error('Error loading price data:', error);
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

  // Load data when symbol or timeframe changes
  useEffect(() => {
    if (symbol) {
      loadPriceData(symbol, timeframe);
      loadCrsData(symbol, timeframe);
    }
  }, [symbol, timeframe]);

  const handleSymbolChange = (newSymbol: string) => {
    setSymbol(newSymbol);
    
    // Update URL
    const newUrl = new URL(window.location.href);
    newUrl.searchParams.set('symbol', newSymbol);
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
            {/* Symbol Input */}
            <div className="flex items-center gap-2">
              <label className="text-white">Symbol:</label>
              <input
                type="text"
                value={symbol}
                onChange={(e) => handleSymbolChange(e.target.value.toUpperCase())}
                className="px-3 py-2 bg-gray-800 border border-gray-600 rounded text-white w-32"
                placeholder="SYMBOL"
              />
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
              <div className="text-sm text-gray-400">
                OHLC Candlestick Chart
              </div>
            </div>
            <div ref={priceChartRef} className="w-full h-full min-h-[300px]" />
          </div>

          {/* CRS Chart */}
          <div className="bg-gray-800 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-lg font-semibold text-white">CRS Chart - {symbol} vs Nifty 500</h2>
              <div className="text-sm text-gray-400">
                Comparative Relative Strength
              </div>
            </div>
            <div ref={crsChartRef} className="w-full h-full min-h-[300px]" />
          </div>
        </div>

        {/* Info Panel */}
        <div className="mt-4 bg-gray-800 rounded-lg p-4">
          <h3 className="text-white font-semibold mb-2">About CRS (Comparative Relative Strength)</h3>
          <p className="text-gray-300 text-sm">
            CRS shows how {symbol} performs relative to Nifty 500. Values above the baseline indicate outperformance, 
            while values below indicate underperformance compared to the broader market index.
          </p>
        </div>
      </div>
    </DashboardLayout>
  );
}

export default function DualChartPage() {
  return (
    <Suspense fallback={<div className="p-6 text-white">Loading dual chart...</div>}>
      <DualChartContent />
    </Suspense>
  );
}
