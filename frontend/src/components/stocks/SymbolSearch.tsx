'use client';

import { useState } from 'react';
import { SymbolMapping } from '@/types';
import { Input } from '@/components/ui/Input';
import { MagnifyingGlassIcon } from '@heroicons/react/24/outline';

interface SymbolSearchProps {
  symbols: SymbolMapping[];
  onSelect: (symbol: string) => void;
  selectedSymbol?: string;
}

export function SymbolSearch({ symbols, onSelect, selectedSymbol }: SymbolSearchProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [isOpen, setIsOpen] = useState(false);

  const filteredSymbols = symbols.filter(symbol =>
    symbol.symbol.toLowerCase().includes(searchTerm.toLowerCase()) ||
    symbol.company_name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleSelect = (symbol: string) => {
    onSelect(symbol);
    setSearchTerm('');
    setIsOpen(false);
  };

  return (
    <div className="relative">
      <div className="relative">
        <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
        <Input
          type="text"
          placeholder="Search symbols (e.g., RELIANCE, TCS)..."
          value={searchTerm}
          onChange={(e) => {
            setSearchTerm(e.target.value);
            setIsOpen(e.target.value.length > 0);
          }}
          onFocus={() => setIsOpen(searchTerm.length > 0)}
          className="pl-10"
        />
      </div>

      {isOpen && filteredSymbols.length > 0 && (
        <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-auto">
          {filteredSymbols.slice(0, 10).map((symbol) => (
            <button
              key={symbol._id}
              onClick={() => handleSelect(symbol.symbol)}
              className="w-full px-4 py-2 text-left hover:bg-gray-50 focus:bg-gray-50 focus:outline-none border-b border-gray-100 last:border-b-0"
            >
              <div className="flex justify-between items-center">
                <div>
                  <div className="font-medium text-gray-900">{symbol.symbol}</div>
                  <div className="text-sm text-gray-500 truncate">{symbol.company_name}</div>
                </div>
                <div className="text-xs text-gray-400">
                  {symbol.index_names.slice(0, 2).join(', ')}
                  {symbol.index_names.length > 2 && '...'}
                </div>
              </div>
            </button>
          ))}
          {filteredSymbols.length > 10 && (
            <div className="px-4 py-2 text-sm text-gray-500 text-center">
              {filteredSymbols.length - 10} more results...
            </div>
          )}
        </div>
      )}

      {selectedSymbol && (
        <div className="mt-2 text-sm text-gray-600">
          Selected: <span className="font-medium">{selectedSymbol}</span>
        </div>
      )}
    </div>
  );
}
