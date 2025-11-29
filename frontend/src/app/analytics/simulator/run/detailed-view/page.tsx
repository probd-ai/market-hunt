'use client';

import React, { useState, useEffect, Suspense } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { 
  ArrowLeft,
  TrendingUp,
  TrendingDown,
  Calendar,
  DollarSign,
  Activity,
  BarChart3,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import { api } from '@/lib/api';

// Types (matching the main simulator)
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

interface HoldingStock {
  symbol: string;
  companyName: string;
  quantity: number;
  avgPrice: number;
  currentPrice: number;
  marketValue: number;
  pnl: number;
  pnlPercent: number;
  sector: string;
  weight?: number;
  holdingPeriods?: number;
  allocationWeight?: number;
}

interface DayResult {
  date: string;
  portfolioValue: number;
  benchmarkValue: number;
  holdings: HoldingStock[];
  newAdded: string[];
  exited: string[];
  exitedDetails: HoldingStock[];
  cash: number;
  totalPnL: number;
  dayPnL: number;
  benchmarkPrice: number;
  dailyCharges?: {
    total_charges: number;
    buy_charges: number;
    sell_charges: number;
  };
  cumulativeCharges?: number;
  chargeImpactPercent?: number;
  brokerageEnabled?: boolean;
  exchangeUsed?: string | null;
}

interface SimulationResult {
  params: SimulationParams;
  benchmark_symbol: string;
  results: DayResult[];
  chargeAnalytics?: any;
  summary: {
    totalReturn: number;
    benchmarkReturn: number;
    alpha: number;
    maxDrawdown: number;
    sharpeRatio: number;
    totalTrades: number;
    brokerageEnabled?: boolean;
    chargeImpact?: number;
    theoreticalReturnWithoutCharges?: number | null;
  };
}

const DetailedViewContent = () => {
  const searchParams = useSearchParams();
  const [simulationParams, setSimulationParams] = useState<SimulationParams | null>(null);
  const [simulationResult, setSimulationResult] = useState<SimulationResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedDays, setExpandedDays] = useState<Set<number>>(new Set());
  const [showOnlyRebalanceDays, setShowOnlyRebalanceDays] = useState(false);
  const [isRestoredFromCache, setIsRestoredFromCache] = useState(false);

  useEffect(() => {
    // First, try to get data from sessionStorage (avoid recalculation)
    try {
      const storedResult = sessionStorage.getItem('simulationResult');
      const storedParams = sessionStorage.getItem('simulationParams');
      
      if (storedResult && storedParams) {
        const result = JSON.parse(storedResult);
        const params = JSON.parse(storedParams);
        
        setSimulationResult(result);
        setSimulationParams(params);
        setIsLoading(false);
        setIsRestoredFromCache(true); // Mark as restored from cache
        return; // Don't run simulation again!
      }
    } catch (e) {
      console.warn('Failed to load from sessionStorage:', e);
    }
    
    // Fallback: Parse from URL params (will recalculate)
    const paramsString = searchParams?.get('params');
    if (paramsString) {
      try {
        const params = JSON.parse(decodeURIComponent(paramsString));
        setSimulationParams(params);
        runSimulation(params);
      } catch (e) {
        setError('Failed to parse simulation parameters');
      }
    } else {
      setError('No simulation data available. Please run a simulation first.');
    }
  }, [searchParams]);

  const runSimulation = async (params: SimulationParams) => {
    try {
      setIsLoading(true);
      setError(null);
      
      const apiParams = {
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
      };
      
      const response = await api.runSimulation(apiParams);
      
      if (response.success && response.simulation) {
        const simulationData = {
          params,
          benchmark_symbol: response.simulation.benchmark_symbol || params.benchmarkSymbol || '50 EQL Wgt',
          results: response.simulation.results.map((day: any) => ({
            date: day.date,
            portfolioValue: day.portfolio_value,
            benchmarkValue: day.benchmark_value || day.portfolio_value,
            holdings: day.holdings.map((holding: any) => ({
              symbol: holding.symbol,
              companyName: holding.company_name,
              quantity: holding.quantity,
              avgPrice: holding.avg_price,
              currentPrice: holding.current_price,
              marketValue: holding.market_value,
              pnl: holding.pnl,
              pnlPercent: holding.pnl_percent,
              sector: holding.sector,
              weight: holding.weight,
              holdingPeriods: holding.holding_periods,
              allocationWeight: holding.allocation_weight
            })),
            newAdded: day.new_added || [],
            exited: day.exited || [],
            exitedDetails: (day.exited_details || []).map((exit: any) => ({
              symbol: exit.symbol,
              companyName: exit.company_name,
              quantity: exit.quantity,
              avgPrice: exit.avg_price,
              currentPrice: exit.exit_price,
              marketValue: exit.quantity * exit.exit_price,
              pnl: exit.pnl,
              pnlPercent: exit.pnl_percent,
              sector: exit.sector
            })),
            cash: day.cash,
            totalPnL: day.total_pnl,
            dayPnL: day.day_pnl || 0,
            benchmarkPrice: day.benchmark_price || day.portfolio_value,
            dailyCharges: day.daily_charges || { total_charges: 0, buy_charges: 0, sell_charges: 0 },
            cumulativeCharges: day.cumulative_charges || 0,
            chargeImpactPercent: day.charge_impact_percent || 0,
            brokerageEnabled: day.brokerage_enabled || false,
            exchangeUsed: day.exchange_used || null
          })),
          chargeAnalytics: response.simulation.charge_analytics || null,
          summary: {
            totalReturn: response.simulation.summary.total_return,
            benchmarkReturn: response.simulation.summary.benchmark_return,
            alpha: response.simulation.summary.alpha,
            maxDrawdown: response.simulation.summary.max_drawdown,
            sharpeRatio: response.simulation.summary.sharpe_ratio,
            totalTrades: response.simulation.summary.total_trades,
            brokerageEnabled: response.simulation.summary.brokerage_enabled || false,
            chargeImpact: response.simulation.summary.charge_impact || 0,
            theoreticalReturnWithoutCharges: response.simulation.summary.theoretical_return_without_charges || null
          }
        };
        
        setSimulationResult(simulationData);
      } else {
        setError('Failed to load simulation data');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  const toggleDay = (index: number) => {
    const newExpanded = new Set(expandedDays);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedDays(newExpanded);
  };

  const expandAll = () => {
    const allIndices = new Set(simulationResult?.results.map((_, i) => i) || []);
    setExpandedDays(allIndices);
  };

  const collapseAll = () => {
    setExpandedDays(new Set());
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading simulation data...</p>
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

  if (!simulationResult) {
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

  // Filter data based on toggle
  const displayResults = showOnlyRebalanceDays 
    ? simulationResult.results.filter(day => day.newAdded.length > 0 || day.exited.length > 0)
    : simulationResult.results;

  const basePortfolioValue = simulationParams?.portfolioValue || 100000;
  const baseBenchmarkValue = simulationResult.results[0]?.benchmarkValue || basePortfolioValue;

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center gap-4 mb-4">
            <Link href="/analytics/simulator/run" className="flex items-center gap-2 text-blue-600 hover:text-blue-800">
              <ArrowLeft className="h-5 w-5" />
              Back to Simulator
            </Link>
            <span className="text-gray-500">/</span>
            <span className="font-semibold text-gray-900">Detailed View - All Days</span>
          </div>
        </div>

        {/* Summary Card */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span>Simulation Summary</span>
              <div className="flex items-center gap-2">
                {isRestoredFromCache && (
                  <Badge variant="outline" className="text-xs text-green-600">
                    ⚡ Instant Load
                  </Badge>
                )}
                <Badge variant="outline">{displayResults.length} Days</Badge>
              </div>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-gray-900">
                  {simulationResult.summary.totalReturn.toFixed(2)}%
                </div>
                <div className="text-sm text-gray-500">Total Return</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">
                  {simulationResult.summary.benchmarkReturn.toFixed(2)}%
                </div>
                <div className="text-sm text-gray-500">Benchmark Return</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">
                  +{simulationResult.summary.alpha.toFixed(2)}%
                </div>
                <div className="text-sm text-gray-500">Alpha</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-purple-600">
                  {simulationResult.summary.totalTrades}
                </div>
                <div className="text-sm text-gray-500">Total Trades</div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Controls */}
        <div className="mb-4 flex items-center justify-between">
          <div className="flex gap-2">
            <Button size="sm" onClick={expandAll} variant="outline">
              Expand All
            </Button>
            <Button size="sm" onClick={collapseAll} variant="outline">
              Collapse All
            </Button>
            <Button 
              size="sm" 
              onClick={() => setShowOnlyRebalanceDays(!showOnlyRebalanceDays)}
              variant={showOnlyRebalanceDays ? "primary" : "outline"}
            >
              {showOnlyRebalanceDays ? 'Show All Days' : 'Rebalance Days Only'}
            </Button>
          </div>
          <div className="text-sm text-gray-600">
            Displaying {displayResults.length} of {simulationResult.results.length} days
          </div>
        </div>

        {/* Day-by-Day Data */}
        <div className="space-y-4">
          {displayResults.map((dayResult, index) => {
            const actualIndex = simulationResult.results.indexOf(dayResult);
            const isExpanded = expandedDays.has(actualIndex);
            const hasActivity = dayResult.newAdded.length > 0 || dayResult.exited.length > 0;
            const portfolioReturn = ((dayResult.portfolioValue / basePortfolioValue - 1) * 100);
            const benchmarkReturn = ((dayResult.benchmarkValue / baseBenchmarkValue - 1) * 100);

            return (
              <Card key={actualIndex} className={hasActivity ? 'border-l-4 border-l-blue-500' : ''}>
                <CardHeader className="cursor-pointer hover:bg-gray-50">
                  <div onClick={() => toggleDay(actualIndex)} className="w-full">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <div className="flex items-center gap-2">
                          {isExpanded ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
                          <Calendar className="h-5 w-5 text-gray-500" />
                          <span className="font-semibold">{new Date(dayResult.date).toLocaleDateString('en-US', { 
                            year: 'numeric', 
                            month: 'short', 
                            day: 'numeric' 
                          })}</span>
                          <Badge variant="outline">Day {actualIndex + 1}</Badge>
                        </div>
                        {hasActivity && (
                          <Badge variant="default" className="bg-blue-500">
                            Rebalance Day
                          </Badge>
                        )}
                      </div>
                      <div className="flex items-center gap-6">
                        <div className="text-right">
                          <div className="text-lg font-bold">
                            ₹{dayResult.portfolioValue.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                          </div>
                          <div className={`text-sm ${portfolioReturn >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                            {portfolioReturn >= 0 ? '+' : ''}{portfolioReturn.toFixed(2)}%
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="text-sm font-semibold text-gray-600">
                            {dayResult.holdings.length} Holdings
                          </div>
                          {hasActivity && (
                            <div className="text-xs text-blue-600">
                              +{dayResult.newAdded.length} / -{dayResult.exited.length}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                </CardHeader>

                {isExpanded && (
                  <CardContent className="border-t">
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                      {/* Current Holdings */}
                      <div>
                        <h3 className="font-semibold mb-3 flex items-center gap-2">
                          <BarChart3 className="h-4 w-4" />
                          Current Holdings ({dayResult.holdings.length})
                        </h3>
                        <div className="space-y-2 max-h-96 overflow-y-auto">
                          {dayResult.holdings.map((holding) => (
                            <div key={holding.symbol} className="bg-white border rounded-lg p-3">
                              <div className="flex items-center justify-between mb-2">
                                <div>
                                  <div className="font-medium">{holding.symbol}</div>
                                  <div className="text-xs text-gray-500">{holding.companyName}</div>
                                </div>
                                <Badge variant={holding.pnl >= 0 ? 'default' : 'secondary'}>
                                  {holding.pnlPercent >= 0 ? '+' : ''}{holding.pnlPercent.toFixed(2)}%
                                </Badge>
                              </div>
                              <div className="grid grid-cols-2 gap-2 text-xs text-gray-600">
                                <div>Qty: {holding.quantity.toFixed(2)}</div>
                                <div>Avg: ₹{holding.avgPrice.toFixed(2)}</div>
                                <div>Current: ₹{holding.currentPrice.toFixed(2)}</div>
                                <div>Value: ₹{holding.marketValue.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* New Additions */}
                      <div>
                        <h3 className="font-semibold mb-3 flex items-center gap-2 text-green-600">
                          <TrendingUp className="h-4 w-4" />
                          New Additions ({dayResult.newAdded.length})
                        </h3>
                        <div className="space-y-2 max-h-96 overflow-y-auto">
                          {dayResult.newAdded.length > 0 ? (
                            dayResult.newAdded.map((symbolName) => {
                              const stockDetails = dayResult.holdings.find(h => h.symbol === symbolName);
                              return stockDetails ? (
                                <div key={symbolName} className="bg-green-50 border border-green-200 rounded-lg p-3">
                                  <div className="font-medium">{symbolName}</div>
                                  <div className="text-xs text-gray-600">{stockDetails.companyName}</div>
                                  <div className="text-xs text-green-600 mt-1">
                                    {stockDetails.quantity.toFixed(2)} shares @ ₹{stockDetails.avgPrice.toFixed(2)}
                                  </div>
                                </div>
                              ) : null;
                            })
                          ) : (
                            <div className="text-center py-4 text-gray-500 text-sm">
                              No new additions
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Exits */}
                      <div>
                        <h3 className="font-semibold mb-3 flex items-center gap-2 text-red-600">
                          <TrendingDown className="h-4 w-4" />
                          Exits ({dayResult.exited.length})
                        </h3>
                        <div className="space-y-2 max-h-96 overflow-y-auto">
                          {dayResult.exitedDetails && dayResult.exitedDetails.length > 0 ? (
                            dayResult.exitedDetails.map((exit) => (
                              <div key={exit.symbol} className="bg-red-50 border border-red-200 rounded-lg p-3">
                                <div className="flex items-center justify-between mb-2">
                                  <div>
                                    <div className="font-medium">{exit.symbol}</div>
                                    <div className="text-xs text-gray-600">{exit.companyName}</div>
                                  </div>
                                  <Badge variant={exit.pnl >= 0 ? 'default' : 'secondary'}>
                                    {exit.pnlPercent >= 0 ? '+' : ''}{exit.pnlPercent.toFixed(2)}%
                                  </Badge>
                                </div>
                                <div className="grid grid-cols-2 gap-2 text-xs text-gray-600">
                                  <div>Qty: {exit.quantity.toFixed(2)}</div>
                                  <div>Avg: ₹{exit.avgPrice.toFixed(2)}</div>
                                  <div>Exit: ₹{exit.currentPrice.toFixed(2)}</div>
                                  <div className={`font-medium ${exit.pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                    P&L: ₹{exit.pnl.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                                  </div>
                                </div>
                              </div>
                            ))
                          ) : dayResult.exited.length > 0 ? (
                            dayResult.exited.map((symbolName) => (
                              <div key={symbolName} className="bg-red-50 border border-red-200 rounded-lg p-3">
                                <div className="font-medium">{symbolName}</div>
                                <div className="text-xs text-red-600 mt-1">Removed from portfolio</div>
                              </div>
                            ))
                          ) : (
                            <div className="text-center py-4 text-gray-500 text-sm">
                              No exits
                            </div>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Day Metrics */}
                    <div className="mt-4 pt-4 border-t grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                      <div>
                        <div className="text-gray-500">Portfolio Value</div>
                        <div className="font-semibold">₹{dayResult.portfolioValue.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</div>
                      </div>
                      <div>
                        <div className="text-gray-500">Benchmark Value</div>
                        <div className="font-semibold">₹{dayResult.benchmarkValue.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</div>
                      </div>
                      <div>
                        <div className="text-gray-500">Day P&L</div>
                        <div className={`font-semibold ${dayResult.dayPnL >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          ₹{dayResult.dayPnL.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                        </div>
                      </div>
                      <div>
                        <div className="text-gray-500">Total P&L</div>
                        <div className={`font-semibold ${dayResult.totalPnL >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          ₹{dayResult.totalPnL.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                        </div>
                      </div>
                    </div>
                  </CardContent>
                )}
              </Card>
            );
          })}
        </div>
      </div>
    </div>
  );
};

const DetailedViewPage = () => {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>
    }>
      <DetailedViewContent />
    </Suspense>
  );
};

export default DetailedViewPage;
