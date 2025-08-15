'use client';

import { useMemo } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { StockPriceData } from '@/types';

interface StockChartProps {
  data: StockPriceData[];
  symbol: string;
}

export function StockChart({ data, symbol }: StockChartProps) {
  const chartData = useMemo(() => {
    return data
      .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())
      .map(record => ({
        date: new Date(record.date).toLocaleDateString(),
        close: record.close_price,
        open: record.open_price,
        high: record.high_price,
        low: record.low_price,
        volume: record.volume,
      }));
  }, [data]);

  if (!data.length) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500">
        No data available for chart
      </div>
    );
  }

  return (
    <div className="h-64">
      <h3 className="text-lg font-semibold mb-4">{symbol} Price Chart</h3>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis 
            dataKey="date" 
            tick={{ fontSize: 12 }}
            interval="preserveStartEnd"
          />
          <YAxis 
            tick={{ fontSize: 12 }}
            domain={['dataMin - 10', 'dataMax + 10']}
          />
          <Tooltip 
            formatter={(value: number, name: string) => [
              `₹${value.toFixed(2)}`,
              name.charAt(0).toUpperCase() + name.slice(1)
            ]}
            labelFormatter={(label) => `Date: ${label}`}
          />
          <Line 
            type="monotone" 
            dataKey="close" 
            stroke="#2563eb" 
            strokeWidth={2}
            dot={false}
            name="close"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
