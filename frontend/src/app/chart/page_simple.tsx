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
  const [error, setError] = useState<string | null>(null);
  const [chartData, setChartData] = useState<ChartData[]>([]);
  const [dataInfo, setDataInfo] = useState<string>('');

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
        chartRef.current.remove();
      }
    };
  }, []);

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

  // Fetch and load chart data
  const loadChartData = async (symbol: string) => {
    setIsLoading(true);
    setError(null);

    try {
      console.log(`Loading data for ${symbol}...`);
      const response = await apiClient.getStockData(symbol, undefined, undefined, 1000);
      console.log(`API Response:`, response);
      
      const transformedData = transformData(response.data || []);
      console.log(`Transformed ${transformedData.length} records`);
      
      if (transformedData.length === 0) {
        setError(`No historical data available for ${symbol}`);
        return;
      }

      setChartData(transformedData);
      setDataInfo(`Showing ${transformedData.length} of ${response.total_records || transformedData.length} records`);
      
      if (seriesRef.current) {
        console.log(`Setting data to chart...`);
        seriesRef.current.setData(transformedData);
        // Fit content to show all data
        if (chartRef.current) {
          chartRef.current.timeScale().fitContent();
        }
      }
    } catch (err: any) {
      console.error('Error loading chart data:', err);
      setError(`Failed to load data for ${symbol}: ${err.message}`);
    } finally {
      setIsLoading(false);
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
            {dataInfo && (
              <div className="text-sm text-gray-500">
                {dataInfo}
              </div>
            )}
            {isLoading && (
              <div className="flex items-center text-sm text-gray-500">
                <ArrowPathIcon className="h-4 w-4 animate-spin mr-1" />
                Loading...
              </div>
            )}
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
