'use client';

import React, { useState, useRef, useEffect } from 'react';
import Link from 'next/link';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { 
  BarChart3,
  TrendingUp,
  PieChart,
  Activity,
  Calendar,
  Filter,
  Download,
  Play,
  Home,
  Menu,
  X,
  LayoutDashboard,
  ChartBar,
  Settings,
  Sparkles,
  Zap,
  Target,
  Globe,
  Layers
} from 'lucide-react';

// Analytics menu items
const analyticsMenuItems = [
  {
    id: 'index-distribution',
    title: 'Index Score Distribution',
    description: 'Time series analysis of TrueVX score distribution across index constituents over the last 20 years',
    icon: BarChart3,
    route: '/analytics/index-distribution',
    status: 'active',
    features: [
      'Interactive time series visualization',
      'Score range distribution heatmaps',
      'Historical trend analysis (5Y, 10Y, 15Y, 20Y)',
      'Multi-index comparison',
      'Real-time data updates'
    ],
    complexity: 'Advanced',
    estimatedTime: '2-3 minutes',
    dataPoints: '500K+ records'
  },
  {
    id: 'simulator',
    title: 'Strategy Simulator',
    description: 'Create and backtest trading strategies based on TrueValueX indicators with comprehensive portfolio simulation',
    icon: Play,
    route: '/analytics/simulator',
    status: 'active',
    features: [
      'Custom strategy builder with TrueVX rules',
      'Portfolio simulation with rebalancing',
      'Performance vs benchmark comparison',
      'Holdings tracking and visualization',
      'Multiple universe support (NIFTY50/100/500)'
    ],
    complexity: 'Advanced',
    estimatedTime: '3-5 minutes',
    dataPoints: '1M+ records'
  },
  {
    id: 'debug',
    title: 'Simulation Debug Tool',
    description: 'Visual debugging and testing tool for portfolio calculations and rebalancing logic',
    icon: Activity,
    route: '/analytics/debug',
    status: 'active',
    features: [
      'Day-by-day portfolio tracking',
      'Detailed rebalancing logs',
      'Holdings breakdown analysis',
      'Capital preservation verification',
      'Visual spike detection'
    ],
    complexity: 'Developer',
    estimatedTime: '1-2 minutes',
    dataPoints: '10-20 records'
  },
  {
    id: 'sector-performance',
    title: 'Sector Performance Matrix',
    description: 'Advanced sector-wise performance analysis with correlation patterns and momentum indicators',
    icon: PieChart,
    route: '/analytics/sector-performance',
    status: 'coming_soon',
    features: [
      'Dynamic sector correlation matrix',
      'Performance momentum tracking',
      'Risk-return scatter plots',
      'Sector rotation analysis'
    ],
    complexity: 'Expert',
    estimatedTime: '3-5 minutes',
    dataPoints: '250K+ records'
  },
  {
    id: 'market-microstructure',
    title: 'Market Microstructure Analysis',
    description: 'Deep dive into market structure patterns, liquidity flows, and institutional behavior',
    icon: Activity,
    route: '/analytics/market-microstructure',
    status: 'coming_soon',
    features: [
      'Order flow analysis',
      'Liquidity depth mapping',
      'Institutional pattern detection',
      'Volume profile analysis'
    ],
    complexity: 'Expert',
    estimatedTime: '4-6 minutes',
    dataPoints: '1M+ records'
  },
  {
    id: 'risk-attribution',
    title: 'Multi-Factor Risk Attribution',
    description: 'Comprehensive risk factor decomposition with dynamic factor loading analysis',
    icon: Target,
    route: '/analytics/risk-attribution',
    status: 'coming_soon',
    features: [
      'Factor exposure analysis',
      'Risk decomposition charts',
      'Attribution waterfall',
      'Stress testing scenarios'
    ],
    complexity: 'Expert',
    estimatedTime: '5-7 minutes',
    dataPoints: '750K+ records'
  }
];

const AnalyticsPage = () => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [selectedComplexity, setSelectedComplexity] = useState('all');
  const [hoveredCard, setHoveredCard] = useState<string | null>(null);
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
      name: 'Indicators',
      href: '/indicators',
      icon: TrendingUp,
      description: 'Technical indicator management'
    }
  ];

  const getComplexityColor = (complexity: string) => {
    switch (complexity) {
      case 'Advanced':
        return 'bg-blue-100 text-blue-800';
      case 'Expert':
        return 'bg-purple-100 text-purple-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active':
        return <Sparkles className="h-4 w-4 text-green-500" />;
      case 'coming_soon':
        return <Zap className="h-4 w-4 text-yellow-500" />;
      default:
        return <Globe className="h-4 w-4 text-gray-400" />;
    }
  };

  const filteredAnalytics = selectedComplexity === 'all' 
    ? analyticsMenuItems 
    : analyticsMenuItems.filter(item => item.complexity.toLowerCase() === selectedComplexity.toLowerCase());

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
          <div className="relative">
            <BarChart3 className="h-8 w-8 text-purple-600" />
            <Sparkles className="h-4 w-4 text-yellow-400 absolute -top-1 -right-1" />
          </div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-purple-600 to-blue-600 bg-clip-text text-transparent">
            Advanced Analytics
          </h1>
        </div>
        <p className="text-gray-600 max-w-3xl mx-auto">
          Cutting-edge financial analytics with interactive visualizations, real-time data processing, 
          and advanced statistical models for comprehensive market insights.
        </p>
      </div>

      {/* Filter Controls */}
      <div className="flex items-center justify-center gap-4 mb-8">
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-gray-500" />
          <span className="text-sm font-medium text-gray-700">Complexity Level:</span>
        </div>
        <div className="flex gap-2">
          {['all', 'advanced', 'expert'].map((level) => (
            <Button
              key={level}
              variant={selectedComplexity === level ? 'primary' : 'outline'}
              size="sm"
              onClick={() => setSelectedComplexity(level)}
              className="capitalize"
            >
              {level === 'all' ? 'All Levels' : level}
            </Button>
          ))}
        </div>
      </div>

      {/* Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <Card className="relative overflow-hidden">
          <CardContent className="p-6 text-center">
            <div className="absolute inset-0 bg-gradient-to-br from-blue-50 to-blue-100 opacity-50"></div>
            <div className="relative">
              <div className="text-2xl font-bold text-blue-600">4</div>
              <div className="text-sm text-gray-600">Analytics Modules</div>
            </div>
          </CardContent>
        </Card>
        <Card className="relative overflow-hidden">
          <CardContent className="p-6 text-center">
            <div className="absolute inset-0 bg-gradient-to-br from-green-50 to-green-100 opacity-50"></div>
            <div className="relative">
              <div className="text-2xl font-bold text-green-600">2.5M+</div>
              <div className="text-sm text-gray-600">Data Points</div>
            </div>
          </CardContent>
        </Card>
        <Card className="relative overflow-hidden">
          <CardContent className="p-6 text-center">
            <div className="absolute inset-0 bg-gradient-to-br from-purple-50 to-purple-100 opacity-50"></div>
            <div className="relative">
              <div className="text-2xl font-bold text-purple-600">5 Years</div>
              <div className="text-sm text-gray-600">Historical Range</div>
            </div>
          </CardContent>
        </Card>
        <Card className="relative overflow-hidden">
          <CardContent className="p-6 text-center">
            <div className="absolute inset-0 bg-gradient-to-br from-orange-50 to-orange-100 opacity-50"></div>
            <div className="relative">
              <div className="text-2xl font-bold text-orange-600">Real-time</div>
              <div className="text-sm text-gray-600">Updates</div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Analytics Modules Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {filteredAnalytics.map((item) => (
          <div
            key={item.id}
            className="h-full"
            onMouseEnter={() => setHoveredCard(item.id)}
            onMouseLeave={() => setHoveredCard(null)}
          >
            <Card 
              className={`h-full flex flex-col transition-all duration-300 transform hover:scale-105 hover:shadow-xl ${
                hoveredCard === item.id ? 'ring-2 ring-purple-300' : ''
              } ${item.status === 'coming_soon' ? 'opacity-75' : ''}`}
            >
            <CardHeader className="pb-4">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-lg ${
                    item.status === 'active' 
                      ? 'bg-gradient-to-br from-purple-100 to-blue-100' 
                      : 'bg-gray-100'
                  }`}>
                    <item.icon className={`h-6 w-6 ${
                      item.status === 'active' ? 'text-purple-600' : 'text-gray-500'
                    }`} />
                  </div>
                  <div>
                    <CardTitle className="text-lg">{item.title}</CardTitle>
                    <div className="flex items-center gap-2 mt-1">
                      {getStatusIcon(item.status)}
                      <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getComplexityColor(item.complexity)}`}>
                        {item.complexity}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </CardHeader>
            
            <CardContent className="flex-1 flex flex-col">
              <p className="text-gray-600 text-sm mb-4 flex-1">
                {item.description}
              </p>
              
              {/* Features */}
              <div className="space-y-3 mb-4">
                <h4 className="font-medium text-gray-900 text-sm">Key Features:</h4>
                <ul className="space-y-1">
                  {item.features.map((feature, index) => (
                    <li key={index} className="text-xs text-gray-600 flex items-center gap-2">
                      <div className="w-1 h-1 bg-purple-400 rounded-full"></div>
                      {feature}
                    </li>
                  ))}
                </ul>
              </div>

              {/* Metadata */}
              <div className="grid grid-cols-2 gap-4 mb-4 p-3 bg-gray-50 rounded-lg">
                <div>
                  <div className="text-xs text-gray-500">Processing Time</div>
                  <div className="text-sm font-medium text-gray-900">{item.estimatedTime}</div>
                </div>
                <div>
                  <div className="text-xs text-gray-500">Data Volume</div>
                  <div className="text-sm font-medium text-gray-900">{item.dataPoints}</div>
                </div>
              </div>
              
              {/* Action Button */}
              <div className="mt-auto">
                {item.status === 'active' ? (
                  <Link href={item.route}>
                    <Button className="w-full flex items-center gap-2 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700">
                      <Play className="h-4 w-4" />
                      Launch Analysis
                    </Button>
                  </Link>
                ) : (
                  <Button 
                    className="w-full flex items-center gap-2" 
                    variant="outline"
                    disabled
                  >
                    <Layers className="h-4 w-4" />
                    Coming Soon
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>
          </div>
        ))}
      </div>

      {/* Feature Preview */}
      <Card className="mt-8 bg-gradient-to-r from-purple-50 to-blue-50 border-purple-200">
        <CardContent className="p-6">
          <div className="text-center space-y-4">
            <div className="flex items-center justify-center gap-2">
              <Sparkles className="h-5 w-5 text-purple-600" />
              <h3 className="text-lg font-semibold text-purple-800">Advanced Analytics Preview</h3>
              <Sparkles className="h-5 w-5 text-purple-600" />
            </div>
            <p className="text-purple-700 max-w-2xl mx-auto">
              Experience next-generation financial analytics with real-time processing, 
              interactive visualizations, and AI-powered insights. Each module is designed 
              for professional traders, analysts, and portfolio managers.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default AnalyticsPage;
