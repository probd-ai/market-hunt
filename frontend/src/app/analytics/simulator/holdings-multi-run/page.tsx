'use client';

import React, { useState, useEffect, Suspense, useMemo } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, Cell, Legend } from 'recharts';
import { 
  TrendingUp,
  TrendingDown,
  ArrowLeft,
  Activity,
  Target,
  DollarSign,
  Calendar,
  BarChart3,
  Shuffle,
  CheckCircle,
  AlertCircle
} from 'lucide-react';

// Types
interface SimulationParams {
  strategyId: string;
  portfolioValue: number;
  rebalanceFreq: 'monthly' | 'weekly' | 'dynamic';
  rebalanceDate: 'first' | 'last' | 'mid';
  rebalanceType: 'equal_weight' | 'skewed';
  universe: 'NIFTY50' | 'NIFTY100' | 'NIFTY500';
  benchmarkSymbol?: string;
  maxHoldings: number;
  momentumRanking: string;
  startDate: string;
  endDate: string;
}

interface HoldingResult {
  holding_size: number;
  total_return: number;
  benchmark_return: number;
  alpha: number;
  max_drawdown: number;
  sharpe_ratio: number;
  volatility: number;
  total_trades: number;
  avg_monthly_churn: number;
  monthly_win_rate: number;
  final_portfolio_value: number;
  days_count: number;
  monthly_returns: number[];
  portfolio_values: { date: string; value: number; benchmark: number }[];
  status: 'completed' | 'running' | 'error';
  error_message?: string;
}

interface MultiHoldingsResult {
  params: SimulationParams;
  holdings_results: HoldingResult[];
  aggregate_metrics: {
    average_return: number;
    average_alpha: number;
    average_sharpe: number;
    best_holding_size: number;
    worst_holding_size: number;
    optimal_risk_adjusted: number;
  };
}

const HoldingsMultiRunContent = () => {
  const searchParams = useSearchParams();
  const [simulationParams, setSimulationParams] = useState<SimulationParams | null>(null);
  const [multiResults, setMultiResults] = useState<MultiHoldingsResult | null>(null);
  const [selectedHolding, setSelectedHolding] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const paramsString = searchParams?.get('params');
    if (paramsString) {
      try {
        const params = JSON.parse(decodeURIComponent(paramsString));
        setSimulationParams(params);
        runMultiHoldingsSimulation(params);
      } catch (e) {
        setError('Failed to parse simulation parameters');
      }
    }
  }, [searchParams]);

  const runMultiHoldingsSimulation = async (params: SimulationParams) => {
    try {
      setIsLoading(true);
      setError(null);
      
      // Call multi-holdings API endpoint
      const response = await fetch('http://localhost:3001/api/simulation/holdings-multi-run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          strategy_id: params.strategyId,
          portfolio_base_value: params.portfolioValue,
          rebalance_frequency: params.rebalanceFreq,
          rebalance_date: params.rebalanceDate,
          rebalance_type: params.rebalanceType,
          universe: params.universe,
          benchmark_symbol: params.benchmarkSymbol || '50 EQL Wgt',
          base_max_holdings: params.maxHoldings,
          momentum_ranking: params.momentumRanking,
          start_date: params.startDate,
          end_date: params.endDate,
          multipliers: [1, 2, 3, 4]  // Will run with 1x, 2x, 3x, 4x holdings
        })
      });

      const data = await response.json();
      console.log('API Response:', data);
      console.log('Multi Holdings Simulation:', data.multi_holdings_simulation);
      
      if (data.success && data.multi_holdings_simulation) {
        setMultiResults(data.multi_holdings_simulation);
        // Select first completed holding by default
        const firstCompleted = data.multi_holdings_simulation.holdings_results.find((h: HoldingResult) => h.status === 'completed');
        if (firstCompleted) {
          setSelectedHolding(firstCompleted.holding_size);
        }
      } else {
        setError('Failed to load multi-holdings simulation data');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  // Prepare comparison data
  const comparisonChartData = useMemo(() => {
    if (!multiResults) return [];
    
    return multiResults.holdings_results
      .filter(h => h.status === 'completed')
      .map(holding => ({
        holdings: `${holding.holding_size} stocks`,
        portfolioReturn: holding.total_return,
        benchmarkReturn: holding.benchmark_return,
        alpha: holding.alpha,
        sharpe: holding.sharpe_ratio,
        maxDrawdown: holding.max_drawdown,
        volatility: holding.volatility,
        monthlyChurn: holding.avg_monthly_churn,
        winRate: holding.monthly_win_rate
      }));
  }, [multiResults]);

  // Portfolio growth chart data (all holdings on same chart)
  const portfolioGrowthData = useMemo(() => {
    if (!multiResults) return [];
    
    const completedHoldings = multiResults.holdings_results.filter((h: HoldingResult) => h.status === 'completed');
    if (completedHoldings.length === 0) return [];
    
    // Get all unique dates
    const allDates = new Set<string>();
    completedHoldings.forEach((h: HoldingResult) => {
      if (h.portfolio_values && Array.isArray(h.portfolio_values)) {
        h.portfolio_values.forEach((pv: any) => allDates.add(pv.date));
      }
    });
    
    const sortedDates = Array.from(allDates).sort();
    
    // Create data points for each date
    return sortedDates.map(date => {
      const dataPoint: any = { date };
      
      completedHoldings.forEach((h: HoldingResult) => {
        if (h.portfolio_values && Array.isArray(h.portfolio_values)) {
          const value = h.portfolio_values.find((pv: any) => pv.date === date);
          if (value) {
            dataPoint[`holdings_${h.holding_size}`] = value.value;
            dataPoint[`benchmark`] = value.benchmark;
          }
        }
      });
      
      return dataPoint;
    });
  }, [multiResults]);

  const selectedHoldingData = useMemo(() => {
    if (!multiResults || !selectedHolding) return null;
    return multiResults.holdings_results.find((h: HoldingResult) => h.holding_size === selectedHolding);
  }, [multiResults, selectedHolding]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-600">Running multi-holdings simulation...</p>
          <p className="text-sm text-gray-500 mt-2">Testing different portfolio sizes</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="text-red-500 mb-4">Error: {error}</div>
          <Link href="/analytics/simulator">
            <Button>Back to Simulator</Button>
          </Link>
        </div>
      </div>
    );
  }

  if (!multiResults) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-600">No simulation data available</p>
          <Link href="/analytics/simulator">
            <Button className="mt-4">Back to Simulator</Button>
          </Link>
        </div>
      </div>
    );
  }

  const colors = ['#2563eb', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899'];

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center gap-4 mb-4">
            <Link href="/analytics/simulator" className="flex items-center gap-2 text-blue-600 hover:text-blue-800">
              <ArrowLeft className="h-5 w-5" />
              Strategy Simulator
            </Link>
            <span className="text-gray-500">/</span>
            <span className="font-semibold text-gray-900">Multi-Dimension Holdings Analysis</span>
          </div>
          <div className="flex items-center gap-2">
            <Shuffle className="h-6 w-6 text-blue-600" />
            <h1 className="text-2xl font-bold text-gray-900">Portfolio Size Optimization</h1>
            <Badge variant="outline" className="ml-2">{multiResults.holdings_results.length} Configurations Tested</Badge>
          </div>
        </div>

        {/* Aggregate Metrics Summary */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Target className="h-5 w-5" />
              Optimization Results
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">
                  {multiResults.aggregate_metrics?.best_holding_size ?? 0} stocks
                </div>
                <div className="text-sm text-gray-500">Best Return</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-purple-600">
                  {multiResults.aggregate_metrics?.optimal_risk_adjusted ?? 0} stocks
                </div>
                <div className="text-sm text-gray-500">Best Risk-Adjusted</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-gray-900">
                  {(multiResults.aggregate_metrics?.average_return ?? 0).toFixed(2)}%
                </div>
                <div className="text-sm text-gray-500">Avg Return</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">
                  +{(multiResults.aggregate_metrics?.average_alpha ?? 0).toFixed(2)}%
                </div>
                <div className="text-sm text-gray-500">Avg Alpha</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-purple-600">
                  {(multiResults.aggregate_metrics?.average_sharpe ?? 0).toFixed(2)}
                </div>
                <div className="text-sm text-gray-500">Avg Sharpe</div>
              </div>
              <div className="text-center">
                <div className="text-sm font-semibold text-red-700">
                  {multiResults.aggregate_metrics?.worst_holding_size ?? 0} stocks
                </div>
                <div className="text-xs text-gray-500">Worst Performer</div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Portfolio Growth Chart - All Holdings */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              Portfolio Growth Comparison
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-96">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={portfolioGrowthData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis 
                    dataKey="date" 
                    tick={{ fontSize: 11 }}
                    tickFormatter={(value) => {
                      const date = new Date(value);
                      return `${date.getMonth() + 1}/${date.getFullYear().toString().slice(-2)}`;
                    }}
                  />
                  <YAxis tick={{ fontSize: 11 }} tickFormatter={(value) => `₹${(value / 1000).toFixed(0)}K`} />
                  <Tooltip 
                    formatter={(value: number) => `₹${value.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`}
                    contentStyle={{ fontSize: '12px' }}
                  />
                  <Legend />
                  {multiResults.holdings_results
                    .filter((h: HoldingResult) => h.status === 'completed')
                    .map((h: HoldingResult, idx: number) => (
                      <Line 
                        key={`line-${idx}-${h.holding_size}`}
                        type="monotone" 
                        dataKey={`holdings_${h.holding_size}`} 
                        name={`${h.holding_size} stocks`}
                        stroke={colors[idx % colors.length]} 
                        strokeWidth={2}
                        dot={false}
                      />
                    ))
                  }
                  <Line 
                    type="monotone" 
                    dataKey="benchmark" 
                    name="Benchmark"
                    stroke="#dc2626" 
                    strokeWidth={2}
                    strokeDasharray="5 5"
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Holding Size Selector */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Select Portfolio Size for Detailed Analysis</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {multiResults.holdings_results.map((holding: HoldingResult, idx: number) => (
                <button
                  key={`holding-${idx}-${holding.holding_size}`}
                  onClick={() => setSelectedHolding(holding.holding_size)}
                  className={`p-4 rounded-lg border-2 transition-all ${
                    selectedHolding === holding.holding_size
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-semibold text-sm">{holding.holding_size} Stocks</span>
                    {holding.status === 'completed' ? (
                      <CheckCircle className="h-4 w-4 text-green-500" />
                    ) : holding.status === 'error' ? (
                      <AlertCircle className="h-4 w-4 text-red-500" />
                    ) : null}
                  </div>
                  <div className={`text-xl font-bold ${
                    holding.total_return >= 0 ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {holding.total_return >= 0 ? '+' : ''}{holding.total_return.toFixed(2)}%
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    Sharpe: {holding.sharpe_ratio.toFixed(2)}
                  </div>
                </button>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Comparison Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {/* Returns & Alpha Comparison */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5" />
                Returns & Alpha by Portfolio Size
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={comparisonChartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="holdings" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} tickFormatter={(value) => `${value}%`} />
                    <Tooltip 
                      formatter={(value: number) => `${value.toFixed(2)}%`}
                      contentStyle={{ fontSize: '12px' }}
                    />
                    <Legend />
                    <Bar dataKey="portfolioReturn" name="Portfolio Return" fill="#2563eb" />
                    <Bar dataKey="alpha" name="Alpha" fill="#10b981" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {/* Risk Metrics Comparison */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Activity className="h-5 w-5" />
                Risk Metrics by Portfolio Size
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={comparisonChartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="holdings" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip contentStyle={{ fontSize: '12px' }} />
                    <Legend />
                    <Bar dataKey="sharpe" name="Sharpe Ratio" fill="#8b5cf6" />
                    <Bar dataKey="volatility" name="Volatility (%)" fill="#f59e0b" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {/* Monthly Metrics */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Calendar className="h-5 w-5" />
                Monthly Performance Metrics
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={comparisonChartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="holdings" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} tickFormatter={(value) => `${value}%`} />
                    <Tooltip 
                      formatter={(value: number) => `${value.toFixed(2)}%`}
                      contentStyle={{ fontSize: '12px' }}
                    />
                    <Legend />
                    <Bar dataKey="monthlyChurn" name="Avg Monthly Churn" fill="#ec4899" />
                    <Bar dataKey="winRate" name="Monthly Win Rate" fill="#10b981" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {/* Drawdown Comparison */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingDown className="h-5 w-5" />
                Maximum Drawdown
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={comparisonChartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="holdings" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} tickFormatter={(value) => `${value}%`} />
                    <Tooltip 
                      formatter={(value: number) => `${value.toFixed(2)}%`}
                      contentStyle={{ fontSize: '12px' }}
                    />
                    <Bar dataKey="maxDrawdown" name="Max Drawdown" fill="#dc2626" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Selected Holding Details */}
        {selectedHoldingData && selectedHoldingData.status === 'completed' && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <DollarSign className="h-5 w-5" />
                Detailed Metrics: {selectedHoldingData.holding_size} Stocks Portfolio
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                <div>
                  <div className="text-sm text-gray-500">Total Return</div>
                  <div className={`text-2xl font-bold ${selectedHoldingData.total_return >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {selectedHoldingData.total_return >= 0 ? '+' : ''}{selectedHoldingData.total_return.toFixed(2)}%
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-500">Alpha</div>
                  <div className="text-2xl font-bold text-green-600">
                    +{selectedHoldingData.alpha.toFixed(2)}%
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-500">Sharpe Ratio</div>
                  <div className="text-2xl font-bold text-purple-600">
                    {selectedHoldingData.sharpe_ratio.toFixed(2)}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-500">Volatility</div>
                  <div className="text-lg font-semibold text-orange-600">
                    {selectedHoldingData.volatility.toFixed(2)}%
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-500">Max Drawdown</div>
                  <div className="text-lg font-semibold text-red-600">
                    {selectedHoldingData.max_drawdown.toFixed(2)}%
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-500">Avg Monthly Churn</div>
                  <div className="text-lg font-semibold">
                    {selectedHoldingData.avg_monthly_churn.toFixed(2)}%
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-500">Monthly Win Rate</div>
                  <div className="text-lg font-semibold text-green-600">
                    {selectedHoldingData.monthly_win_rate.toFixed(2)}%
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-500">Total Trades</div>
                  <div className="text-lg font-semibold">
                    {selectedHoldingData.total_trades}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Performance Table */}
        <Card className="mt-6">
          <CardHeader>
            <CardTitle>All Portfolio Sizes - Comprehensive Metrics</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="p-3 text-left font-semibold">Holdings</th>
                    <th className="p-3 text-right font-semibold">Return</th>
                    <th className="p-3 text-right font-semibold">Alpha</th>
                    <th className="p-3 text-right font-semibold">Sharpe</th>
                    <th className="p-3 text-right font-semibold">Volatility</th>
                    <th className="p-3 text-right font-semibold">Max DD</th>
                    <th className="p-3 text-right font-semibold">Churn</th>
                    <th className="p-3 text-right font-semibold">Win Rate</th>
                    <th className="p-3 text-right font-semibold">Trades</th>
                    <th className="p-3 text-center font-semibold">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {multiResults.holdings_results.map((holding: HoldingResult, idx: number) => (
                    <tr 
                      key={`table-${idx}-${holding.holding_size}`} 
                      className={`border-t hover:bg-gray-50 cursor-pointer ${selectedHolding === holding.holding_size ? 'bg-blue-50' : ''}`}
                      onClick={() => setSelectedHolding(holding.holding_size)}
                    >
                      <td className="p-3 font-medium">{holding.holding_size} stocks</td>
                      <td className={`p-3 text-right font-semibold ${holding.total_return >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {holding.total_return >= 0 ? '+' : ''}{holding.total_return.toFixed(2)}%
                      </td>
                      <td className="p-3 text-right text-green-600">
                        +{holding.alpha.toFixed(2)}%
                      </td>
                      <td className="p-3 text-right text-purple-600">
                        {holding.sharpe_ratio.toFixed(2)}
                      </td>
                      <td className="p-3 text-right text-orange-600">
                        {holding.volatility.toFixed(2)}%
                      </td>
                      <td className="p-3 text-right text-red-600">
                        {holding.max_drawdown.toFixed(2)}%
                      </td>
                      <td className="p-3 text-right">
                        {holding.avg_monthly_churn.toFixed(2)}%
                      </td>
                      <td className="p-3 text-right text-green-600">
                        {holding.monthly_win_rate.toFixed(2)}%
                      </td>
                      <td className="p-3 text-right">
                        {holding.total_trades}
                      </td>
                      <td className="p-3 text-center">
                        {holding.status === 'completed' ? (
                          <CheckCircle className="h-5 w-5 text-green-500 mx-auto" />
                        ) : holding.status === 'error' ? (
                          <AlertCircle className="h-5 w-5 text-red-500 mx-auto" />
                        ) : (
                          <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

const HoldingsMultiRunPage = () => {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>
    }>
      <HoldingsMultiRunContent />
    </Suspense>
  );
};

export default HoldingsMultiRunPage;
