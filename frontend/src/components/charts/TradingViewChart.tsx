import { createChart, ColorType, CandlestickSeries } from 'lightweight-charts';
import React, { useEffect, useRef } from 'react';

interface StockData {
  date: string;
  open_price: number;
  high_price: number;
  low_price: number;
  close_price: number;
  volume: number;
}

interface TradingViewChartProps {
  data: StockData[];
  symbol?: string;
  chartType?: 'candlestick' | 'line' | 'area';
  height?: number;
  colors?: {
    backgroundColor?: string;
    lineColor?: string;
    textColor?: string;
    upColor?: string;
    downColor?: string;
    borderUpColor?: string;
    borderDownColor?: string;
    wickUpColor?: string;
    wickDownColor?: string;
  };
}

export const TradingViewChart: React.FC<TradingViewChartProps> = (props) => {
  const {
    data,
    symbol,
    chartType = 'candlestick',
    height = 400,
    colors: {
      backgroundColor = 'white',
      textColor = 'black',
      upColor = '#26a69a',
      downColor = '#ef5350',
      borderUpColor = '#26a69a',
      borderDownColor = '#ef5350',
      wickUpColor = '#26a69a',
      wickDownColor = '#ef5350',
    } = {},
  } = props;

  const chartContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    console.log('🔄 TradingViewChart useEffect triggered:', {
      hasContainer: !!chartContainerRef.current,
      hasData: !!data,
      dataLength: data?.length || 0,
      symbol,
      chartType,
      height
    });

    if (!chartContainerRef.current || !data || data.length === 0) {
      console.log('❌ TradingViewChart: Missing requirements', {
        hasContainer: !!chartContainerRef.current,
        hasData: !!data,
        dataLength: data?.length || 0
      });
      return;
    }

    const handleResize = () => {
      if (chartContainerRef.current && chart) {
        chart.applyOptions({ width: chartContainerRef.current.clientWidth });
      }
    };

    // Create the chart
    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: backgroundColor },
        textColor,
      },
      width: chartContainerRef.current.clientWidth,
      height: height,
      grid: {
        vertLines: {
          color: 'rgba(197, 203, 206, 0.5)',
        },
        horzLines: {
          color: 'rgba(197, 203, 206, 0.5)',
        },
      },
      crosshair: {
        mode: 1,
      },
      rightPriceScale: {
        borderColor: 'rgba(197, 203, 206, 0.8)',
      },
      timeScale: {
        borderColor: 'rgba(197, 203, 206, 0.8)',
      },
    });

    // Add candlestick series
    const candlestickSeries = chart.addSeries(CandlestickSeries, {
      upColor: upColor,
      downColor: downColor,
      borderUpColor: borderUpColor,
      borderDownColor: borderDownColor,
      wickUpColor: wickUpColor,
      wickDownColor: wickDownColor,
    });

    // Transform data to match lightweight-charts format
    // Transform data for chart
    const chartData = data?.map((item: StockData) => ({
      time: new Date(item.date).toISOString().split('T')[0], // Convert to yyyy-mm-dd format
      open: item.open_price,
      high: item.high_price,
      low: item.low_price,
      close: item.close_price,
    })) || [];
    
    // Sort data by date to ensure proper ordering
    chartData.sort((a: any, b: any) => new Date(a.time).getTime() - new Date(b.time).getTime());

    console.log('📊 Chart data prepared:', {
      totalPoints: chartData.length,
      firstPoint: chartData[0],
      lastPoint: chartData[chartData.length - 1],
      sampleData: chartData.slice(0, 3)
    });

    // Set data to the series
    candlestickSeries.setData(chartData);
    console.log('✅ Chart data set successfully');

    // Fit content to show all data
    chart.timeScale().fitContent();
    console.log('✅ Chart fitted to content');

    // Add resize listener
    window.addEventListener('resize', handleResize);

    // Cleanup function
    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [data, backgroundColor, textColor, upColor, downColor, borderUpColor, borderDownColor, wickUpColor, wickDownColor, height]);

  return <div ref={chartContainerRef} style={{ width: '100%', height: `${height}px` }} />;
};

export default TradingViewChart;
