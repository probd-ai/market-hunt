'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import { SymbolMapping, StockDataStatistics, DownloadStockDataRequest } from '@/types';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { StockChart } from '@/components/stocks/StockChart';
import { SymbolSearch } from '@/components/stocks/SymbolSearch';
import { CurrencyDollarIcon } from '@heroicons/react/24/outline';

export default function DebugStocksPage() {
  const [selectedSymbol, setSelectedSymbol] = useState<string>('');

  // Test basic API call
  const { data: symbolMappings = [], isLoading, error } = useQuery({
    queryKey: ['symbolMappings'],
    queryFn: () => apiClient.getSymbolMappings(),
  });

  if (isLoading) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-bold mb-4">Stock Data Management (Debug - Step 1)</h1>
        <div>Loading...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-bold mb-4">Stock Data Management (Debug - Step 1)</h1>
        <div className="text-red-600">Error: {error.message}</div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">Stock Data Management (Debug - Step 1)</h1>
      
      <Card className="p-6 mb-6">
        <h2 className="text-xl font-semibold mb-4">Basic + Types + Input + StockChart + SymbolSearch Passed</h2>
        <p>Total symbols loaded: {symbolMappings.length}</p>
        <SymbolSearch 
          symbols={symbolMappings} 
          onSelect={(symbol) => setSelectedSymbol(symbol)} 
        />
        <Input 
          type="text" 
          placeholder="Test input" 
          value={selectedSymbol}
          onChange={(e) => setSelectedSymbol(e.target.value)}
          className="mb-4"
        />
        <StockChart data={[]} symbol="TEST" />
        <Button 
          onClick={() => console.log('Button clicked', symbolMappings.slice(0, 3))}
          className="mt-4"
        >
          Next: Add Heroicons
        </Button>
      </Card>
    </div>
  );
}
