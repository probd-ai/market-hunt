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
  Layers,
  CheckCircle,
  AlertCircle
} from 'lucide-react';
import { api } from '@/lib/api';

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

interface PeriodResult {
  period_label: string;
  start_date: string;
  end_date: string;
  total_return: number;
  benchmark_return: number;
  alpha: number;
  max_drawdown: number;
  sharpe_ratio: number;
  total_trades: number;
  final_portfolio_value: number;
  days_count: number;
  status: 'completed' | 'running' | 'error';
  error_message?: string;
}

interface MultiSimulationResult {
  params: SimulationParams;
  periods: PeriodResult[];
  aggregate_metrics: {
    avg_return: number;
    avg_alpha: number;
    avg_sharpe: number;
    best_period: string;
    worst_period: string;
    consistency_score: number;
  };
}

const MultiRunContent = () => {
  const searchParams = useSearchParams();
  const [simulationParams, setSimulationParams] = useState<SimulationParams | null>(null);
  const [multiResults, setMultiResults] = useState<MultiSimulationResult | null>(null);
  const [selectedPeriod, setSelectedPeriod] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const paramsString = searchParams?.get('params');
    if (paramsString) {
      try {
        const params = JSON.parse(decodeURIComponent(paramsString));
        setSimulationParams(params);
        runMultiDimensionSimulation(params);
      } catch (e) {
        setError('Failed to parse simulation parameters');
      }
    }
  }, [searchParams]);

  const runMultiDimensionSimulation = async (params: SimulationParams) => {
    try {
      setIsLoading(true);
      setError(null);
      
      // Call multi-dimension API endpoint
      const response = await fetch('http://localhost:3001/api/simulation/multi-run', {
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
          max_holdings: params.maxHoldings,
          momentum_ranking: params.momentumRanking,
          start_date: params.startDate,
          end_date: params.endDate
        })
      });

      const data = await response.json();
      
      if (data.success && data.multi_simulation) {
        setMultiResults(data.multi_simulation);
        // Select first completed period by default
        const firstCompleted = data.multi_simulation.periods.find((p: PeriodResult) => p.status === 'completed');
        if (firstCompleted) {
          setSelectedPeriod(firstCompleted.period_label);
        }
      } else {
        setError('Failed to load multi-dimension simulation data');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  // Prepare chart data for comparison
  const comparisonChartData = useMemo(() => {
    if (!multiResults) return [];
    
    return multiResults.periods
      .filter(p => p.status === 'completed')
      .map(period => ({
        period: period.period_label,
        portfolioReturn: period.total_return,
        benchmarkReturn: period.benchmark_return,
        alpha: period.alpha,
        sharpe: period.sharpe_ratio,
        maxDrawdown: period.max_drawdown
      }));
  }, [multiResults]);

  const selectedPeriodData = useMemo(() => {
    if (!multiResults || !selectedPeriod) return null;
    return multiResults.periods.find(p => p.period_label === selectedPeriod);
  }, [multiResults, selectedPeriod]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-600">Running multi-dimension simulation...</p>
          <p className="text-sm text-gray-500 mt-2">Analyzing performance across different time periods</p>
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
            <span className="font-semibold text-gray-900">Multi-Dimension Analysis</span>
          </div>
          <div className="flex items-center gap-2">
            <Layers className="h-6 w-6 text-purple-600" />
            <h1 className="text-2xl font-bold text-gray-900">Time Period Comparison</h1>
            <Badge variant="outline" className="ml-2">{multiResults.periods.length} Periods Analyzed</Badge>
          </div>
        </div>

        {/* Aggregate Metrics Summary */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Target className="h-5 w-5" />
              Aggregate Performance Metrics
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-gray-900">
                  {multiResults.aggregate_metrics.avg_return.toFixed(2)}%
                </div>
                <div className="text-sm text-gray-500">Avg Return</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">
                  +{multiResults.aggregate_metrics.avg_alpha.toFixed(2)}%
                </div>
                <div className="text-sm text-gray-500">Avg Alpha</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-purple-600">
                  {multiResults.aggregate_metrics.avg_sharpe.toFixed(2)}
                </div>
                <div className="text-sm text-gray-500">Avg Sharpe</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">
                  {multiResults.aggregate_metrics.consistency_score.toFixed(1)}%
                </div>
                <div className="text-sm text-gray-500">Consistency</div>
              </div>
              <div className="text-center">
                <div className="text-sm font-semibold text-green-700">
                  {multiResults.aggregate_metrics.best_period}
                </div>
                <div className="text-xs text-gray-500">Best Period</div>
              </div>
              <div className="text-center">
                <div className="text-sm font-semibold text-red-700">
                  {multiResults.aggregate_metrics.worst_period}
                </div>
                <div className="text-xs text-gray-500">Worst Period</div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Period Selector */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Select Time Period to Analyze</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-3">
              {multiResults.periods.map((period) => (
                <button
                  key={period.period_label}
                  onClick={() => setSelectedPeriod(period.period_label)}
                  className={`p-4 rounded-lg border-2 transition-all ${
                    selectedPeriod === period.period_label
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-semibold text-sm">{period.period_label}</span>
                    {period.status === 'completed' ? (
                      <CheckCircle className="h-4 w-4 text-green-500" />
                    ) : period.status === 'error' ? (
                      <AlertCircle className="h-4 w-4 text-red-500" />
                    ) : null}
                  </div>
                  <div className={`text-xl font-bold ${
                    period.total_return >= 0 ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {period.total_return >= 0 ? '+' : ''}{period.total_return.toFixed(2)}%
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    {period.days_count} days
                  </div>
                </button>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Comparison Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {/* Returns Comparison */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5" />
                Returns Comparison
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={comparisonChartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="period" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} tickFormatter={(value) => `${value}%`} />
                    <Tooltip 
                      formatter={(value: number) => `${value.toFixed(2)}%`}
                      contentStyle={{ fontSize: '12px' }}
                    />
                    <Legend />
                    <Bar dataKey="portfolioReturn" name="Portfolio" fill="#2563eb" />
                    <Bar dataKey="benchmarkReturn" name="Benchmark" fill="#dc2626" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {/* Alpha & Sharpe Comparison */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Activity className="h-5 w-5" />
                Alpha & Sharpe Ratio
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={comparisonChartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="period" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip contentStyle={{ fontSize: '12px' }} />
                    <Legend />
                    <Bar dataKey="alpha" name="Alpha (%)" fill="#10b981" />
                    <Bar dataKey="sharpe" name="Sharpe Ratio" fill="#8b5cf6" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Selected Period Details */}
        {selectedPeriodData && selectedPeriodData.status === 'completed' && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Calendar className="h-5 w-5" />
                Detailed Analysis: {selectedPeriodData.period_label}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                <div>
                  <div className="text-sm text-gray-500">Period</div>
                  <div className="text-lg font-semibold">{selectedPeriodData.start_date} to {selectedPeriodData.end_date}</div>
                </div>
                <div>
                  <div className="text-sm text-gray-500">Total Return</div>
                  <div className={`text-2xl font-bold ${selectedPeriodData.total_return >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {selectedPeriodData.total_return >= 0 ? '+' : ''}{selectedPeriodData.total_return.toFixed(2)}%
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-500">Benchmark Return</div>
                  <div className="text-2xl font-bold text-blue-600">
                    {selectedPeriodData.benchmark_return >= 0 ? '+' : ''}{selectedPeriodData.benchmark_return.toFixed(2)}%
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-500">Alpha</div>
                  <div className="text-2xl font-bold text-green-600">
                    +{selectedPeriodData.alpha.toFixed(2)}%
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-500">Max Drawdown</div>
                  <div className="text-lg font-semibold text-red-600">
                    {selectedPeriodData.max_drawdown.toFixed(2)}%
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-500">Sharpe Ratio</div>
                  <div className="text-lg font-semibold text-purple-600">
                    {selectedPeriodData.sharpe_ratio.toFixed(2)}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-500">Total Trades</div>
                  <div className="text-lg font-semibold">
                    {selectedPeriodData.total_trades}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-500">Final Value</div>
                  <div className="text-lg font-semibold">
                    ₹{selectedPeriodData.final_portfolio_value.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                  </div>
                </div>
              </div>

              {/* Link to view full simulation */}
              <div className="mt-6 pt-6 border-t">
                <Link 
                  href={`/analytics/simulator/run?strategyId=${simulationParams?.strategyId}&portfolioValue=${simulationParams?.portfolioValue}&rebalanceFreq=${simulationParams?.rebalanceFreq}&rebalanceDate=${simulationParams?.rebalanceDate}&rebalanceType=${simulationParams?.rebalanceType}&universe=${simulationParams?.universe}&benchmarkSymbol=${simulationParams?.benchmarkSymbol}&maxHoldings=${simulationParams?.maxHoldings}&momentumRanking=${simulationParams?.momentumRanking}&startDate=${selectedPeriodData.start_date}&endDate=${selectedPeriodData.end_date}`}
                >
                  <Button variant="outline" className="w-full">
                    View Full Simulation for This Period
                  </Button>
                </Link>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Performance Table */}
        <Card className="mt-6">
          <CardHeader>
            <CardTitle>All Periods Performance Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="p-3 text-left font-semibold">Period</th>
                    <th className="p-3 text-left font-semibold">Days</th>
                    <th className="p-3 text-right font-semibold">Portfolio Return</th>
                    <th className="p-3 text-right font-semibold">Benchmark Return</th>
                    <th className="p-3 text-right font-semibold">Alpha</th>
                    <th className="p-3 text-right font-semibold">Sharpe</th>
                    <th className="p-3 text-right font-semibold">Max DD</th>
                    <th className="p-3 text-right font-semibold">Trades</th>
                    <th className="p-3 text-center font-semibold">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {multiResults.periods.map((period, index) => (
                    <tr 
                      key={period.period_label} 
                      className={`border-t hover:bg-gray-50 cursor-pointer ${selectedPeriod === period.period_label ? 'bg-blue-50' : ''}`}
                      onClick={() => setSelectedPeriod(period.period_label)}
                    >
                      <td className="p-3 font-medium">{period.period_label}</td>
                      <td className="p-3 text-gray-600">{period.days_count}</td>
                      <td className={`p-3 text-right font-semibold ${period.total_return >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {period.total_return >= 0 ? '+' : ''}{period.total_return.toFixed(2)}%
                      </td>
                      <td className="p-3 text-right text-blue-600">
                        {period.benchmark_return >= 0 ? '+' : ''}{period.benchmark_return.toFixed(2)}%
                      </td>
                      <td className="p-3 text-right text-green-600">
                        +{period.alpha.toFixed(2)}%
                      </td>
                      <td className="p-3 text-right text-purple-600">
                        {period.sharpe_ratio.toFixed(2)}
                      </td>
                      <td className="p-3 text-right text-red-600">
                        {period.max_drawdown.toFixed(2)}%
                      </td>
                      <td className="p-3 text-right">
                        {period.total_trades}
                      </td>
                      <td className="p-3 text-center">
                        {period.status === 'completed' ? (
                          <CheckCircle className="h-5 w-5 text-green-500 mx-auto" />
                        ) : period.status === 'error' ? (
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

const MultiRunPage = () => {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>
    }>
      <MultiRunContent />
    </Suspense>
  );
};

export default MultiRunPage;
