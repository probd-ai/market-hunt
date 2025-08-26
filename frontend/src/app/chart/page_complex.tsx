'use client';

import { useState, useEffect, useRef, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { createChart, CandlestickSeries, ColorType } from 'lightweight-charts';
import { apiClient } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { 
  MagnifyingGlassIcon,
  ArrowPathIcon,
  ExclamationTriangleIcon 
} from '@heroicons/react/24/outline';

interface ChartData {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
}

function ChartComponent() {
  const searchParams = useSearchParams();
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<any>(null);
  const seriesRef = useRef<any>(null);
  
  const [currentSymbol, setCurrentSymbol] = useState(searchParams?.get('symbol') || 'LT');
  const [symbolInput, setSymbolInput] = useState(currentSymbol);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [chartData, setChartData] = useState<ChartData[]>([]);
  const [hasMoreData, setHasMoreData] = useState(true);
  const [totalRecords, setTotalRecords] = useState(0);
  const [loadedRecords, setLoadedRecords] = useState(0);

  // Progressive loading parameters
  const INITIAL_LOAD_SIZE = 1000;
  const INCREMENTAL_LOAD_SIZE = 1000;

  // Initialize chart
  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      layout: {
        textColor: '#333',
        background: { 
          type: ColorType.Solid, 
          color: '#ffffff' 
        },
        fontSize: 12,
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        attributionLogo: true,
      },
      grid: {
        vertLines: { color: '#f0f0f0' },
        horzLines: { color: '#f0f0f0' }
      },
      crosshair: {
        mode: 0,
        vertLine: {
          color: '#758696',
          width: 1,
          style: 2,
        },
        horzLine: {
          color: '#758696',
          width: 1,
          style: 2,
        }
      },
      timeScale: {
        timeVisible: true,
        secondsVisible: false,
        borderColor: '#D1D4DC',
      },
      rightPriceScale: {
        borderColor: '#D1D4DC',
      },
    });

    const candlestickSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#26a69a',
      downColor: '#ef5350',
      borderVisible: false,
      wickUpColor: '#26a69a',
      wickDownColor: '#ef5350',
      priceFormat: {
        type: 'price',
        precision: 2,
        minMove: 0.01,
      }
    });

    chartRef.current = chart;
    seriesRef.current = candlestickSeries;

    // Progressive loading: detect when user scrolls to the beginning
    const handleVisibleRangeChange = () => {
      if (!chartRef.current || !hasMoreData || isLoadingMore) return;
      
      const timeScale = chartRef.current.timeScale();
      const visibleRange = timeScale.getVisibleRange();
      
      if (visibleRange && chartData.length > 0) {
        const firstVisibleTime = new Date(visibleRange.from * 1000);
        const firstDataTime = new Date(chartData[0].time);
        
        // If user scrolled close to the beginning, load more data
        const timeDiff = firstDataTime.getTime() - firstVisibleTime.getTime();
        const daysDiff = timeDiff / (1000 * 60 * 60 * 24);
        
        if (daysDiff < 30) { // Load more when within 30 days of start
          loadMoreHistoricalData();
        }
      }
    };

    // Subscribe to visible range changes
    chart.timeScale().subscribeVisibleTimeRangeChange(handleVisibleRangeChange);

    // Handle resize
    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        const { clientWidth, clientHeight } = chartContainerRef.current;
        chartRef.current.applyOptions({
          width: clientWidth,
          height: clientHeight,
        });
      }
    };

    const resizeObserver = new ResizeObserver(handleResize);
    resizeObserver.observe(chartContainerRef.current);

    return () => {
      resizeObserver.disconnect();
      if (chartRef.current) {
        chart.timeScale().unsubscribeVisibleTimeRangeChange(handleVisibleRangeChange);
        chartRef.current.remove();
      }
    };
  }, [hasMoreData, isLoadingMore, chartData]);

  // Transform database data to TradingView format
  const transformData = (rawData: any[]): ChartData[] => {
    return rawData
      .map(item => {
        try {
          // Convert date to YYYY-MM-DD format that TradingView expects
          const date = new Date(item.date);
          
          // Validate that the date is valid
          if (isNaN(date.getTime())) {
            console.warn(`Invalid date found: ${item.date}`);
            return null;
          }
          
          const formattedDate = date.toISOString().split('T')[0]; // Gets YYYY-MM-DD
          
          // Validate OHLC data
          const open = parseFloat(item.open_price);
          const high = parseFloat(item.high_price);
          const low = parseFloat(item.low_price);
          const close = parseFloat(item.close_price);
          
          if (isNaN(open) || isNaN(high) || isNaN(low) || isNaN(close)) {
            console.warn(`Invalid OHLC data found for date ${formattedDate}`);
            return null;
          }
          
          return {
            time: formattedDate,
            open: open,
            high: high,
            low: low,
            close: close,
          };
        } catch (error) {
          console.warn(`Error processing data item:`, item, error);
          return null;
        }
      })
      .filter(item => item !== null) // Remove invalid items
      .sort((a, b) => new Date(a!.time).getTime() - new Date(b!.time).getTime()) as ChartData[];
  };

  // Initial load of chart data
  const loadChartData = async (symbol: string, isInitialLoad = true) => {
    console.log(`loadChartData called for ${symbol}, isInitialLoad: ${isInitialLoad}`);
    
    if (isInitialLoad) {
      setIsLoading(true);
      setError(null);
      setChartData([]);
      setLoadedRecords(0);
      setHasMoreData(true);
    }

    try {
      console.log(`Fetching data for ${symbol}...`);
      const response = await apiClient.getStockData(symbol, undefined, undefined, INITIAL_LOAD_SIZE);
      console.log(`API response:`, response);
      
      const transformedData = transformData(response.data || []);
      console.log(`Transformed ${transformedData.length} records`);
      console.log(`First few records:`, transformedData.slice(0, 3));
      
      if (transformedData.length === 0) {
        console.log(`No data available for ${symbol}`);
        setError(`No historical data available for ${symbol}`);
        return;
      }

      setTotalRecords(response.total_records || transformedData.length);
      setLoadedRecords(transformedData.length);
      setChartData(transformedData);
      setHasMoreData(transformedData.length >= INITIAL_LOAD_SIZE);
      
      if (seriesRef.current) {
        console.log(`Setting data to chart series...`);
        seriesRef.current.setData(transformedData);
        // Fit content to show recent data
        if (chartRef.current) {
          console.log(`Fitting chart content...`);
          chartRef.current.timeScale().fitContent();
        }
      } else {
        console.log(`Chart series not ready yet`);
      }
    } catch (err: any) {
      console.error(`Error loading data for ${symbol}:`, err);
      setError(`Failed to load data for ${symbol}: ${err.message}`);
    } finally {
      if (isInitialLoad) {
        setIsLoading(false);
      }
    }
  };

  // Load more historical data when user scrolls back
  const loadMoreHistoricalData = async () => {
    if (!hasMoreData || isLoadingMore || chartData.length === 0) return;
    
    setIsLoadingMore(true);
    
    try {
      // Get the earliest date from current data
      const earliestDate = chartData[0].time;
      const endDate = new Date(earliestDate);
      endDate.setDate(endDate.getDate() - 1); // Day before earliest
      
      const response = await apiClient.getStockData(
        currentSymbol, 
        undefined, 
        endDate.toISOString().split('T')[0], // YYYY-MM-DD format
        INCREMENTAL_LOAD_SIZE
      );
      
      const newData = transformData(response.data || []);
      
      if (newData.length === 0) {
        setHasMoreData(false);
        return;
      }
      
      // Merge new historical data with existing data
      const mergedData = [...newData, ...chartData];
      setChartData(mergedData);
      setLoadedRecords(prev => prev + newData.length);
      setHasMoreData(newData.length >= INCREMENTAL_LOAD_SIZE);
      
      // Update chart with merged data
      if (seriesRef.current) {
        seriesRef.current.setData(mergedData);
      }
      
    } catch (err: any) {
      console.error('Failed to load more historical data:', err);
    } finally {
      setIsLoadingMore(false);
    }
  };

  // Load data when symbol changes
  useEffect(() => {
    if (currentSymbol) {
      loadChartData(currentSymbol);
    }
  }, [currentSymbol]);

  // Handle symbol change
  const handleSymbolChange = () => {
    if (symbolInput.trim() && symbolInput.trim() !== currentSymbol) {
      setCurrentSymbol(symbolInput.trim().toUpperCase());
      // Update URL without page refresh
      const newUrl = new URL(window.location.href);
      newUrl.searchParams.set('symbol', symbolInput.trim().toUpperCase());
      window.history.replaceState({}, '', newUrl);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSymbolChange();
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header Strip */}
      <div className="bg-white shadow-sm border-b border-gray-200 px-4 py-3">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <h1 className="text-lg font-semibold text-gray-900">
              {currentSymbol} - Stock Chart
            </h1>
            <div className="flex items-center space-x-3 text-sm">
              {isLoading && (
                <div className="flex items-center text-gray-500">
                  <ArrowPathIcon className="h-4 w-4 animate-spin mr-1" />
                  Loading initial data...
                </div>
              )}
              {isLoadingMore && (
                <div className="flex items-center text-blue-600">
                  <ArrowPathIcon className="h-4 w-4 animate-spin mr-1" />
                  Loading more data...
                </div>
              )}
              {!isLoading && !isLoadingMore && chartData.length > 0 && (
                <div className="text-gray-600">
                  Showing {loadedRecords.toLocaleString()} of {totalRecords.toLocaleString()} records
                  {hasMoreData && " • Scroll left for more history"}
                </div>
              )}
            </div>
          </div>
          
          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-2">
              <Input
                type="text"
                placeholder="Enter symbol..."
                value={symbolInput}
                onChange={(e) => setSymbolInput(e.target.value.toUpperCase())}
                onKeyPress={handleKeyPress}
                className="w-32 text-sm"
                disabled={isLoading}
              />
              <Button
                onClick={handleSymbolChange}
                disabled={isLoading || !symbolInput.trim()}
                size="sm"
                className="flex items-center gap-1"
              >
                <MagnifyingGlassIcon className="h-4 w-4" />
                Load
              </Button>
            </div>
            
            <div className="text-xs text-gray-500">
              Powered by{' '}
              <a 
                href="https://www.tradingview.com/" 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-blue-600 hover:text-blue-800"
              >
                TradingView
              </a>
            </div>
          </div>
        </div>
      </div>

      {/* Chart Container */}
      <div className="flex-1 p-4">
        <div className="max-w-7xl mx-auto h-full">
          {error ? (
            <div className="h-full flex items-center justify-center">
              <div className="text-center">
                <ExclamationTriangleIcon className="h-12 w-12 text-red-500 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">Error Loading Chart</h3>
                <p className="text-gray-600 mb-4">{error}</p>
                <Button onClick={() => loadChartData(currentSymbol)}>
                  Try Again
                </Button>
              </div>
            </div>
          ) : (
            <div 
              ref={chartContainerRef}
              className="w-full bg-white rounded-lg shadow border border-gray-200"
              style={{ height: 'calc(100vh - 140px)' }}
            />
          )}
        </div>
      </div>
    </div>
  );
}

export default function ChartPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <ArrowPathIcon className="h-8 w-8 animate-spin mx-auto mb-4 text-gray-400" />
          <p className="text-gray-600">Loading chart...</p>
        </div>
      </div>
    }>
      <ChartComponent />
    </Suspense>
  );
}
