'use client';

import React, { useEffect, useRef, useState } from 'react';
import { StockPriceData } from '@/types';

// Dynamic import to avoid SSR issues
const createChart = async () => {
  const { createChart: create, ColorType } = await import('lightweight-charts');
  return { create, ColorType };
};

interface TradingViewChartProps {
  data: StockPriceData[];
  symbol: string;
  chartType?: 'candlestick' | 'line' | 'area';
  height?: number;
}

export function TradingViewChart({ 
  data, 
  symbol, 
  chartType = 'candlestick', 
  height = 400 
}: TradingViewChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<any>(null);
  const seriesRef = useRef<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isChartReady, setIsChartReady] = useState(false);

  // Convert StockPriceData to TradingView format
  const formatDataForChart = React.useMemo(() => {
    if (!data || data.length === 0) return [];
    
    const sortedData = [...data].sort((a, b) => 
      new Date(a.date).getTime() - new Date(b.date).getTime()
    );

    return sortedData.map(item => {
      const timestamp = Math.floor(new Date(item.date).getTime() / 1000) as any; // Cast to Time type
      
      if (chartType === 'candlestick') {
        return {
          time: timestamp,
          open: item.open_price,
          high: item.high_price,
          low: item.low_price,
          close: item.close_price,
        };
      } else { // line or area
        return {
          time: timestamp,
          value: item.close_price,
        };
      }
    });
  }, [data, chartType]);

  // Volume data for volume series
  const volumeData = React.useMemo(() => {
    if (!data || data.length === 0) return [];
    
    const sortedData = [...data].sort((a, b) => 
      new Date(a.date).getTime() - new Date(b.date).getTime()
    );

    return sortedData.map(item => ({
      time: Math.floor(new Date(item.date).getTime() / 1000) as any, // Cast to Time type
      value: item.volume,
      color: item.close_price > item.open_price ? '#26a69a' : '#ef5350',
    }));
  }, [data]);

  // Initialize chart once
  useEffect(() => {
    if (!chartContainerRef.current) return;

    const initChart = async () => {
      setIsLoading(true);
      
      try {
        const { create, ColorType } = await createChart();
        
        // Create chart
        const chart = create(chartContainerRef.current!, {
          layout: {
            background: { type: ColorType.Solid, color: 'white' },
            textColor: 'black',
          },
          width: chartContainerRef.current!.clientWidth,
          height: height,
          grid: {
            vertLines: {
              color: '#e1e1e1',
            },
            horzLines: {
              color: '#e1e1e1',
            },
          },
          crosshair: {
            mode: 1 as any,
          },
          rightPriceScale: {
            borderColor: '#cccccc',
          },
          timeScale: {
            borderColor: '#cccccc',
            timeVisible: true,
            secondsVisible: false,
          },
        });

        // Store chart reference
        chartRef.current = chart;
        setIsChartReady(true);
        setIsLoading(false);

        // Handle resize
        const handleResize = () => {
          if (chart && chartContainerRef.current) {
            chart.applyOptions({ 
              width: chartContainerRef.current.clientWidth 
            });
          }
        };

        window.addEventListener('resize', handleResize);

        // Cleanup function
        return () => {
          window.removeEventListener('resize', handleResize);
          if (chart) {
            chart.remove();
          }
          chartRef.current = null;
          seriesRef.current = null;
          setIsChartReady(false);
        };
      } catch (error) {
        console.error('Error initializing chart:', error);
        setIsLoading(false);
      }
    };

    initChart();
  }, [height]); // Only depend on height

  // Update chart data and type
  useEffect(() => {
    if (!chartRef.current || !isChartReady || formatDataForChart.length === 0) return;

    const updateChart = async () => {
      try {
        // Import series types for v5 API
        const { CandlestickSeries, LineSeries, AreaSeries, HistogramSeries } = await import('lightweight-charts');
        
        // Remove existing series if any
        if (seriesRef.current) {
          chartRef.current.removeSeries(seriesRef.current);
        }

        // Create main price series based on chart type using v5 API
        let mainSeries: any;
        
        if (chartType === 'candlestick') {
          mainSeries = chartRef.current.addSeries(CandlestickSeries, {
            upColor: '#26a69a',
            downColor: '#ef5350',
            borderUpColor: '#26a69a',
            borderDownColor: '#ef5350',
            wickUpColor: '#26a69a',
            wickDownColor: '#ef5350',
          });
        } else if (chartType === 'line') {
          mainSeries = chartRef.current.addSeries(LineSeries, {
            color: '#2962FF',
            lineWidth: 2,
          });
        } else { // area
          mainSeries = chartRef.current.addSeries(AreaSeries, {
            lineColor: '#2962FF',
            topColor: '#2962FF',
            bottomColor: 'rgba(41, 98, 255, 0.28)',
          });
        }

        // Add volume series using v5 API
        const volumeSeries = chartRef.current.addSeries(HistogramSeries, {
          color: '#26a69a',
          priceFormat: {
            type: 'volume',
          },
          priceScaleId: 'volume',
        });

        // Set data
        mainSeries.setData(formatDataForChart);
        volumeSeries.setData(volumeData);

        // Auto-fit the chart to data
        chartRef.current.timeScale().fitContent();

        // Store series reference
        seriesRef.current = mainSeries;

      } catch (error) {
        console.error('Error updating chart:', error);
      }
    };

    updateChart();
  }, [formatDataForChart, volumeData, chartType, isChartReady]);

  if (!data || data.length === 0) {
    return (
      <div 
        className="flex items-center justify-center border rounded bg-gray-50"
        style={{ height: `${height}px` }}
      >
        <div className="text-center text-gray-500">
          <div className="text-2xl mb-2">📊</div>
          <div>No data available for {symbol}</div>
          <div className="text-sm mt-1">Select a symbol with historical data</div>
        </div>
      </div>
    );
  }

  return (
    <div className="relative">
      {isLoading && (
        <div 
          className="absolute inset-0 flex items-center justify-center bg-white bg-opacity-75 z-10"
          style={{ height: `${height}px` }}
        >
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
            <div className="mt-2 text-sm text-gray-600">Rendering chart...</div>
          </div>
        </div>
      )}
      
      <div 
        ref={chartContainerRef} 
        className="w-full border rounded"
        style={{ height: `${height}px` }}
      />
      
      {/* Chart Info */}
      <div className="mt-2 text-xs text-gray-500 flex justify-between items-center">
        <div>
          <span className="font-medium">{symbol}</span> • 
          <span className="ml-1">{formatDataForChart.length} data points</span> • 
          <span className="ml-1 capitalize">{chartType} chart</span>
        </div>
        <div className="text-right">
          {data.length > 0 && (
            <span>
              {new Date(data[0].date).toLocaleDateString()} - {new Date(data[data.length - 1].date).toLocaleDateString()}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

export default TradingViewChart;
