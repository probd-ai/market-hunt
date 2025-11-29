'use client';

import React, { useState, useRef, useEffect } from 'react';
import Link from 'next/link';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { 
  TrendingUp, 
  Settings, 
  BarChart3, 
  ArrowRight,
  CheckCircle,
  Clock,
  Home,
  Menu,
  X,
  LayoutDashboard,
  ChartBar,
  PieChart,
  TrendingDown
} from 'lucide-react';

// Available indicators
const availableIndicators = [
  {
    id: 'truevx',
    name: 'TrueValueX Ranking',
    description: 'Advanced ranking system with structural and trend analysis comparing stocks against benchmark indices',
    status: 'active',
    features: [
      'Pine Script converted algorithm',
      'Multi-timeframe analysis (Alpha, Beta, Gamma)',
      'Structural and trend scoring',
      'Benchmark comparison (Nifty 50, Nifty 500)',
      'Real-time calculation'
    ],
    parameters: {
      's1': 'Alpha (Short-term): 22 periods',
      'm2': 'Beta (Mid-term): 66 periods', 
      'l3': 'Gamma (Long-term): 222 periods'
    },
    route: '/indicators/truevx'
  },
  // Future indicators can be added here
  {
    id: 'macd',
    name: 'MACD',
    description: 'Moving Average Convergence Divergence - Trend following momentum indicator',
    status: 'coming_soon',
    features: [
      'Fast and slow moving averages',
      'Signal line crossovers',
      'Histogram analysis',
      'Divergence detection'
    ],
    parameters: {
      'fast': 'Fast Period: 12',
      'slow': 'Slow Period: 26',
      'signal': 'Signal Period: 9'
    },
    route: '/indicators/macd'
  },
  {
    id: 'rsi',
    name: 'RSI',
    description: 'Relative Strength Index - Momentum oscillator measuring speed and magnitude of price changes',
    status: 'coming_soon',
    features: [
      'Overbought/oversold levels',
      'Momentum analysis',
      'Divergence patterns',
      'Range: 0-100'
    ],
    parameters: {
      'period': 'Period: 14',
      'overbought': 'Overbought: 70',
      'oversold': 'Oversold: 30'
    },
    route: '/indicators/rsi'
  }
];

const IndicatorsListPage = () => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsMenuOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const navigationItems = [
    {
      name: 'Dashboard',
      href: '/',
      icon: LayoutDashboard,
      description: 'Main dashboard overview'
    },
    {
      name: 'Charts',
      href: '/chart',
      icon: ChartBar,
      description: 'Interactive stock charts'
    },
    {
      name: 'Analytics',
      href: '/analytics',
      icon: PieChart,
      description: 'Market analysis tools'
    }
  ];

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'coming_soon':
        return <Clock className="h-5 w-5 text-yellow-500" />;
      default:
        return <Clock className="h-5 w-5 text-gray-400" />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'active':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
            Active
          </span>
        );
      case 'coming_soon':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
            Coming Soon
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
            Inactive
          </span>
        );
    }
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Navigation Bar */}
      <div className="flex items-center justify-between mb-6">
        {/* Home Button */}
        <Link href="/">
          <Button variant="outline" size="sm" className="flex items-center gap-2">
            <Home className="h-4 w-4" />
            Dashboard
          </Button>
        </Link>

        {/* Navigation Menu Toggle */}
        <div className="relative" ref={menuRef}>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsMenuOpen(!isMenuOpen)}
            className="flex items-center gap-2"
          >
            {isMenuOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
            Navigation
          </Button>

          {/* Dropdown Menu */}
          {isMenuOpen && (
            <div className="absolute right-0 mt-2 w-64 bg-white rounded-lg shadow-lg border z-50">
              <div className="p-2">
                <div className="text-sm font-medium text-gray-700 px-3 py-2 border-b">
                  Quick Navigation
                </div>
                {navigationItems.map((item) => (
                  <Link
                    key={item.name}
                    href={item.href}
                    onClick={() => setIsMenuOpen(false)}
                    className="flex items-center gap-3 px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-md transition-colors"
                  >
                    <item.icon className="h-4 w-4 text-gray-500" />
                    <div>
                      <div className="font-medium">{item.name}</div>
                      <div className="text-xs text-gray-500">{item.description}</div>
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Header */}
      <div className="text-center space-y-4">
        <div className="flex items-center justify-center gap-3">
          <BarChart3 className="h-8 w-8 text-blue-600" />
          <h1 className="text-3xl font-bold">Technical Indicators</h1>
        </div>
        <p className="text-gray-600 max-w-2xl mx-auto">
          Advanced technical analysis tools for Indian stock market. Calculate, store, and analyze 
          indicators for individual stocks or entire portfolios with real-time data processing.
        </p>
      </div>

      {/* Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <Card>
          <CardContent className="p-6 text-center">
            <div className="text-2xl font-bold text-blue-600">1</div>
            <div className="text-sm text-gray-600">Active Indicators</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6 text-center">
            <div className="text-2xl font-bold text-green-600">500+</div>
            <div className="text-sm text-gray-600">Supported Stocks</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6 text-center">
            <div className="text-2xl font-bold text-purple-600">2+ Years</div>
            <div className="text-sm text-gray-600">Historical Data</div>
          </CardContent>
        </Card>
      </div>

      {/* Indicators Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {availableIndicators.map((indicator) => (
          <Card key={indicator.id} className="h-full flex flex-col">
            <CardHeader>
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  {getStatusIcon(indicator.status)}
                  <div>
                    <CardTitle className="text-lg">{indicator.name}</CardTitle>
                    {getStatusBadge(indicator.status)}
                  </div>
                </div>
              </div>
            </CardHeader>
            
            <CardContent className="flex-1 space-y-4">
              <p className="text-gray-600 text-sm leading-relaxed">
                {indicator.description}
              </p>
              
              {/* Features */}
              <div>
                <h4 className="font-medium text-sm text-gray-900 mb-2">Features:</h4>
                <ul className="space-y-1">
                  {indicator.features.slice(0, 3).map((feature, index) => (
                    <li key={index} className="text-xs text-gray-600 flex items-start gap-1">
                      <span className="text-green-500 mt-0.5">•</span>
                      {feature}
                    </li>
                  ))}
                  {indicator.features.length > 3 && (
                    <li className="text-xs text-gray-500">
                      +{indicator.features.length - 3} more features
                    </li>
                  )}
                </ul>
              </div>

              {/* Parameters */}
              <div>
                <h4 className="font-medium text-sm text-gray-900 mb-2">Key Parameters:</h4>
                <div className="space-y-1">
                  {Object.entries(indicator.parameters).slice(0, 2).map(([key, value]) => (
                    <div key={key} className="text-xs text-gray-600">
                      <span className="font-medium">{value}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Action Button */}
              <div className="pt-4">
                {indicator.status === 'active' ? (
                  <Link href={indicator.route}>
                    <Button className="w-full flex items-center justify-center gap-2">
                      <Settings className="h-4 w-4" />
                      Manage Indicator
                      <ArrowRight className="h-4 w-4" />
                    </Button>
                  </Link>
                ) : (
                  <Button 
                    disabled 
                    className="w-full flex items-center justify-center gap-2"
                  >
                    <Clock className="h-4 w-4" />
                    Coming Soon
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Footer Info */}
      <div className="text-center pt-8">
        <div className="inline-flex items-center gap-2 px-4 py-2 bg-blue-50 rounded-lg text-blue-700 text-sm">
          <TrendingUp className="h-4 w-4" />
          More indicators are coming soon. TrueValueX is production-ready and fully operational.
        </div>
      </div>
    </div>
  );
};

export default IndicatorsListPage;
