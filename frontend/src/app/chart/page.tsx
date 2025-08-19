'use client';

import { useEffect, useRef, useState, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { createChart, ColorType, IChartApi, ISeriesApi, CandlestickData, UTCTimestamp, CandlestickSeries } from 'lightweight-charts';
import { apiClient } from '@/lib/api';

interface StockData {
  symbol: string;
  date: string;
  open_price: number;
  high_price: number;
  low_price: number;
  close_price: number;
  volume: number;
}

interface StockMapping {
  symbol: string;
  company_name: string;
  industry: string;
}

type TimeframeType = '1Y' | '5Y' | 'ALL';

interface TimeframeOption {
  label: string;
  value: TimeframeType;
  aggregation: 'daily' | 'weekly' | 'monthly';
}

const timeframeOptions: TimeframeOption[] = [
  { label: '1Y (Daily)', value: '1Y', aggregation: 'daily' },
  { label: '5Y (Weekly)', value: '5Y', aggregation: 'weekly' },
  { label: 'ALL (Monthly)', value: 'ALL', aggregation: 'monthly' }
];

function ChartPageContent() {
  const searchParams = useSearchParams();
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chart = useRef<IChartApi | null>(null);
  const candlestickSeries = useRef<ISeriesApi<"Candlestick"> | null>(null);
  
  const [symbol, setSymbol] = useState(searchParams.get('symbol') || 'LT');
  const [searchSymbol, setSearchSymbol] = useState('');
  const [timeframe, setTimeframe] = useState<TimeframeType>('1Y');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dataCount, setDataCount] = useState(0);
  
  // Autocomplete states
  const [stockSymbols, setStockSymbols] = useState<StockMapping[]>([]);
  const [filteredSymbols, setFilteredSymbols] = useState<StockMapping[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [symbolsLoading, setSymbolsLoading] = useState(false);

  // Load available stock symbols
  useEffect(() => {
    const loadSymbols = async () => {
      setSymbolsLoading(true);
      try {
        const result = await apiClient.getStockMappings();
        if (result && result.mappings) {
          setStockSymbols(result.mappings);
          console.log(`Loaded ${result.mappings.length} stock symbols`);
        }
      } catch (err) {
        console.error('Error loading stock symbols:', err);
      } finally {
        setSymbolsLoading(false);
      }
    };
    
    loadSymbols();
  }, []);

  // Initialize chart
  useEffect(() => {
    if (!chartContainerRef.current) return;

    chart.current = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: '#000000' },
        textColor: '#ffffff',
      },
      grid: {
        vertLines: { color: '#2B2B43' },
        horzLines: { color: '#2B2B43' },
      },
      crosshair: {
        mode: 1,
      },
      rightPriceScale: {
        borderColor: '#2B2B43',
      },
      timeScale: {
        borderColor: '#2B2B43',
        timeVisible: true,
        secondsVisible: false,
      },
      width: chartContainerRef.current.clientWidth,
      height: chartContainerRef.current.clientHeight,
    });

    candlestickSeries.current = chart.current.addSeries(CandlestickSeries, {
      upColor: '#26a69a',
      downColor: '#ef5350',
      borderVisible: false,
      wickUpColor: '#26a69a',
      wickDownColor: '#ef5350',
    });

    // Handle resize
    const handleResize = () => {
      if (chart.current && chartContainerRef.current) {
        chart.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
          height: chartContainerRef.current.clientHeight,
        });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      if (chart.current) {
        chart.current.remove();
      }
    };
  }, []);

  // Load data
  const loadData = async (symbolToLoad: string, selectedTimeframe: TimeframeType) => {
    if (!candlestickSeries.current) {
      console.error('Candlestick series not initialized');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const timeframeConfig = timeframeOptions.find(opt => opt.value === selectedTimeframe);
      if (!timeframeConfig) throw new Error('Invalid timeframe');

      // Calculate date range based on timeframe
      const endDate = new Date();
      let startDate = new Date();
      
      if (selectedTimeframe === '1Y') {
        startDate.setFullYear(endDate.getFullYear() - 1);
      } else if (selectedTimeframe === '5Y') {
        startDate.setFullYear(endDate.getFullYear() - 5);
      } else {
        // ALL - start from 2005
        startDate = new Date('2005-01-01');
      }

      console.log(`Loading ${symbolToLoad} data from ${startDate.toISOString().split('T')[0]} to ${endDate.toISOString().split('T')[0]} with ${timeframeConfig.aggregation} aggregation`);

      const result = await apiClient.getStockData(
        symbolToLoad,
        startDate.toISOString().split('T')[0],
        endDate.toISOString().split('T')[0],
        50000 // Large limit to get all data
      );

      console.log('API Response:', result);

      if (!result || !Array.isArray(result.data)) {
        console.error('Invalid response format:', result);
        throw new Error('Invalid response format');
      }

      if (result.data.length === 0) {
        throw new Error(`No data found for symbol ${symbolToLoad}`);
      }

      console.log('Sample data item:', result.data[0]);

      // Transform data for TradingView
      const chartData: CandlestickData<UTCTimestamp>[] = result.data
        .map((item: StockData) => ({
          time: (new Date(item.date).getTime() / 1000) as UTCTimestamp,
          open: item.open_price,
          high: item.high_price,
          low: item.low_price,
          close: item.close_price,
        }))
        .sort((a, b) => (a.time as number) - (b.time as number)); // Ensure ascending order

      console.log(`Processed ${chartData.length} data points for ${symbolToLoad}`);
      console.log('Sample chart data:', chartData.slice(0, 3));
      
      // Remove duplicate timestamps
      const uniqueData: CandlestickData<UTCTimestamp>[] = [];
      const seenTimes = new Set();
      
      for (const item of chartData) {
        if (!seenTimes.has(item.time)) {
          seenTimes.add(item.time);
          uniqueData.push(item);
        }
      }

      if (uniqueData.length !== chartData.length) {
        console.warn(`Removed ${chartData.length - uniqueData.length} duplicate timestamps`);
      }

      console.log('Setting chart data:', uniqueData.length, 'items');
      
      if (candlestickSeries.current) {
        candlestickSeries.current.setData(uniqueData);
        console.log('Chart data set successfully');
      }
        
      if (chart.current) {
        chart.current.timeScale().fitContent();
        console.log('Chart fitted to content');
      }
      
      setDataCount(uniqueData.length);

    } catch (err) {
      console.error('Error loading data:', err);
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  // Load data when symbol or timeframe changes
  useEffect(() => {
    if (symbol) {
      loadData(symbol, timeframe);
    }
  }, [symbol, timeframe]);

  // Filter symbols based on search input
  useEffect(() => {
    if (searchSymbol.length > 0) {
      const filtered = stockSymbols.filter(stock => 
        stock.symbol.toLowerCase().includes(searchSymbol.toLowerCase()) ||
        stock.company_name.toLowerCase().includes(searchSymbol.toLowerCase())
      ).slice(0, 10); // Limit to 10 results
      setFilteredSymbols(filtered);
      setShowDropdown(filtered.length > 0);
    } else {
      setFilteredSymbols([]);
      setShowDropdown(false);
    }
  }, [searchSymbol, stockSymbols]);

  const handleSearch = () => {
    if (searchSymbol.trim()) {
      const trimmedSymbol = searchSymbol.trim().toUpperCase();
      setSymbol(trimmedSymbol);
      setSearchSymbol('');
      setShowDropdown(false);
    }
  };

  const handleSymbolSelect = (selectedSymbol: string) => {
    setSymbol(selectedSymbol);
    setSearchSymbol('');
    setShowDropdown(false);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    } else if (e.key === 'Escape') {
      setShowDropdown(false);
    }
  };

  return (
    <div className="w-full h-screen bg-black flex flex-col">
      {/* Header Controls */}
      <div className="flex items-center justify-between p-4 bg-gray-900 border-b border-gray-700">
        <div className="flex items-center space-x-4">
          <h1 className="text-white text-xl font-bold">
            {symbol} - Stock Chart
            {dataCount > 0 && (
              <span className="text-sm text-gray-400 ml-2">
                ({dataCount.toLocaleString()} records)
              </span>
            )}
            {symbolsLoading && (
              <span className="text-sm text-blue-400 ml-2">
                (Loading symbols...)
              </span>
            )}
          </h1>
        </div>
        
        <div className="flex items-center space-x-4">
          {/* Symbol Search with Autocomplete */}
          <div className="relative">
            <div className="flex items-center space-x-2">
              <input
                type="text"
                value={searchSymbol}
                onChange={(e) => setSearchSymbol(e.target.value)}
                onKeyPress={handleKeyPress}
                onFocus={() => {
                  if (filteredSymbols.length > 0) {
                    setShowDropdown(true);
                  }
                }}
                onBlur={() => {
                  // Delay hiding dropdown to allow clicks on dropdown items
                  setTimeout(() => setShowDropdown(false), 200);
                }}
                placeholder="Search symbol or company name..."
                className="w-64 px-3 py-2 bg-gray-800 text-white border border-gray-600 rounded focus:outline-none focus:border-blue-500"
                disabled={symbolsLoading}
              />
              <button
                onClick={handleSearch}
                disabled={loading || symbolsLoading || !searchSymbol.trim()}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Loading...' : 'Search'}
              </button>
            </div>
            
            {/* Autocomplete Dropdown */}
            {showDropdown && filteredSymbols.length > 0 && (
              <div className="absolute top-full left-0 right-0 mt-1 bg-gray-800 border border-gray-600 rounded shadow-lg z-50 max-h-60 overflow-y-auto">
                {filteredSymbols.map((stock) => (
                  <div
                    key={stock.symbol}
                    onClick={() => handleSymbolSelect(stock.symbol)}
                    className="px-4 py-3 hover:bg-gray-700 cursor-pointer border-b border-gray-700 last:border-b-0"
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <div className="text-white font-medium">{stock.symbol}</div>
                        <div className="text-gray-400 text-sm truncate max-w-xs">
                          {stock.company_name}
                        </div>
                      </div>
                      <div className="text-gray-500 text-xs ml-2 shrink-0">
                        {stock.industry}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Timeframe Buttons */}
          <div className="flex space-x-2">
            {timeframeOptions.map((option) => (
              <button
                key={option.value}
                onClick={() => setTimeframe(option.value)}
                className={`px-3 py-2 rounded text-sm font-medium transition-colors ${
                  timeframe === option.value
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                }`}
                disabled={loading}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Loading/Error States */}
      {loading && (
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-white text-lg">
          Loading {symbol} data...
        </div>
      )}

      {error && (
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-red-500 text-lg text-center">
          <div className="bg-gray-900 p-4 rounded border border-red-500">
            <div className="font-bold">Error loading data:</div>
            <div>{error}</div>
          </div>
        </div>
      )}

      {/* Chart Container */}
      <div 
        ref={chartContainerRef}
        className="flex-1 w-full"
        style={{ minHeight: '500px' }}
      />
    </div>
  );
}

export default function ChartPage() {
  return (
    <Suspense fallback={
      <div className="w-full h-screen bg-black flex items-center justify-center">
        <div className="text-white text-lg">Loading chart...</div>
      </div>
    }>
      <ChartPageContent />
    </Suspense>
  );
}
