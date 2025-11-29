'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { 
  TrendingUp,
  Play,
  Home,
  ArrowLeft,
  Settings,
  Plus,
  Target,
  Activity,
  BarChart3,
  Calendar,
  DollarSign,
  Edit2,
  Trash2,
  MoreVertical,
  Layers
} from 'lucide-react';
import { api } from '@/lib/api';

// Types for strategy and simulation
interface StrategyRule {
  id: string;
  metric: 'truevx_score' | 'mean_short' | 'mean_mid' | 'mean_long';
  operator: '>' | '<' | '>=' | '<=' | '==' | '!=';
  threshold: number;
  name: string;
}

interface Strategy {
  id: string;
  name: string;
  description: string;
  rules: StrategyRule[];
  createdAt: string;
  lastModified: string;
}

interface SimulationConfig {
  strategyId: string;
  portfolioBaseValue: number;
  rebalanceFrequency: 'monthly' | 'weekly' | 'quarterly' | 'dynamic';
  rebalanceDate: 'first' | 'last' | 'mid';
  rebalanceType: 'equal_weight' | 'skewed'; // Allocation method
  universe: string; // Dynamic universe from database
  benchmarkSymbol?: string; // Optional custom benchmark symbol
  maxHoldings: number; // Maximum number of stocks in portfolio
  momentumRanking: '20_day_return' | 'price_roc_66d' | 'price_roc_222d' | 'risk_adjusted' | 'technical' | 
                   'truevx_roc' | 'short_mean_roc' | 'mid_mean_roc' | 'long_mean_roc' | 'stock_score_roc'; // Momentum ranking method
  startDate: string;
  endDate: string;
}

const AnalyticsSimulatorPage = () => {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [selectedStrategy, setSelectedStrategy] = useState<Strategy | null>(null);
  const [showCreateStrategy, setShowCreateStrategy] = useState(false);
  const [showSimulationConfig, setShowSimulationConfig] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [universeOptions, setUniverseOptions] = useState<Array<{value: string, label: string, stock_count: number}>>([]);

  // Edit and Delete states
  const [editingStrategy, setEditingStrategy] = useState<Strategy | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // Strategy creation states
  const [newStrategyName, setNewStrategyName] = useState('');
  const [newStrategyDescription, setNewStrategyDescription] = useState('');
  const [newStrategyRules, setNewStrategyRules] = useState<StrategyRule[]>([]);

  // Simulation config states
  const [simulationConfig, setSimulationConfig] = useState<SimulationConfig>({
    strategyId: '',
    portfolioBaseValue: 100000,
    rebalanceFrequency: 'monthly',
    rebalanceDate: 'first',
    rebalanceType: 'equal_weight', // Default to equal weight allocation
    universe: 'NIFTY50', // Default fallback, will be updated when universes load
    benchmarkSymbol: '50 EQL Wgt', // Default to Equal Weight Index
    maxHoldings: 10, // Default maximum holdings
    momentumRanking: '20_day_return', // Default momentum ranking method
    startDate: '2020-01-01',
    endDate: '2025-08-30'
  });

  const metricOptions = [
    { value: 'truevx_score', label: 'TrueVX Score', description: 'Main TrueValueX ranking score (0-100)' },
    { value: 'mean_short', label: 'Short Mean', description: 'Short-term (22-period) moving average' },
    { value: 'mean_mid', label: 'Mid Mean', description: 'Mid-term (66-period) moving average' },
    { value: 'mean_long', label: 'Long Mean', description: 'Long-term (222-period) moving average' },
  ];

  const operatorOptions = [
    { value: '>', label: 'Greater than (>)' },
    { value: '<', label: 'Less than (<)' },
    { value: '>=', label: 'Greater than or equal (>=)' },
    { value: '<=', label: 'Less than or equal (<=)' },
    { value: '==', label: 'Equal to (==)' },
    { value: '!=', label: 'Not equal to (!=)' },
  ];

  const benchmarkOptions = [
    { value: '50 EQL Wgt', label: '50 EQL Wgt (Equal Weight Index)' },
    { value: 'Nifty 50', label: 'Nifty 50 (Cap Weighted)' },
  ];

  const rebalanceTypeOptions = [
    { 
      value: 'equal_weight', 
      label: 'Equal Weight', 
      description: 'Equal allocation to all selected stocks' 
    },
    { 
      value: 'skewed', 
      label: 'Skewed (Holding Period)', 
      description: 'More allocation to stocks held for longer periods' 
    },
  ];

  // Load existing strategies and universes
  useEffect(() => {
    loadStrategies();
    loadUniverses();
  }, []);

  const loadStrategies = async () => {
    try {
      setIsLoading(true);
      
      // Load strategies from API
      const response = await api.getStrategies();
      if (response.success) {
        setStrategies(response.strategies || []);
      } else {
        console.error('Failed to load strategies:', response.error);
        setStrategies([]);
      }
    } catch (err) {
      console.error('Failed to load strategies:', err);
      setError('Failed to load strategies');
    } finally {
      setIsLoading(false);
    }
  };

  const loadUniverses = async () => {
    try {
      const response = await fetch('http://localhost:3001/api/data/universes');
      const data = await response.json();
      
      if (data.universes && Array.isArray(data.universes)) {
        setUniverseOptions(data.universes);
        console.log(`📊 Loaded ${data.universes.length} universes from database`);
      } else {
        // Fallback to hardcoded options if API fails
        console.warn('Failed to load universes from API, using fallback');
        setUniverseOptions([
          { value: 'NIFTY50', label: 'NIFTY 50 (50 stocks)', stock_count: 50 },
          { value: 'NIFTY100', label: 'NIFTY 100 (100 stocks)', stock_count: 100 },
          { value: 'NIFTY500', label: 'NIFTY 500 (500 stocks)', stock_count: 500 },
        ]);
      }
    } catch (err) {
      console.error('Failed to load universes:', err);
      // Fallback to hardcoded options
      setUniverseOptions([
        { value: 'NIFTY50', label: 'NIFTY 50 (50 stocks)', stock_count: 50 },
        { value: 'NIFTY100', label: 'NIFTY 100 (100 stocks)', stock_count: 100 },
        { value: 'NIFTY500', label: 'NIFTY 500 (500 stocks)', stock_count: 500 },
      ]);
    }
  };

  const addNewRule = () => {
    const newRule: StrategyRule = {
      id: `rule_${Date.now()}`,
      metric: 'truevx_score',
      operator: '>',
      threshold: 60,
      name: 'New Rule'
    };
    setNewStrategyRules([...newStrategyRules, newRule]);
  };

  const updateRule = (ruleId: string, updates: Partial<StrategyRule>) => {
    setNewStrategyRules(rules => 
      rules.map(rule => 
        rule.id === ruleId ? { ...rule, ...updates } : rule
      )
    );
  };

  const removeRule = (ruleId: string) => {
    setNewStrategyRules(rules => rules.filter(rule => rule.id !== ruleId));
  };

  const saveStrategy = async () => {
    try {
      setIsLoading(true);
      
      const strategyData = {
        name: newStrategyName,
        description: newStrategyDescription,
        rules: newStrategyRules
      };

      let response;
      if (editingStrategy) {
        // Update existing strategy
        response = await api.updateStrategy(editingStrategy.id, strategyData);
      } else {
        // Create new strategy
        response = await api.saveStrategy(strategyData);
      }
      
      if (response.success) {
        // Reload strategies to get the updated list
        await loadStrategies();
        
        // Reset form
        setNewStrategyName('');
        setNewStrategyDescription('');
        setNewStrategyRules([]);
        setEditingStrategy(null);
        setShowCreateStrategy(false);
      } else {
        setError(editingStrategy ? 'Failed to update strategy' : 'Failed to save strategy');
      }
      
    } catch (err) {
      console.error('Error saving strategy:', err);
      setError(editingStrategy ? 'Failed to update strategy' : 'Failed to save strategy');
    } finally {
      setIsLoading(false);
    }
  };

  const startSimulation = (strategy: Strategy) => {
    setSelectedStrategy(strategy);
    setSimulationConfig({ ...simulationConfig, strategyId: strategy.id });
    setShowSimulationConfig(true);
  };

  const editStrategy = (strategy: Strategy) => {
    setEditingStrategy(strategy);
    setNewStrategyName(strategy.name);
    setNewStrategyDescription(strategy.description);
    setNewStrategyRules(strategy.rules || []);
    setShowCreateStrategy(true);
  };

  const deleteStrategy = (strategyId: string) => {
    setShowDeleteConfirm(strategyId);
  };

  const confirmDeleteStrategy = async () => {
    if (!showDeleteConfirm) return;

    setIsDeleting(true);
    try {
      const response = await api.deleteStrategy(showDeleteConfirm);
      
      if (response.success) {
        // Refresh strategies list
        loadStrategies();
        setShowDeleteConfirm(null);
      } else {
        console.error('Failed to delete strategy');
        alert('Failed to delete strategy. Please try again.');
      }
    } catch (error) {
      console.error('Error deleting strategy:', error);
      alert('Error deleting strategy. Please try again.');
    } finally {
      setIsDeleting(false);
    }
  };

  const cancelDelete = () => {
    setShowDeleteConfirm(null);
  };

  const runSimulation = () => {
    // Navigate to simulation runner page
    const params = new URLSearchParams({
      strategyId: simulationConfig.strategyId,
      portfolioValue: simulationConfig.portfolioBaseValue.toString(),
      rebalanceFreq: simulationConfig.rebalanceFrequency,
      rebalanceDate: simulationConfig.rebalanceDate,
      rebalanceType: simulationConfig.rebalanceType, // Add rebalance type parameter
      universe: simulationConfig.universe,
      benchmarkSymbol: simulationConfig.benchmarkSymbol || '50 EQL Wgt', // Always include benchmark
      maxHoldings: simulationConfig.maxHoldings.toString(),
      momentumRanking: simulationConfig.momentumRanking,
      startDate: simulationConfig.startDate,
      endDate: simulationConfig.endDate
    });
    
    window.location.href = `/analytics/simulator/run?${params.toString()}`;
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
            <span className="font-semibold text-gray-900">Strategy Simulator</span>
          </div>
          
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">Strategy Simulator</h1>
              <p className="text-gray-600">Create and backtest trading strategies based on TrueValueX indicators</p>
            </div>
            
            <Button 
              onClick={() => setShowCreateStrategy(true)}
              className="flex items-center gap-2"
            >
              <Plus className="h-4 w-4" />
              Create Strategy
            </Button>
          </div>
        </div>

        {/* Strategies Grid */}
        {!showCreateStrategy && !showSimulationConfig && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {strategies.map((strategy) => (
              <Card key={strategy.id} className="hover:shadow-lg transition-shadow">
                <CardHeader>
                  <CardTitle className="flex items-center justify-between">
                    <span>{strategy.name}</span>
                    <Badge variant="outline">{strategy.rules.length} rules</Badge>
                  </CardTitle>
                  <p className="text-sm text-gray-600">{strategy.description}</p>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {/* Strategy Rules Preview */}
                    <div className="space-y-2">
                      <h4 className="text-sm font-medium text-gray-700">Rules:</h4>
                      {strategy.rules.slice(0, 2).map((rule) => (
                        <div key={rule.id} className="text-xs bg-gray-50 p-2 rounded">
                          {metricOptions.find(m => m.value === rule.metric)?.label} {rule.operator} {rule.threshold}
                        </div>
                      ))}
                      {strategy.rules.length > 2 && (
                        <div className="text-xs text-gray-500">
                          +{strategy.rules.length - 2} more rules
                        </div>
                      )}
                    </div>
                    
                    <div className="flex items-center justify-between pt-3 border-t">
                      <span className="text-xs text-gray-500">
                        Modified: {strategy.lastModified}
                      </span>
                      <div className="flex items-center gap-2">
                        <Button 
                          size="sm" 
                          variant="outline"
                          onClick={() => editStrategy(strategy)}
                          className="flex items-center gap-1"
                        >
                          <Edit2 className="h-3 w-3" />
                          Edit
                        </Button>
                        <Button 
                          size="sm" 
                          variant="outline"
                          onClick={() => deleteStrategy(strategy.id)}
                          className="flex items-center gap-1 text-red-600 hover:text-red-700 hover:bg-red-50"
                        >
                          <Trash2 className="h-3 w-3" />
                          Delete
                        </Button>
                        <Button 
                          size="sm" 
                          onClick={() => startSimulation(strategy)}
                          className="flex items-center gap-1"
                        >
                          <Play className="h-3 w-3" />
                          Simulate
                        </Button>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* Create Strategy Modal */}
        {showCreateStrategy && (
          <Card className="max-w-4xl mx-auto">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>{editingStrategy ? 'Edit Strategy' : 'Create New Strategy'}</span>
                <Button 
                  variant="outline" 
                  onClick={() => {
                    setShowCreateStrategy(false);
                    setEditingStrategy(null);
                    setNewStrategyName('');
                    setNewStrategyDescription('');
                    setNewStrategyRules([]);
                  }}
                >
                  Cancel
                </Button>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Basic Info */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Strategy Name
                  </label>
                  <Input
                    value={newStrategyName}
                    onChange={(e) => setNewStrategyName(e.target.value)}
                    placeholder="e.g., High Momentum Strategy"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Description
                  </label>
                  <Input
                    value={newStrategyDescription}
                    onChange={(e) => setNewStrategyDescription(e.target.value)}
                    placeholder="Brief description of the strategy"
                  />
                </div>
              </div>

              {/* Rules Section */}
              <div>
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-medium text-gray-900">Strategy Rules</h3>
                  <Button onClick={addNewRule} size="sm" variant="outline">
                    <Plus className="h-4 w-4 mr-2" />
                    Add Rule
                  </Button>
                </div>
                
                <div className="space-y-4">
                  {newStrategyRules.map((rule, index) => (
                    <div key={rule.id} className="border border-gray-200 rounded-lg p-4">
                      <div className="flex items-center justify-between mb-3">
                        <h4 className="font-medium text-gray-700">Rule {index + 1}</h4>
                        <Button 
                          size="sm" 
                          variant="outline" 
                          onClick={() => removeRule(rule.id)}
                        >
                          Remove
                        </Button>
                      </div>
                      
                      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                        <div>
                          <label className="block text-sm font-medium text-gray-600 mb-1">
                            Metric
                          </label>
                          <select
                            value={rule.metric}
                            onChange={(e) => updateRule(rule.id, { 
                              metric: e.target.value as StrategyRule['metric'] 
                            })}
                            className="w-full p-2 border border-gray-300 rounded-md text-sm"
                          >
                            {metricOptions.map((option) => (
                              <option key={option.value} value={option.value}>
                                {option.label}
                              </option>
                            ))}
                          </select>
                        </div>
                        
                        <div>
                          <label className="block text-sm font-medium text-gray-600 mb-1">
                            Operator
                          </label>
                          <select
                            value={rule.operator}
                            onChange={(e) => updateRule(rule.id, { 
                              operator: e.target.value as StrategyRule['operator'] 
                            })}
                            className="w-full p-2 border border-gray-300 rounded-md text-sm"
                          >
                            {operatorOptions.map((option) => (
                              <option key={option.value} value={option.value}>
                                {option.label}
                              </option>
                            ))}
                          </select>
                        </div>
                        
                        <div>
                          <label className="block text-sm font-medium text-gray-600 mb-1">
                            Threshold
                          </label>
                          <Input
                            type="number"
                            value={rule.threshold}
                            onChange={(e) => updateRule(rule.id, { 
                              threshold: parseFloat(e.target.value) || 0 
                            })}
                            step="0.1"
                            className="text-sm"
                          />
                        </div>
                        
                        <div>
                          <label className="block text-sm font-medium text-gray-600 mb-1">
                            Rule Name
                          </label>
                          <Input
                            value={rule.name}
                            onChange={(e) => updateRule(rule.id, { 
                              name: e.target.value 
                            })}
                            placeholder="Rule description"
                            className="text-sm"
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                  
                  {newStrategyRules.length === 0 && (
                    <div className="text-center py-8 text-gray-500">
                      <Target className="h-12 w-12 mx-auto mb-3 text-gray-300" />
                      <p>No rules defined yet. Add your first rule to get started.</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Save Button */}
              <div className="flex justify-end gap-3 pt-6 border-t">
                <Button 
                  variant="outline" 
                  onClick={() => setShowCreateStrategy(false)}
                >
                  Cancel
                </Button>
                <Button 
                  onClick={saveStrategy}
                  disabled={!newStrategyName || newStrategyRules.length === 0}
                  className="flex items-center gap-2"
                >
                  <Target className="h-4 w-4" />
                  {editingStrategy ? 'Update Strategy' : 'Save Strategy'}
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Simulation Configuration Modal */}
        {showSimulationConfig && selectedStrategy && (
          <Card className="max-w-4xl mx-auto">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>Configure Simulation - {selectedStrategy.name}</span>
                <Button 
                  variant="outline" 
                  onClick={() => setShowSimulationConfig(false)}
                >
                  Cancel
                </Button>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Portfolio Settings */}
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-4">Portfolio Settings</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Portfolio Base Value (₹)
                    </label>
                    <Input
                      type="number"
                      value={simulationConfig.portfolioBaseValue}
                      onChange={(e) => setSimulationConfig({
                        ...simulationConfig,
                        portfolioBaseValue: parseInt(e.target.value) || 100000
                      })}
                      placeholder="100000"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Universe
                    </label>
                    <select
                      value={simulationConfig.universe}
                      onChange={(e) => setSimulationConfig({
                        ...simulationConfig,
                        universe: e.target.value
                      })}
                      className="w-full p-2 border border-gray-300 rounded-md"
                    >
                      {universeOptions.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Benchmark Symbol
                    </label>
                    <select
                      value={simulationConfig.benchmarkSymbol || '50 EQL Wgt'}
                      onChange={(e) => setSimulationConfig({
                        ...simulationConfig,
                        benchmarkSymbol: e.target.value
                      })}
                      className="w-full p-2 border border-gray-300 rounded-md"
                    >
                      {benchmarkOptions.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                    <p className="text-xs text-gray-500 mt-1">
                      Benchmark for performance comparison. Default is Equal Weight Index.
                    </p>
                  </div>
                </div>
              </div>

              {/* Rebalancing Settings */}
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-4">Rebalancing Settings</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Rebalance Frequency
                    </label>
                    <select
                      value={simulationConfig.rebalanceFrequency}
                      onChange={(e) => setSimulationConfig({
                        ...simulationConfig,
                        rebalanceFrequency: e.target.value as SimulationConfig['rebalanceFrequency']
                      })}
                      className="w-full p-2 border border-gray-300 rounded-md"
                    >
                      <option value="monthly">Monthly</option>
                      <option value="weekly">Weekly</option>
                      <option value="quarterly">Quarterly</option>
                      <option value="dynamic">Dynamic (immediate)</option>
                    </select>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Rebalance Date
                    </label>
                    <select
                      value={simulationConfig.rebalanceDate}
                      onChange={(e) => setSimulationConfig({
                        ...simulationConfig,
                        rebalanceDate: e.target.value as SimulationConfig['rebalanceDate']
                      })}
                      className="w-full p-2 border border-gray-300 rounded-md"
                    >
                      <option value="first">First available date</option>
                      <option value="mid">Mid period date</option>
                      <option value="last">Last available date</option>
                    </select>
                  </div>
                </div>
                
                {/* Rebalance Type Setting */}
                <div className="mt-6">
                  <h4 className="text-base font-medium text-gray-900 mb-3">Allocation Method</h4>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Rebalance Type
                    </label>
                    <select
                      value={simulationConfig.rebalanceType}
                      onChange={(e) => setSimulationConfig({
                        ...simulationConfig,
                        rebalanceType: e.target.value as SimulationConfig['rebalanceType']
                      })}
                      className="w-full p-2 border border-gray-300 rounded-md"
                    >
                      {rebalanceTypeOptions.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                    <p className="text-xs text-gray-500 mt-1">
                      {rebalanceTypeOptions.find(o => o.value === simulationConfig.rebalanceType)?.description}
                    </p>
                  </div>
                </div>
              </div>

              {/* Portfolio Limit Settings */}
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-4">Portfolio Limit Settings</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Max Holdings
                    </label>
                    <Input
                      type="number"
                      min="1"
                      max="50"
                      value={simulationConfig.maxHoldings}
                      onChange={(e) => setSimulationConfig({
                        ...simulationConfig,
                        maxHoldings: parseInt(e.target.value) || 10
                      })}
                      className="w-full"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Maximum number of stocks to hold in portfolio
                    </p>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Momentum Ranking Method
                    </label>
                    <select
                      value={simulationConfig.momentumRanking}
                      onChange={(e) => setSimulationConfig({
                        ...simulationConfig,
                        momentumRanking: e.target.value as SimulationConfig['momentumRanking']
                      })}
                      className="w-full p-2 border border-gray-300 rounded-md"
                    >
                      <optgroup label="Price-Based Momentum">
                        <option value="20_day_return">20-Day Price Return</option>
                        <option value="price_roc_66d">66-Day Price Return</option>
                        <option value="price_roc_222d">222-Day Price Return</option>
                        <option value="risk_adjusted">Risk-Adjusted Return (Sharpe-like)</option>
                        <option value="technical">Technical Momentum (MA-based)</option>
                      </optgroup>
                      <optgroup label="Indicator-Based Momentum (22-day)">
                        <option value="truevx_roc">TrueVX Score ROC</option>
                        <option value="short_mean_roc">Short Mean ROC</option>
                        <option value="mid_mean_roc">Mid Mean ROC</option>
                        <option value="long_mean_roc">Long Mean ROC</option>
                        <option value="stock_score_roc">StockScore ROC</option>
                      </optgroup>
                    </select>
                    <p className="text-xs text-gray-500 mt-1">
                      Method used to rank stocks when portfolio limit is exceeded
                    </p>
                  </div>
                </div>
              </div>

              {/* Simulation Period */}
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-4">Simulation Period</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Start Date
                    </label>
                    <Input
                      type="date"
                      value={simulationConfig.startDate}
                      onChange={(e) => setSimulationConfig({
                        ...simulationConfig,
                        startDate: e.target.value
                      })}
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      End Date
                    </label>
                    <Input
                      type="date"
                      value={simulationConfig.endDate}
                      onChange={(e) => setSimulationConfig({
                        ...simulationConfig,
                        endDate: e.target.value
                      })}
                    />
                  </div>
                </div>
              </div>

              {/* Strategy Preview */}
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-4">Strategy Preview</h3>
                <div className="bg-gray-50 p-4 rounded-lg">
                  <h4 className="font-medium text-gray-800 mb-2">{selectedStrategy.name}</h4>
                  <p className="text-sm text-gray-600 mb-3">{selectedStrategy.description}</p>
                  <div className="space-y-1">
                    {selectedStrategy.rules.map((rule) => (
                      <div key={rule.id} className="text-sm bg-white p-2 rounded border">
                        <span className="font-medium">
                          {metricOptions.find(m => m.value === rule.metric)?.label}
                        </span>
                        <span className="mx-2">{rule.operator}</span>
                        <span className="font-medium">{rule.threshold}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex justify-end gap-3 pt-6 border-t">
                <Button 
                  variant="outline" 
                  onClick={() => setShowSimulationConfig(false)}
                >
                  Cancel
                </Button>
                <Button 
                  onClick={() => {
                    // Navigate to time-period multi-run page
                    const params = {
                      strategyId: simulationConfig.strategyId,
                      portfolioValue: simulationConfig.portfolioBaseValue,
                      rebalanceFreq: simulationConfig.rebalanceFrequency,
                      rebalanceDate: simulationConfig.rebalanceDate,
                      rebalanceType: simulationConfig.rebalanceType,
                      universe: simulationConfig.universe,
                      benchmarkSymbol: simulationConfig.benchmarkSymbol || '50 EQL Wgt',
                      maxHoldings: simulationConfig.maxHoldings,
                      momentumRanking: simulationConfig.momentumRanking,
                      startDate: simulationConfig.startDate,
                      endDate: simulationConfig.endDate
                    };
                    const encodedParams = encodeURIComponent(JSON.stringify(params));
                    window.location.href = `/analytics/simulator/multi-run?params=${encodedParams}`;
                  }}
                  variant="outline"
                  className="flex items-center gap-2"
                >
                  <Layers className="h-4 w-4" />
                  ML Simulation
                </Button>
                <Button 
                  onClick={() => {
                    // Navigate to holdings multi-dimension page
                    const params = {
                      strategyId: simulationConfig.strategyId,
                      portfolioValue: simulationConfig.portfolioBaseValue,
                      rebalanceFreq: simulationConfig.rebalanceFrequency,
                      rebalanceDate: simulationConfig.rebalanceDate,
                      rebalanceType: simulationConfig.rebalanceType,
                      universe: simulationConfig.universe,
                      benchmarkSymbol: simulationConfig.benchmarkSymbol || '50 EQL Wgt',
                      maxHoldings: simulationConfig.maxHoldings,
                      momentumRanking: simulationConfig.momentumRanking,
                      startDate: simulationConfig.startDate,
                      endDate: simulationConfig.endDate
                    };
                    const encodedParams = encodeURIComponent(JSON.stringify(params));
                    window.location.href = `/analytics/simulator/holdings-multi-run?params=${encodedParams}`;
                  }}
                  variant="outline"
                  className="flex items-center gap-2"
                >
                  <Target className="h-4 w-4" />
                  Multi-Dimension Holdings
                </Button>
                <Button 
                  onClick={runSimulation}
                  className="flex items-center gap-2"
                >
                  <Play className="h-4 w-4" />
                  Start Simulation
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Loading/Error States */}
        {isLoading && (
          <div className="text-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto"></div>
            <p className="mt-2 text-gray-600">Loading...</p>
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-800">
            {error}
          </div>
        )}

        {/* Delete Confirmation Dialog */}
        {showDeleteConfirm && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <Card className="w-full max-w-md mx-4">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-red-600">
                  <Trash2 className="h-5 w-5" />
                  Delete Strategy
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-gray-700 mb-6">
                  Are you sure you want to delete this strategy? This action cannot be undone.
                </p>
                <div className="flex gap-3 justify-end">
                  <Button 
                    variant="outline" 
                    onClick={cancelDelete}
                    disabled={isDeleting}
                  >
                    Cancel
                  </Button>
                  <Button 
                    onClick={confirmDeleteStrategy}
                    disabled={isDeleting}
                    className="bg-red-600 hover:bg-red-700 text-white"
                  >
                    {isDeleting ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                        Deleting...
                      </>
                    ) : (
                      <>
                        <Trash2 className="h-4 w-4 mr-2" />
                        Delete
                      </>
                    )}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
};

export default AnalyticsSimulatorPage;
