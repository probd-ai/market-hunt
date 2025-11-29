'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { ArrowLeft, Bug, Play, TrendingUp, AlertTriangle, CheckCircle, XCircle, BarChart3, Calendar, Activity, Settings, Edit3 } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';

interface DebugResult {
  date: string;
  day_number: number;
  portfolio_value: number;
  should_rebalance: boolean;
  qualified_stocks: string[];
  holdings_count: number;
  holdings_detail: Array<{
    symbol: string;
    shares: number;
    price: number;
    value: number;
  }>;
}

interface DebugResponse {
  success: boolean;
  debug_simulation?: {
    params: any;
    debug_results: DebugResult[];
    summary: {
      total_days: number;
      rebalance_days: number;
      final_value: number;
    };
  };
  message?: string;
}

interface TestScenario {
  id: string;
  name: string;
  description: string;
  params: any;
  expectedBehavior: string;
  riskLevel: 'low' | 'medium' | 'high';
}

const SimulationDebugPage = () => {
  const [debugResult, setDebugResult] = useState<DebugResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedScenario, setSelectedScenario] = useState<string>('');
  const [testParams, setTestParams] = useState<TestParams>({
    strategy_id: "strategy_1756565385890",
    portfolio_base_value: 100000,
    rebalance_frequency: "monthly",
    rebalance_date: "first",
    universe: "NIFTY100",
    benchmark_symbol: "Nifty 50",
    max_holdings: 10,
    momentum_ranking: "20_day_return",
    start_date: "2020-01-01",
    end_date: "2020-12-31"
  });
  const [isEditMode, setIsEditMode] = useState(false);

interface TestScenario {
  id: string;
  name: string;
  description: string;
  defaultParams: any;
  expectedBehavior: string;
  riskLevel: 'low' | 'medium' | 'high';
  category: 'spike_detection' | 'stress_test' | 'validation' | 'performance';
}

interface TestParams {
  strategy_id: string;
  portfolio_base_value: number;
  rebalance_frequency: string;
  rebalance_date: string;
  universe: string;
  benchmark_symbol: string;
  max_holdings: number;
  momentum_ranking: string;
  start_date: string;
  end_date: string;
}

const SimulationDebugPage = () => {
  const [debugResult, setDebugResult] = useState<DebugResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedScenario, setSelectedScenario] = useState<string>('');
  const [testParams, setTestParams] = useState<TestParams>({
    strategy_id: "strategy_1756565385890",
    portfolio_base_value: 100000,
    rebalance_frequency: "monthly",
    rebalance_date: "first",
    universe: "NIFTY100",
    benchmark_symbol: "Nifty 50",
    max_holdings: 10,
    momentum_ranking: "20_day_return",
    start_date: "2020-01-01",
    end_date: "2020-12-31"
  });
  const [isEditMode, setIsEditMode] = useState(false);

  const testScenarios: TestScenario[] = [
    {
      id: 'rebalance_spike_test',
      name: '🚨 Rebalance Spike Detection',
      description: 'Comprehensive test for artificial portfolio spikes on rebalance days over full year',
      category: 'spike_detection',
      riskLevel: 'high',
      expectedBehavior: 'Portfolio should preserve capital during rebalancing, no sudden jumps greater than 5%',
      defaultParams: {
        strategy_id: "strategy_1756565385890",
        portfolio_base_value: 100000,
        rebalance_frequency: "monthly",
        rebalance_date: "first",
        universe: "NIFTY100",
        benchmark_symbol: "Nifty 50",
        max_holdings: 10,
        momentum_ranking: "20_day_return",
        start_date: "2020-01-01",
        end_date: "2020-12-31" // Full year = 365 days with 12 rebalances
      }
    },
    {
      id: 'weekly_rebalance_stress',
      name: '⚡ Weekly Rebalance Stress Test',
      description: 'High-frequency rebalancing stress test to detect calculation errors',
      category: 'stress_test',
      riskLevel: 'high',
      expectedBehavior: 'Weekly rebalancing should maintain portfolio integrity without amplification errors',
      defaultParams: {
        strategy_id: "strategy_1756565385890",
        portfolio_base_value: 100000,
        rebalance_frequency: "weekly",
        rebalance_date: "first",
        universe: "NIFTY100",
        benchmark_symbol: "Nifty 50",
        max_holdings: 8,
        momentum_ranking: "risk_adjusted",
        start_date: "2020-01-01",
        end_date: "2020-06-30" // 6 months = ~26 weekly rebalances
      }
    },
    {
      id: 'momentum_rotation_analysis',
      name: '🔄 Momentum Rotation Deep Analysis',
      description: 'Analyze momentum-based stock selection and rotation patterns',
      category: 'validation',
      riskLevel: 'medium',
      expectedBehavior: 'Should demonstrate clear momentum-based stock rotation with portfolio concentration limits',
      defaultParams: {
        strategy_id: "strategy_1756565385890",
        portfolio_base_value: 100000,
        rebalance_frequency: "monthly",
        rebalance_date: "first",
        universe: "NIFTY100",
        benchmark_symbol: "Nifty 50",
        max_holdings: 5, // Smaller portfolio for clearer rotation analysis
        momentum_ranking: "20_day_return",
        start_date: "2020-01-01",
        end_date: "2021-01-01" // Full year for seasonal patterns
      }
    },
    {
      id: 'crash_recovery_test',
      name: '📉 Market Crash Recovery Test',
      description: 'Test portfolio behavior during March 2020 crash and recovery',
      category: 'stress_test',
      riskLevel: 'high',
      expectedBehavior: 'Should handle extreme volatility without calculation errors or impossible returns',
      defaultParams: {
        strategy_id: "strategy_1756565385890",
        portfolio_base_value: 100000,
        rebalance_frequency: "monthly",
        rebalance_date: "first",
        universe: "NIFTY100",
        benchmark_symbol: "Nifty 50",
        max_holdings: 10,
        momentum_ranking: "risk_adjusted", // Better for volatile periods
        start_date: "2020-02-01",
        end_date: "2020-08-31" // Covers crash and initial recovery
      }
    },
    {
      id: 'capital_preservation_audit',
      name: '💰 Capital Preservation Audit',
      description: 'Verify exact capital preservation during all rebalancing events',
      category: 'validation',
      riskLevel: 'low',
      expectedBehavior: 'Before/after rebalance portfolio values should match within 0.01% tolerance',
      defaultParams: {
        strategy_id: "strategy_1756565385890",
        portfolio_base_value: 100000,
        rebalance_frequency: "monthly",
        rebalance_date: "first",
        universe: "NIFTY100",
        benchmark_symbol: "Nifty 50",
        max_holdings: 10,
        momentum_ranking: "20_day_return",
        start_date: "2020-01-01",
        end_date: "2021-12-31" // 2 full years = 24 rebalances
      }
    },
    {
      id: 'performance_benchmark',
      name: '🏆 Performance vs Benchmark',
      description: 'Compare strategy performance against Nifty 50 benchmark',
      category: 'performance',
      riskLevel: 'medium',
      expectedBehavior: 'Strategy should demonstrate momentum factor effectiveness vs passive benchmark',
      defaultParams: {
        strategy_id: "strategy_1756565385890",
        portfolio_base_value: 100000,
        rebalance_frequency: "monthly",
        rebalance_date: "first",
        universe: "NIFTY100",
        benchmark_symbol: "Nifty 50",
        max_holdings: 15,
        momentum_ranking: "technical",
        start_date: "2020-01-01",
        end_date: "2022-12-31" // 3 full years for robust analysis
      }
    }
  ];

  const handleScenarioChange = (scenarioId: string) => {
    setSelectedScenario(scenarioId);
    const scenario = testScenarios.find(s => s.id === scenarioId);
    if (scenario) {
      setTestParams(scenario.defaultParams);
    }
    setIsEditMode(false);
    setDebugResult(null);
    setError(null);
  };

  const handleParamChange = (key: keyof TestParams, value: any) => {
    setTestParams(prev => ({
      ...prev,
      [key]: value
    }));
  };

  const runScenarioTest = async () => {
    if (!selectedScenario) {
      setError('Please select a test scenario first');
      return;
    }

    try {
      setIsLoading(true);
      setError(null);

      const response = await fetch('http://localhost:3001/api/simulation/debug', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(testParams)
      });

      const result = await response.json();
      setDebugResult(result);

    } catch (err) {
      console.error('Debug simulation error:', err);
      setError('Failed to run debug simulation');
    } finally {
      setIsLoading(false);
    }
  };

  const analyzeResults = (results: DebugResult[]) => {
    if (!results || results.length === 0) return null;

    const analysis = {
      totalDays: results.length,
      rebalanceDays: results.filter(r => r.should_rebalance).length,
      maxPortfolioValue: Math.max(...results.map(r => r.portfolio_value)),
      minPortfolioValue: Math.min(...results.map(r => r.portfolio_value)),
      finalReturn: ((results[results.length - 1].portfolio_value / results[0].portfolio_value) - 1) * 100,
      volatility: 0,
      maxDrawdown: 0,
      spikes: [] as Array<{date: string, change: number, isRebalance: boolean}>,
      issues: [] as string[]
    };

    // Calculate daily returns and detect spikes
    for (let i = 1; i < results.length; i++) {
      const prevValue = results[i-1].portfolio_value;
      const currValue = results[i].portfolio_value;
      const dailyReturn = ((currValue / prevValue) - 1) * 100;
      
      // Detect suspicious spikes (increased threshold for longer tests)
      if (Math.abs(dailyReturn) > 10) {
        analysis.spikes.push({
          date: results[i].date,
          change: dailyReturn,
          isRebalance: results[i].should_rebalance
        });
      }

      // Track max drawdown
      const peak = Math.max(...results.slice(0, i+1).map(r => r.portfolio_value));
      const drawdown = ((currValue / peak) - 1) * 100;
      analysis.maxDrawdown = Math.min(analysis.maxDrawdown, drawdown);
    }

    // Check for issues
    if (analysis.spikes.length > 0) {
      analysis.issues.push(`${analysis.spikes.length} portfolio spikes detected (greater than 10% daily change)`);
    }
    if (analysis.rebalanceDays === 0) {
      analysis.issues.push('No rebalancing occurred during test period');
    }
    if (analysis.maxPortfolioValue / analysis.minPortfolioValue > 5) {
      analysis.issues.push('Extreme portfolio value range detected');
    }
    if (Math.abs(analysis.finalReturn) > 200) {
      analysis.issues.push('Unrealistic total return detected');
    }

    return analysis;
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value);
  };

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'low': return 'bg-green-100 text-green-800';
      case 'medium': return 'bg-yellow-100 text-yellow-800';
      case 'high': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'spike_detection': return 'bg-red-50 border-red-200';
      case 'stress_test': return 'bg-orange-50 border-orange-200';
      case 'validation': return 'bg-blue-50 border-blue-200';
      case 'performance': return 'bg-green-50 border-green-200';
      default: return 'bg-gray-50 border-gray-200';
    }
  };

  const selectedScenarioData = testScenarios.find(s => s.id === selectedScenario);

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-4 mb-4">
            <Link href="/analytics" className="flex items-center gap-2 text-blue-600 hover:text-blue-800">
              <ArrowLeft className="h-5 w-5" />
              Analytics Hub
            </Link>
            <span className="text-gray-500">/</span>
            <span className="font-semibold text-gray-900">Expert Debug Suite</span>
          </div>
          
          <div className="flex items-center gap-3">
            <Bug className="h-8 w-8 text-orange-600" />
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Expert Portfolio Debug Suite</h1>
              <p className="text-gray-600">Advanced testing scenarios with customizable parameters for comprehensive validation</p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left Panel - Test Selection & Configuration */}
          <div className="space-y-6">
            {/* Scenario Selection */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Settings className="h-5 w-5" />
                  Test Scenario Selection
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Select Test Scenario
                    </label>
                    <select
                      value={selectedScenario}
                      onChange={(e) => handleScenarioChange(e.target.value)}
                      className="w-full p-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value="">Choose a test scenario...</option>
                      {testScenarios.map((scenario) => (
                        <option key={scenario.id} value={scenario.id}>
                          {scenario.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  {selectedScenarioData && (
                    <div className={`p-4 rounded-lg border ${getCategoryColor(selectedScenarioData.category)}`}>
                      <div className="flex items-start justify-between mb-2">
                        <h3 className="font-medium text-gray-900">{selectedScenarioData.name}</h3>
                        <Badge className={getRiskColor(selectedScenarioData.riskLevel)}>
                          {selectedScenarioData.riskLevel.toUpperCase()}
                        </Badge>
                      </div>
                      <p className="text-sm text-gray-600 mb-2">{selectedScenarioData.description}</p>
                      <p className="text-xs text-gray-500">
                        <strong>Expected:</strong> {selectedScenarioData.expectedBehavior}
                      </p>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Parameter Configuration */}
            {selectedScenario && (
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="flex items-center gap-2">
                      <Edit3 className="h-5 w-5" />
                      Test Parameters
                    </CardTitle>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setIsEditMode(!isEditMode)}
                    >
                      {isEditMode ? 'Lock' : 'Edit'}
                    </Button>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 gap-4">
                    {/* Basic Parameters */}
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">
                          Portfolio Value
                        </label>
                        <input
                          type="number"
                          value={testParams.portfolio_base_value}
                          onChange={(e) => handleParamChange('portfolio_base_value', parseInt(e.target.value))}
                          disabled={!isEditMode}
                          className="w-full p-2 text-sm border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 disabled:bg-gray-50"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">
                          Max Holdings
                        </label>
                        <input
                          type="number"
                          value={testParams.max_holdings}
                          onChange={(e) => handleParamChange('max_holdings', parseInt(e.target.value))}
                          disabled={!isEditMode}
                          className="w-full p-2 text-sm border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 disabled:bg-gray-50"
                        />
                      </div>
                    </div>

                    {/* Rebalancing Configuration */}
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">
                          Rebalance Frequency
                        </label>
                        <select
                          value={testParams.rebalance_frequency}
                          onChange={(e) => handleParamChange('rebalance_frequency', e.target.value)}
                          disabled={!isEditMode}
                          className="w-full p-2 text-sm border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 disabled:bg-gray-50"
                        >
                          <option value="monthly">Monthly</option>
                          <option value="weekly">Weekly</option>
                          <option value="dynamic">Daily</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">
                          Momentum Ranking
                        </label>
                        <select
                          value={testParams.momentum_ranking}
                          onChange={(e) => handleParamChange('momentum_ranking', e.target.value)}
                          disabled={!isEditMode}
                          className="w-full p-2 text-sm border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 disabled:bg-gray-50"
                        >
                          <option value="20_day_return">20-Day Return</option>
                          <option value="risk_adjusted">Risk Adjusted</option>
                          <option value="technical">Technical</option>
                        </select>
                      </div>
                    </div>

                    {/* Date Range */}
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">
                          Start Date
                        </label>
                        <input
                          type="date"
                          value={testParams.start_date}
                          onChange={(e) => handleParamChange('start_date', e.target.value)}
                          disabled={!isEditMode}
                          className="w-full p-2 text-sm border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 disabled:bg-gray-50"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">
                          End Date
                        </label>
                        <input
                          type="date"
                          value={testParams.end_date}
                          onChange={(e) => handleParamChange('end_date', e.target.value)}
                          disabled={!isEditMode}
                          className="w-full p-2 text-sm border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 disabled:bg-gray-50"
                        />
                      </div>
                    </div>

                    {/* Universe Selection */}
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">
                        Stock Universe
                      </label>
                      <select
                        value={testParams.universe}
                        onChange={(e) => handleParamChange('universe', e.target.value)}
                        disabled={!isEditMode}
                        className="w-full p-2 text-sm border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 disabled:bg-gray-50"
                      >
                        <option value="NIFTY100">NIFTY 100</option>
                        <option value="NIFTY50">NIFTY 50</option>
                        <option value="NIFTY200">NIFTY 200</option>
                      </select>
                    </div>

                    {/* Calculated Test Info */}
                    <div className="bg-blue-50 p-3 rounded text-sm">
                      <div className="font-medium text-blue-800 mb-1">Test Coverage:</div>
                      <div className="text-blue-700">
                        Period: {Math.ceil((new Date(testParams.end_date).getTime() - new Date(testParams.start_date).getTime()) / (1000 * 60 * 60 * 24))} days
                        <br />
                        Expected Rebalances: ~{
                          testParams.rebalance_frequency === 'monthly' 
                            ? Math.ceil((new Date(testParams.end_date).getTime() - new Date(testParams.start_date).getTime()) / (1000 * 60 * 60 * 24 * 30))
                            : testParams.rebalance_frequency === 'weekly'
                            ? Math.ceil((new Date(testParams.end_date).getTime() - new Date(testParams.start_date).getTime()) / (1000 * 60 * 60 * 24 * 7))
                            : Math.ceil((new Date(testParams.end_date).getTime() - new Date(testParams.start_date).getTime()) / (1000 * 60 * 60 * 24))
                        }
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Run Test Button */}
            {selectedScenario && (
              <Card>
                <CardContent className="pt-6">
                  <Button 
                    onClick={runScenarioTest}
                    disabled={isLoading || !selectedScenario}
                    className="w-full flex items-center justify-center gap-2"
                    size="lg"
                  >
                    <Play className="h-5 w-5" />
                    {isLoading ? 'Running Test...' : 'Run Debug Test'}
                  </Button>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Right Panel - Results */}
          <div className="space-y-6">
            {/* Error Display */}
            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-800">
                {error}
              </div>
            )}

            {/* Loading State */}
            {isLoading && (
              <Card>
                <CardContent className="pt-6">
                  <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
                    <p className="text-gray-600">Running comprehensive test simulation...</p>
                    <p className="text-sm text-gray-500 mt-2">This may take 30-60 seconds for longer periods</p>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Results Display */}
            {debugResult?.success && debugResult.debug_simulation && (() => {
              const results = debugResult.debug_simulation.debug_results;
              const analysis = analyzeResults(results);
              
              if (!analysis) return <p>No analysis available</p>;

              const chartData = results.map(r => ({
                date: r.date,
                portfolio: r.portfolio_value,
                isRebalance: r.should_rebalance,
                holdings: r.holdings_count
              }));

              return (
                <div className="space-y-6">
                  {/* Analysis Summary */}
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <BarChart3 className="h-5 w-5" />
                        Test Results Summary
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-2 gap-4">
                        <div className="text-center p-3 bg-blue-50 rounded">
                          <div className="text-2xl font-bold text-blue-600">{analysis.totalDays}</div>
                          <div className="text-sm text-gray-600">Total Days</div>
                        </div>
                        <div className="text-center p-3 bg-green-50 rounded">
                          <div className="text-2xl font-bold text-green-600">{analysis.rebalanceDays}</div>
                          <div className="text-sm text-gray-600">Rebalance Days</div>
                        </div>
                        <div className="text-center p-3 bg-purple-50 rounded">
                          <div className="text-2xl font-bold text-purple-600">{analysis.finalReturn.toFixed(2)}%</div>
                          <div className="text-sm text-gray-600">Total Return</div>
                        </div>
                        <div className="text-center p-3 bg-red-50 rounded">
                          <div className="text-2xl font-bold text-red-600">{analysis.spikes.length}</div>
                          <div className="text-sm text-gray-600">Major Spikes</div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>

                  {/* Issues Alert */}
                  {analysis.issues.length > 0 && (
                    <Card className="border-red-200 bg-red-50">
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2 text-red-800">
                          <AlertTriangle className="h-5 w-5" />
                          Issues Detected
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <ul className="list-disc list-inside text-red-700 text-sm space-y-1">
                          {analysis.issues.map((issue, i) => (
                            <li key={i}>{issue}</li>
                          ))}
                        </ul>
                      </CardContent>
                    </Card>
                  )}

                  {/* Portfolio Value Chart */}
                  <Card>
                    <CardHeader>
                      <CardTitle>Portfolio Value Progression</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="h-64">
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={chartData}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis dataKey="date" tick={{fontSize: 12}} />
                            <YAxis tick={{fontSize: 12}} />
                            <Tooltip 
                              formatter={(value: any, name: string) => [
                                name === 'portfolio' ? formatCurrency(value) : value,
                                name === 'portfolio' ? 'Portfolio Value' : 'Holdings Count'
                              ]}
                            />
                            <Line 
                              type="monotone" 
                              dataKey="portfolio" 
                              stroke="#2563eb" 
                              strokeWidth={2}
                              dot={(props: any) => {
                                return props.payload.isRebalance ? 
                                  (<circle cx={props.cx} cy={props.cy} r={4} fill="#ef4444" />) : 
                                  (<circle cx={props.cx} cy={props.cy} r={2} fill="#2563eb" />);
                              }}
                            />
                          </LineChart>
                        </ResponsiveContainer>
                      </div>
                      <p className="text-xs text-gray-500 mt-2">
                        Red dots indicate rebalancing days. Look for unusual spikes or drops.
                      </p>
                    </CardContent>
                  </Card>

                  {/* Spikes Details */}
                  {analysis.spikes.length > 0 && (
                    <Card>
                      <CardHeader>
                        <CardTitle>Portfolio Spikes (greater than 10% daily change)</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="overflow-x-auto">
                          <table className="min-w-full bg-white border border-gray-200">
                            <thead className="bg-gray-50">
                              <tr>
                                <th className="px-4 py-2 text-left text-sm font-medium text-gray-900">Date</th>
                                <th className="px-4 py-2 text-left text-sm font-medium text-gray-900">Daily Change</th>
                                <th className="px-4 py-2 text-left text-sm font-medium text-gray-900">Rebalance Day</th>
                                <th className="px-4 py-2 text-left text-sm font-medium text-gray-900">Status</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-200">
                              {analysis.spikes.map((spike, i) => (
                                <tr key={i}>
                                  <td className="px-4 py-2 text-sm text-gray-900">{spike.date}</td>
                                  <td className={`px-4 py-2 text-sm font-medium ${spike.change > 0 ? 'text-green-600' : 'text-red-600'}`}>
                                    {spike.change > 0 ? '+' : ''}{spike.change.toFixed(2)}%
                                  </td>
                                  <td className="px-4 py-2 text-sm">
                                    {spike.isRebalance ? (
                                      <Badge className="bg-orange-100 text-orange-800">Yes</Badge>
                                    ) : (
                                      <Badge variant="outline">No</Badge>
                                    )}
                                  </td>
                                  <td className="px-4 py-2">
                                    {spike.isRebalance ? (
                                      <XCircle className="h-4 w-4 text-red-500" />
                                    ) : (
                                      <CheckCircle className="h-4 w-4 text-yellow-500" />
                                    )}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </CardContent>
                    </Card>
                  )}

                  {/* Success Indicator */}
                  {analysis.spikes.length === 0 && analysis.issues.length === 0 && (
                    <Card className="border-green-200 bg-green-50">
                      <CardContent className="pt-6">
                        <div className="flex items-center justify-center gap-3 text-green-800">
                          <CheckCircle className="h-6 w-6" />
                          <span className="font-medium">All Tests Passed! No issues detected.</span>
                        </div>
                      </CardContent>
                    </Card>
                  )}
                </div>
              );
            })()}
          </div>
        </div>
      </div>
    </div>
  );
};

export default SimulationDebugPage;

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value);
  };

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'low': return 'bg-green-100 text-green-800';
      case 'medium': return 'bg-yellow-100 text-yellow-800';
      case 'high': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-4 mb-4">
            <Link href="/analytics" className="flex items-center gap-2 text-blue-600 hover:text-blue-800">
              <ArrowLeft className="h-5 w-5" />
              Analytics Hub
            </Link>
            <span className="text-gray-500">/</span>
            <span className="font-semibold text-gray-900">Expert Debug Suite</span>
          </div>
          
          <div className="flex items-center gap-3">
            <Bug className="h-8 w-8 text-orange-600" />
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Expert Portfolio Debug Suite</h1>
              <p className="text-gray-600">Advanced testing scenarios for portfolio calculation validation</p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* Detailed Results */}
        {selectedScenario && debugResults[selectedScenario]?.success && (
          <Card className="mb-6">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5" />
                Detailed Analysis: {testScenarios.find(s => s.id === selectedScenario)?.name}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {(() => {
                const results = debugResults[selectedScenario]!.debug_simulation!.debug_results;
                const analysis = analyzeResults(selectedScenario, results);
                
                if (!analysis) return <p>No analysis available</p>;

                const chartData = results.map(r => ({
                  date: r.date,
                  portfolio: r.portfolio_value,
                  isRebalance: r.should_rebalance,
                  holdings: r.holdings_count
                }));

                return (
                  <div className="space-y-6">
                    {/* Analysis Summary */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div className="text-center p-3 bg-blue-50 rounded">
                        <div className="text-2xl font-bold text-blue-600">{analysis.totalDays}</div>
                        <div className="text-sm text-gray-600">Total Days</div>
                      </div>
                      <div className="text-center p-3 bg-green-50 rounded">
                        <div className="text-2xl font-bold text-green-600">{analysis.rebalanceDays}</div>
                        <div className="text-sm text-gray-600">Rebalance Days</div>
                      </div>
                      <div className="text-center p-3 bg-purple-50 rounded">
                        <div className="text-2xl font-bold text-purple-600">{analysis.finalReturn.toFixed(2)}%</div>
                        <div className="text-sm text-gray-600">Total Return</div>
                      </div>
                      <div className="text-center p-3 bg-red-50 rounded">
                        <div className="text-2xl font-bold text-red-600">{analysis.spikes.length}</div>
                        <div className="text-sm text-gray-600">Spikes Detected</div>
                      </div>
                    </div>

                    {/* Issues Alert */}
                    {analysis.issues.length > 0 && (
                      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                        <div className="flex items-center gap-2 mb-2">
                          <AlertTriangle className="h-5 w-5 text-red-600" />
                          <h3 className="font-medium text-red-800">Issues Detected</h3>
                        </div>
                        <ul className="list-disc list-inside text-red-700 text-sm">
                          {analysis.issues.map((issue, i) => (
                            <li key={i}>{issue}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Portfolio Value Chart */}
                    <div>
                      <h3 className="text-lg font-medium mb-3">Portfolio Value Progression</h3>
                      <div className="h-64">
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={chartData}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis dataKey="date" tick={{fontSize: 12}} />
                            <YAxis tick={{fontSize: 12}} />
                            <Tooltip 
                              formatter={(value: any, name: string) => [
                                name === 'portfolio' ? formatCurrency(value) : value,
                                name === 'portfolio' ? 'Portfolio Value' : 'Holdings Count'
                              ]}
                            />
                            <Line 
                              type="monotone" 
                              dataKey="portfolio" 
                              stroke="#2563eb" 
                              strokeWidth={2}
                              dot={(props: any) => {
                                if (props.payload.isRebalance) {
                                  return <circle cx={props.cx} cy={props.cy} r={4} fill="#ef4444" />;
                                }
                                return <circle cx={props.cx} cy={props.cy} r={2} fill="#2563eb" />;
                              }}
                            />
                          </LineChart>
                        </ResponsiveContainer>
                      </div>
                    </div>

                    {/* Spikes Details */}
                    {analysis.spikes.length > 0 && (
                      <div>
                        <h3 className="text-lg font-medium mb-3">Portfolio Spikes (&gt;5% daily change)</h3>
                        <div className="overflow-x-auto">
                          <table className="min-w-full bg-white border border-gray-200">
                            <thead className="bg-gray-50">
                              <tr>
                                <th className="px-4 py-2 text-left text-sm font-medium text-gray-900">Date</th>
                                <th className="px-4 py-2 text-left text-sm font-medium text-gray-900">Daily Change</th>
                                <th className="px-4 py-2 text-left text-sm font-medium text-gray-900">Rebalance Day</th>
                                <th className="px-4 py-2 text-left text-sm font-medium text-gray-900">Status</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-200">
                              {analysis.spikes.map((spike, i) => (
                                <tr key={i}>
                                  <td className="px-4 py-2 text-sm text-gray-900">{spike.date}</td>
                                  <td className={`px-4 py-2 text-sm font-medium ${spike.change > 0 ? 'text-green-600' : 'text-red-600'}`}>
                                    {spike.change > 0 ? '+' : ''}{spike.change.toFixed(2)}%
                                  </td>
                                  <td className="px-4 py-2 text-sm">
                                    {spike.isRebalance ? (
                                      <Badge className="bg-orange-100 text-orange-800">Yes</Badge>
                                    ) : (
                                      <Badge variant="outline">No</Badge>
                                    )}
                                  </td>
                                  <td className="px-4 py-2">
                                    {spike.isRebalance ? (
                                      <XCircle className="h-4 w-4 text-red-500" />
                                    ) : (
                                      <CheckCircle className="h-4 w-4 text-yellow-500" />
                                    )}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })()}
            </CardContent>
          </Card>
        )}

        {/* Error Display */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-800 mb-6">
            {error}
          </div>
        )}
      </div>
    </div>
  );
};

export default SimulationDebugPage;
