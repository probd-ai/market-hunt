'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';

export default function TestStocksPage() {
  const [selectedSymbol, setSelectedSymbol] = useState<string>('');

  // Test basic API call
  const { data: symbolMappings = [], isLoading, error } = useQuery({
    queryKey: ['symbolMappings'],
    queryFn: () => apiClient.getSymbolMappings(),
  });

  if (isLoading) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-bold mb-4">Stock Data Management (Test)</h1>
        <div>Loading...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-bold mb-4">Stock Data Management (Test)</h1>
        <div className="text-red-600">Error: {error.message}</div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">Stock Data Management (Test)</h1>
      
      <Card className="p-6 mb-6">
        <h2 className="text-xl font-semibold mb-4">Basic Info</h2>
        <p>Total symbols loaded: {symbolMappings.length}</p>
        <Button 
          onClick={() => console.log('Button clicked', symbolMappings.slice(0, 3))}
          className="mt-4"
        >
          Test Button
        </Button>
      </Card>

      <Card className="p-6">
        <h2 className="text-xl font-semibold mb-4">First 5 Symbols</h2>
        <div className="space-y-2">
          {symbolMappings.slice(0, 5).map((symbol) => (
            <div key={symbol._id} className="p-2 border rounded">
              <div className="font-medium">{symbol.symbol}</div>
              <div className="text-sm text-gray-600">{symbol.company_name}</div>
              <div className="text-xs text-gray-500">
                Indices: {symbol.index_names?.join(', ') || 'N/A'}
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
