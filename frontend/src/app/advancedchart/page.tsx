'use client';

import { useEffect, useRef, useState, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { createChart, ColorType, IChartApi, ISeriesApi, CandlestickData, UTCTimestamp, CandlestickSeries, LineData, LineSeries } from 'lightweight-charts';
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

interface IndicatorData {
  date: string;
  value: number;
  indicator: string;
  period: number;
  price_field: string;
}

interface StockMapping {
  symbol: string;
  company_name: string;
  industry: string;
}

type TimeframeType = '1Y' | '5Y' | 'ALL';
type IndicatorType = 'sma';

interface TimeframeOption {
  label: string;
  value: TimeframeType;
  aggregation: 'daily' | 'weekly' | 'monthly';
}

interface IndicatorConfig {
  type: IndicatorType;
  period: number;
  enabled: boolean;
  color: string;
}

const timeframeOptions: TimeframeOption[] = [
  { label: '1Y (Daily)', value: '1Y', aggregation: 'daily' },
  { label: '5Y (Weekly)', value: '5Y', aggregation: 'weekly' },
  { label: 'ALL (Monthly)', value: 'ALL', aggregation: 'monthly' }
];

function AdvancedChartPageContent() {
  const searchParams = useSearchParams();
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chart = useRef<IChartApi | null>(null);
  const candlestickSeries = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const indicatorSeries = useRef<ISeriesApi<"Line">[]>([]);
  
  const [symbol, setSymbol] = useState(searchParams.get('symbol') || 'LT');
  const [searchSymbol, setSearchSymbol] = useState('');
  const [timeframe, setTimeframe] = useState<TimeframeType>('1Y');
  const [loading, setLoading] = useState(false);
  const [indicatorLoading, setIndicatorLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dataCount, setDataCount] = useState(0);
  
  // Indicator configuration
  const [indicators, setIndicators] = useState<IndicatorConfig[]>([
    { type: 'sma', period: 5, enabled: false, color: '#ff6b6b' },
    { type: 'sma', period: 20, enabled: false, color: '#4ecdc4' },
    { type: 'sma', period: 50, enabled: false, color: '#45b7d1' },
  ]);
  
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

  // Load stock data
  const loadStockData = async (symbolToLoad: string, selectedTimeframe: TimeframeType) => {
    if (!candlestickSeries.current) {
      console.error('Candlestick series not initialized');
      return [];
    }

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

      console.log('Stock API Response:', result);

      if (!result || !Array.isArray(result.data)) {
        console.error('Invalid response format:', result);
        throw new Error('Invalid response format');
      }

      if (result.data.length === 0) {
        throw new Error(`No data found for symbol ${symbolToLoad}`);
      }

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
      return result.data;

    } catch (err) {
      console.error('Error loading stock data:', err);
      throw err;
    }
  };

  // Load indicator data with performance optimizations
  const loadIndicatorData = async (symbolToLoad: string, indicator: IndicatorConfig) => {
    if (!chart.current) return;

    try {
      console.log(`Loading ${indicator.type} indicator for ${symbolToLoad} with period ${indicator.period}`);
      
      const startTime = performance.now();
      
      // Calculate date range based on timeframe (same as stock data)
      const endDate = new Date();
      let startDate = new Date();
      
      if (timeframe === '1Y') {
        startDate.setFullYear(endDate.getFullYear() - 1);
      } else if (timeframe === '5Y') {
        startDate.setFullYear(endDate.getFullYear() - 5);
      } else {
        // ALL - start from 2005 (same as stock data)
        startDate = new Date('2005-01-01');
      }
      
      const response = await fetch('http://localhost:3001/api/stock/indicators', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          symbol: symbolToLoad,
          indicator_type: indicator.type,
          period: indicator.period,
          price_field: 'close_price',
          start_date: startDate.toISOString().split('T')[0],
          end_date: endDate.toISOString().split('T')[0]
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch indicator data: ${response.statusText}`);
      }

      const result = await response.json();
      
      const loadTime = performance.now() - startTime;
      console.log(`Indicator API Response (${loadTime.toFixed(0)}ms):`, {
        total_points: result.total_points,
        calculation_time: result.calculation_time_seconds,
        data_sample: result.data?.slice(0, 2)
      });

      if (!result || !Array.isArray(result.data)) {
        throw new Error('Invalid indicator response format');
      }

      // Transform indicator data for TradingView
      const rawIndicatorData: LineData<UTCTimestamp>[] = result.data
        .map((item: IndicatorData) => ({
          time: (new Date(item.date).getTime() / 1000) as UTCTimestamp,
          value: item.value,
        }))
        .sort((a, b) => (a.time as number) - (b.time as number));

      // Remove duplicate timestamps to prevent TradingView errors
      const indicatorChartData: LineData<UTCTimestamp>[] = [];
      const seenTimes = new Set();
      
      for (const item of rawIndicatorData) {
        if (!seenTimes.has(item.time)) {
          seenTimes.add(item.time);
          indicatorChartData.push(item);
        }
      }

      if (indicatorChartData.length !== rawIndicatorData.length) {
        console.warn(`Removed ${rawIndicatorData.length - indicatorChartData.length} duplicate timestamps from indicator data`);
      }

      console.log(`Processed ${indicatorChartData.length} indicator points in ${loadTime.toFixed(0)}ms`);

      // Create line series for this indicator
      const lineSeries = chart.current.addSeries(LineSeries, {
        color: indicator.color,
        lineWidth: 2,
        title: `${indicator.type.toUpperCase()}(${indicator.period})`,
      });

      lineSeries.setData(indicatorChartData);
      indicatorSeries.current.push(lineSeries);

    } catch (err) {
      console.error('Error loading indicator data:', err);
      throw err;
    }
  };

  // Clear all indicators
  const clearIndicators = () => {
    if (chart.current) {
      indicatorSeries.current.forEach(series => {
        chart.current?.removeSeries(series);
      });
      indicatorSeries.current = [];
    }
  };

  // Load data when symbol or timeframe changes
  const loadData = async () => {
    if (!symbol) return;

    setLoading(true);
    setError(null);

    try {
      // Clear existing indicators
      clearIndicators();

      // Load stock data first
      await loadStockData(symbol, timeframe);

      // Load enabled indicators
      setIndicatorLoading(true);
      const enabledIndicators = indicators.filter(ind => ind.enabled);
      
      for (const indicator of enabledIndicators) {
        await loadIndicatorData(symbol, indicator);
      }

    } catch (err) {
      console.error('Error loading data:', err);
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setLoading(false);
      setIndicatorLoading(false);
    }
  };

  // Load data when symbol, timeframe, or indicators change
  useEffect(() => {
    loadData();
  }, [symbol, timeframe]);

  // Reload indicators when configuration changes (with debouncing)
  useEffect(() => {
    if (!loading && symbol) {
      // Debounce indicator changes to prevent too many API calls
      const timeoutId = setTimeout(() => {
        setIndicatorLoading(true);
        
        // Clear existing indicators
        clearIndicators();

        // Load enabled indicators
        const enabledIndicators = indicators.filter(ind => ind.enabled);
        
        if (enabledIndicators.length === 0) {
          setIndicatorLoading(false);
          return;
        }
        
        Promise.all(
          enabledIndicators.map(indicator => loadIndicatorData(symbol, indicator))
        ).catch(err => {
          console.error('Error loading indicators:', err);
          setError(err instanceof Error ? err.message : 'Failed to load indicators');
        }).finally(() => {
          setIndicatorLoading(false);
        });
      }, 300); // 300ms debounce
      
      return () => clearTimeout(timeoutId);
    }
  }, [indicators]);

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

  const toggleIndicator = (index: number) => {
    setIndicators(prev => 
      prev.map((ind, i) => 
        i === index ? { ...ind, enabled: !ind.enabled } : ind
      )
    );
  };

  const updateIndicatorPeriod = (index: number, period: number) => {
    setIndicators(prev => 
      prev.map((ind, i) => 
        i === index ? { ...ind, period } : ind
      )
    );
  };

  return (
    <div className="w-full h-screen bg-black flex flex-col">
      {/* Header Controls */}
      <div className="flex items-center justify-between p-4 bg-gray-900 border-b border-gray-700">
        <div className="flex items-center space-x-4">
          <h1 className="text-white text-xl font-bold">
            {symbol} - Advanced Chart
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
            {indicatorLoading && (
              <span className="text-sm text-orange-400 ml-2">
                (Loading indicators...)
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

      {/* Indicator Controls */}
      <div className="flex items-center space-x-4 p-3 bg-gray-800 border-b border-gray-700">
        <span className="text-white text-sm font-medium">Indicators:</span>
        {indicators.map((indicator, index) => (
          <div key={index} className="flex items-center space-x-2">
            <label className="flex items-center space-x-2 cursor-pointer">
              <input
                type="checkbox"
                checked={indicator.enabled}
                onChange={() => toggleIndicator(index)}
                className="rounded"
                disabled={loading || indicatorLoading}
              />
              <span className="text-white text-sm">
                {indicator.type.toUpperCase()}
              </span>
            </label>
            <input
              type="number"
              min="1"
              max="200"
              value={indicator.period}
              onChange={(e) => updateIndicatorPeriod(index, parseInt(e.target.value) || 1)}
              disabled={loading || indicatorLoading}
              className="w-16 px-2 py-1 bg-gray-700 text-white border border-gray-600 rounded text-sm"
            />
            <div 
              className="w-4 h-4 rounded"
              style={{ backgroundColor: indicator.color }}
            />
          </div>
        ))}
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

export default function AdvancedChartPage() {
  return (
    <Suspense fallback={
      <div className="w-full h-screen bg-black flex items-center justify-center">
        <div className="text-white text-lg">Loading advanced chart...</div>
      </div>
    }>
      <AdvancedChartPageContent />
    </Suspense>
  );
}
