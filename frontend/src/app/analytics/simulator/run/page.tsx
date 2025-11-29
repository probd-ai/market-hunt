'use client';

import React, { useState, useEffect, Suspense, useMemo } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { DownloadTradebookButton } from '@/components/DownloadTradebookButton';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, Cell } from 'recharts';
import { 
  TrendingUp,
  Play,
  Pause,
  SkipForward,
  SkipBack,
  Home,
  ArrowLeft,
  Activity,
  Target,
  DollarSign,
  Calendar,
  BarChart3,
  FastForward,
  Rewind,
  Gauge,
  TrendingDown,
  Clock,
  Percent
} from 'lucide-react';
import { api } from '@/lib/api';

// Types for simulation
interface SimulationParams {
  strategyId: string;
  portfolioValue: number;
  rebalanceFreq: 'monthly' | 'weekly' | 'dynamic';
  rebalanceDate: 'first' | 'last' | 'mid';
  rebalanceType: 'equal_weight' | 'skewed'; // Allocation method
  universe: 'NIFTY50' | 'NIFTY100' | 'NIFTY500';
  benchmarkSymbol?: string;  // Optional benchmark override
  maxHoldings: number; // Maximum number of stocks in portfolio
  momentumRanking: '20_day_return' | 'price_roc_66d' | 'price_roc_222d' | 'risk_adjusted' | 'technical' |
                   'truevx_roc' | 'short_mean_roc' | 'mid_mean_roc' | 'long_mean_roc' | 'stock_score_roc'; // Momentum ranking method
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
  weight?: number; // Portfolio weight percentage (for display)
  holdingPeriods?: number; // Number of consecutive rebalance periods held
  allocationWeight?: number; // Skewed allocation weight (1.0 + periods * 0.3)
}

interface DayResult {
  date: string;
  portfolioValue: number;
  benchmarkValue: number;
  holdings: HoldingStock[];
  newAdded: string[];  // Array of symbol names
  exited: string[];    // Array of symbol names
  exitedDetails: HoldingStock[];  // Array of exit details with performance
  cash: number;
  totalPnL: number;
  dayPnL: number;
  benchmarkPrice: number;
  // Brokerage-related fields
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

interface RebalancePeriod {
  startDate: string;
  endDate: string;
  periodLabel: string;
  startValue: number;
  endValue: number;
  returnPercent: number;
  holdings: HoldingStock[];
  stockPerformance: Array<{
    symbol: string;
    companyName: string;
    startPrice: number;
    endPrice: number;
    returnPercent: number;
    weight: number;
  }>;
}

interface PeriodReturn {
  periodLabel: string;
  startDate: string;
  endDate: string;
  returnPercent: number;
  periodType: 'monthly' | 'quarterly' | 'yearly';
}

interface SimulationResult {
  params: SimulationParams;
  benchmark_symbol: string;  // Actual benchmark symbol used
  results: DayResult[];
  chargeAnalytics?: {
    total_cumulative_charges: number;
    charge_impact_percent: number;
    total_rebalances: number;
    avg_cost_per_rebalance: number;
    charge_drag_on_returns: number;
    theoretical_return_without_charges: number;
    charge_as_percent_of_final_value: number;
    component_breakdown?: {
      stt: number;
      transaction_charges: number;
      sebi_charges: number;
      stamp_duty: number;
      brokerage: number;
      gst: number;
      total_buy_charges: number;
      total_sell_charges: number;
    };
  };
  summary: {
    totalReturn: number;
    benchmarkReturn: number;
    alpha: number;
    maxDrawdown: number;
    sharpeRatio: number;
    totalTrades: number;
    // Brokerage summary fields
    brokerageEnabled?: boolean;
    chargeImpact?: number;
    theoreticalReturnWithoutCharges?: number | null;
  };
}

const SimulationRunnerContent = () => {
  const searchParams = useSearchParams();
  const [simulationParams, setSimulationParams] = useState<SimulationParams | null>(null);
  const [simulationResult, setSimulationResult] = useState<SimulationResult | null>(null);
  const [currentDayIndex, setCurrentDayIndex] = useState(0);
  
  // Update sessionStorage when day index changes (for navigation restoration)
  useEffect(() => {
    if (simulationResult) {
      try {
        sessionStorage.setItem('currentDayIndex', currentDayIndex.toString());
      } catch (e) {
        // Silently fail if sessionStorage is unavailable
      }
    }
  }, [currentDayIndex, simulationResult]);
  const [isAutoPlaying, setIsAutoPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [autoPlaySpeed, setAutoPlaySpeed] = useState(1000); // milliseconds
  const [selectedRebalancePeriod, setSelectedRebalancePeriod] = useState<RebalancePeriod | null>(null);
  const [activeReturnType, setActiveReturnType] = useState<'rebalance' | 'monthly' | 'quarterly' | 'yearly'>('rebalance');
  const [isRestoredFromCache, setIsRestoredFromCache] = useState(false);

  // Parse URL parameters
  useEffect(() => {
    // Check if this is a new simulation request (has URL params) vs navigation (no params but has cache)
    const hasUrlParams = searchParams.get('strategyId') !== null;
    
    // First, try to restore from sessionStorage ONLY if navigating back (no new URL params)
    if (!hasUrlParams) {
      try {
        const storedResult = sessionStorage.getItem('simulationResult');
        const storedParams = sessionStorage.getItem('simulationParams');
        const storedDayIndex = sessionStorage.getItem('currentDayIndex');
        
        if (storedResult && storedParams) {
          const result = JSON.parse(storedResult);
          const params = JSON.parse(storedParams);
          const dayIndex = storedDayIndex ? parseInt(storedDayIndex) : 0;
          
          setSimulationResult(result);
          setSimulationParams(params);
          setCurrentDayIndex(dayIndex);
          setIsLoading(false);
          setIsRestoredFromCache(true);
          return; // Don't run simulation again!
        }
      } catch (e) {
        console.warn('Failed to restore from sessionStorage:', e);
      }
    }
    
    // New simulation request - clear old cache and parse params
    if (hasUrlParams) {
      // Clear old cache for fresh simulation
      try {
        sessionStorage.removeItem('simulationResult');
        sessionStorage.removeItem('simulationParams');
        sessionStorage.removeItem('currentDayIndex');
      } catch (e) {
        console.warn('Failed to clear cache:', e);
      }
    }
    
    const benchmarkFromUrl = searchParams.get('benchmarkSymbol');
    
    const params: SimulationParams = {
      strategyId: searchParams.get('strategyId') || '',
      portfolioValue: parseInt(searchParams.get('portfolioValue') || '100000'),
      rebalanceFreq: (searchParams.get('rebalanceFreq') as SimulationParams['rebalanceFreq']) || 'monthly',
      rebalanceDate: (searchParams.get('rebalanceDate') as SimulationParams['rebalanceDate']) || 'first',
      rebalanceType: (searchParams.get('rebalanceType') as SimulationParams['rebalanceType']) || 'equal_weight',
      universe: (searchParams.get('universe') as SimulationParams['universe']) || 'NIFTY50',
      benchmarkSymbol: benchmarkFromUrl || '50 EQL Wgt', // Default to Equal Weight Index
      maxHoldings: parseInt(searchParams.get('maxHoldings') || '10'),
      momentumRanking: (searchParams.get('momentumRanking') as SimulationParams['momentumRanking']) || '20_day_return',
      startDate: searchParams.get('startDate') || '2020-01-01',
      endDate: searchParams.get('endDate') || '2025-08-30'
    };
    
    // If no benchmark symbol in URL, update the URL to include the default
    if (!benchmarkFromUrl) {
      const currentUrl = new URL(window.location.href);
      currentUrl.searchParams.set('benchmarkSymbol', '50 EQL Wgt');
      window.history.replaceState(null, '', currentUrl.toString());
    }
    
    setSimulationParams(params);
    runSimulation(params);
  }, [searchParams]);

  // Auto-play functionality
  useEffect(() => {
    if (isAutoPlaying && simulationResult && currentDayIndex < simulationResult.results.length - 1) {
      if (autoPlaySpeed === 0) {
        // Max speed - use minimal delay to prevent infinite loop
        const timer = setTimeout(() => {
          setCurrentDayIndex(prev => prev + 1);
        }, 1); // 1ms delay to break the synchronous loop
        
        return () => clearTimeout(timer);
      } else {
        // Normal speed with timeout
        const timer = setTimeout(() => {
          setCurrentDayIndex(prev => prev + 1);
        }, autoPlaySpeed);
        
        return () => clearTimeout(timer);
      }
    } else if (isAutoPlaying && simulationResult && currentDayIndex >= simulationResult.results.length - 1) {
      setIsAutoPlaying(false);
    }
  }, [isAutoPlaying, currentDayIndex, simulationResult, autoPlaySpeed]);

  const runSimulation = async (params: SimulationParams) => {
    try {
      setIsLoading(true);
      setError(null);
      setIsRestoredFromCache(false); // Reset cache flag for new simulation
      
      // Clear old cache before running new simulation
      try {
        sessionStorage.removeItem('simulationResult');
        sessionStorage.removeItem('simulationParams');
        sessionStorage.removeItem('currentDayIndex');
      } catch (e) {
        console.warn('Failed to clear old cache:', e);
      }
      
      // Convert params to the format expected by the API
      const apiParams = {
        strategy_id: params.strategyId,
        portfolio_base_value: params.portfolioValue,
        rebalance_frequency: params.rebalanceFreq,
        rebalance_date: params.rebalanceDate,
        rebalance_type: params.rebalanceType, // Add rebalance type parameter
        universe: params.universe,
        benchmark_symbol: params.benchmarkSymbol || '50 EQL Wgt', // Always include benchmark
        max_holdings: params.maxHoldings,
        momentum_ranking: params.momentumRanking,
        start_date: params.startDate,
        end_date: params.endDate
      };
      
      // Call the real API
      const response = await api.runSimulation(apiParams);
      
      if (response.success && response.simulation) {
        // Transform the API response to match frontend interface
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
              weight: holding.weight, // Portfolio weight percentage
              holdingPeriods: holding.holding_periods, // Number of consecutive periods held
              allocationWeight: holding.allocation_weight // Skewed allocation weight
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
            // Brokerage-related data
            dailyCharges: day.daily_charges || { total_charges: 0, buy_charges: 0, sell_charges: 0 },
            cumulativeCharges: day.cumulative_charges || 0,
            chargeImpactPercent: day.charge_impact_percent || 0,
            brokerageEnabled: day.brokerage_enabled || false,
            exchangeUsed: day.exchange_used || null
          })),
          // Add charge analytics to simulation result
          chargeAnalytics: response.simulation.charge_analytics || null,
          summary: {
            totalReturn: response.simulation.summary.total_return,
            benchmarkReturn: response.simulation.summary.benchmark_return,
            alpha: response.simulation.summary.alpha,
            maxDrawdown: response.simulation.summary.max_drawdown,
            sharpeRatio: response.simulation.summary.sharpe_ratio,
            totalTrades: response.simulation.summary.total_trades,
            // Add brokerage summary data
            brokerageEnabled: response.simulation.summary.brokerage_enabled || false,
            chargeImpact: response.simulation.summary.charge_impact || 0,
            theoreticalReturnWithoutCharges: response.simulation.summary.theoretical_return_without_charges || null
          }
        };
        
        setSimulationResult(simulationData);
        setCurrentDayIndex(0);
        
        // Store simulation data in sessionStorage for detailed view (avoid recalculation)
        try {
          sessionStorage.setItem('simulationResult', JSON.stringify(simulationData));
          sessionStorage.setItem('simulationParams', JSON.stringify(params));
          sessionStorage.setItem('currentDayIndex', '0'); // Reset to day 0 on new simulation
        } catch (e) {
          console.warn('Failed to store simulation data in sessionStorage:', e);
        }
      } else {
        // Fallback to mock data if API fails
        const mockResult: SimulationResult = {
          params,
          benchmark_symbol: params.benchmarkSymbol || '50 EQL Wgt', // Use specified benchmark
          results: generateMockSimulationResults(params),
          summary: {
            totalReturn: 15.5,
            benchmarkReturn: 12.3,
            alpha: 3.2,
            maxDrawdown: -8.5,
            sharpeRatio: 1.2,
            totalTrades: 45
          }
        };
        
        setSimulationResult(mockResult);
        setCurrentDayIndex(0);
      }
    } catch (err) {
      console.error('Simulation error:', err);
      setError('Failed to run simulation. Using mock data.');
      
      // Fallback to mock data
      const mockResult: SimulationResult = {
        params,
        benchmark_symbol: params.benchmarkSymbol || '50 EQL Wgt', // Use specified benchmark
        results: generateMockSimulationResults(params),
        summary: {
          totalReturn: 15.5,
          benchmarkReturn: 12.3,
          alpha: 3.2,
          maxDrawdown: -8.5,
          sharpeRatio: 1.2,
          totalTrades: 45
        }
      };
      
      setSimulationResult(mockResult);
      setCurrentDayIndex(0);
    } finally {
      setIsLoading(false);
    }
  };

  const generateMockSimulationResults = (params: SimulationParams): DayResult[] => {
    // Generate mock simulation data
    const results: DayResult[] = [];
    const startDate = new Date(params.startDate);
    const endDate = new Date(params.endDate);
    const totalDays = Math.floor((endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24));
    
    let portfolioValue = params.portfolioValue;
    let benchmarkValue = params.portfolioValue;
    
    for (let i = 0; i < Math.min(totalDays, 30); i += 7) { // Weekly for demo
      const currentDate = new Date(startDate.getTime() + i * 24 * 60 * 60 * 1000);
      
      // Mock price movement
      const portfolioChange = (Math.random() - 0.48) * 0.02; // Slight positive bias
      const benchmarkChange = (Math.random() - 0.5) * 0.015;
      
      portfolioValue *= (1 + portfolioChange);
      benchmarkValue *= (1 + benchmarkChange);
      
      const mockHoldings: HoldingStock[] = [
        {
          symbol: 'TCS',
          companyName: 'Tata Consultancy Services',
          quantity: 10,
          avgPrice: 3500,
          currentPrice: 3500 * (1 + portfolioChange),
          marketValue: 35000 * (1 + portfolioChange),
          pnl: 35000 * portfolioChange,
          pnlPercent: portfolioChange * 100,
          sector: 'IT'
        },
        {
          symbol: 'INFY',
          companyName: 'Infosys Limited',
          quantity: 15,
          avgPrice: 1400,
          currentPrice: 1400 * (1 + portfolioChange),
          marketValue: 21000 * (1 + portfolioChange),
          pnl: 21000 * portfolioChange,
          pnlPercent: portfolioChange * 100,
          sector: 'IT'
        }
      ];
      
      results.push({
        date: currentDate.toISOString().split('T')[0],
        portfolioValue,
        benchmarkValue,
        holdings: mockHoldings,
        newAdded: i === 0 ? mockHoldings.map(h => h.symbol) : [],
        exited: [],
        exitedDetails: [],
        cash: portfolioValue - mockHoldings.reduce((sum, h) => sum + h.marketValue, 0),
        totalPnL: portfolioValue - params.portfolioValue,
        dayPnL: i === 0 ? 0 : portfolioValue - results[results.length - 1]?.portfolioValue || 0,
        benchmarkPrice: benchmarkValue
      });
    }
    
    return results;
  };

  // Function to calculate rebalance periods and their performance
  const calculateRebalancePeriods = (): RebalancePeriod[] => {
    if (!simulationResult || !simulationParams) return [];

    const results = simulationResult.results;
    const rebalancePeriods: RebalancePeriod[] = [];
    
    // Find rebalance dates (when newAdded or exited arrays have content)
    const rebalanceDates: number[] = [0]; // Always include first day
    
    for (let i = 1; i < results.length; i++) {
      const day = results[i];
      if ((day.newAdded && day.newAdded.length > 0) || (day.exited && day.exited.length > 0)) {
        rebalanceDates.push(i);
      }
    }
    
    // Add last day if not already included
    if (rebalanceDates[rebalanceDates.length - 1] !== results.length - 1) {
      rebalanceDates.push(results.length - 1);
    }

    // Calculate performance for each period
    for (let i = 0; i < rebalanceDates.length - 1; i++) {
      const startIndex = rebalanceDates[i];
      const endIndex = rebalanceDates[i + 1];
      
      const startDay = results[startIndex];
      const endDay = results[endIndex];
      
      const startValue = startDay.portfolioValue;
      const endValue = endDay.portfolioValue;
      const returnPercent = ((endValue / startValue) - 1) * 100;
      
      // Calculate stock performance for this period
      const stockPerformance: Array<{
        symbol: string;
        companyName: string;
        startPrice: number;
        endPrice: number;
        returnPercent: number;
        weight: number;
      }> = [];
      
      // Get holdings at start of period
      const periodHoldings = startDay.holdings || [];
      const totalValue = periodHoldings.reduce((sum, h) => sum + h.marketValue, 0);
      
      periodHoldings.forEach(holding => {
        // Find the same stock's price at end of period
        const endHolding = endDay.holdings?.find(h => h.symbol === holding.symbol);
        
        // Calculate stock return even if stock is not in holdings at end (was sold)
        let endPrice = holding.currentPrice; // Default to start price if not found
        if (endHolding) {
          endPrice = endHolding.currentPrice;
        } else {
          // If stock was sold, try to find the last known price before end date
          // For now, use the start price as fallback
          console.log(`Stock ${holding.symbol} was sold during period, using start price as end price`);
        }
        
        const stockReturn = ((endPrice / holding.currentPrice) - 1) * 100;
        const weight = totalValue > 0 ? (holding.marketValue / totalValue) * 100 : 0;
        
        stockPerformance.push({
          symbol: holding.symbol,
          companyName: holding.companyName,
          startPrice: holding.currentPrice,
          endPrice: endPrice,
          returnPercent: stockReturn,
          weight: weight
        });
      });
      
      // Sort by return percentage (descending)
      stockPerformance.sort((a, b) => b.returnPercent - a.returnPercent);
      
      const periodLabel = simulationParams.rebalanceFreq === 'monthly' 
        ? `Period ${i + 1}` 
        : simulationParams.rebalanceFreq === 'weekly' 
        ? `Week ${i + 1}`
        : `Rebalance ${i + 1}`;
      
      rebalancePeriods.push({
        startDate: startDay.date,
        endDate: endDay.date,
        periodLabel,
        startValue,
        endValue,
        returnPercent,
        holdings: periodHoldings,
        stockPerformance
      });
    }
    
    return rebalancePeriods;
  };

  // Function to calculate monthly, quarterly, and yearly returns
  const calculatePeriodReturns = (periodType: 'monthly' | 'quarterly' | 'yearly'): PeriodReturn[] => {
    if (!simulationResult) return [];

    const results = simulationResult.results;
    const periodReturns: PeriodReturn[] = [];
    
    // Group results by period
    const periodGroups: { [key: string]: typeof results } = {};
    
    results.forEach(day => {
      const date = new Date(day.date);
      let periodKey = '';
      
      if (periodType === 'monthly') {
        periodKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
      } else if (periodType === 'quarterly') {
        const quarter = Math.floor(date.getMonth() / 3) + 1;
        periodKey = `${date.getFullYear()}-Q${quarter}`;
      } else if (periodType === 'yearly') {
        periodKey = `${date.getFullYear()}`;
      }
      
      if (!periodGroups[periodKey]) {
        periodGroups[periodKey] = [];
      }
      periodGroups[periodKey].push(day);
    });
    
    // Calculate returns for each period
    Object.entries(periodGroups).forEach(([periodKey, periodDays]) => {
      if (periodDays.length > 0) {
        const sortedDays = periodDays.sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
        const firstDay = sortedDays[0];
        const lastDay = sortedDays[sortedDays.length - 1];
        
        const returnPercent = ((lastDay.portfolioValue / firstDay.portfolioValue) - 1) * 100;
        
        periodReturns.push({
          periodLabel: periodKey,
          startDate: firstDay.date,
          endDate: lastDay.date,
          returnPercent,
          periodType
        });
      }
    });
    
    return periodReturns.sort((a, b) => new Date(a.startDate).getTime() - new Date(b.startDate).getTime());
  };

  const nextDay = () => {
    if (simulationResult && currentDayIndex < simulationResult.results.length - 1) {
      setCurrentDayIndex(prev => prev + 1);
    }
  };

  const prevDay = () => {
    if (currentDayIndex > 0) {
      setCurrentDayIndex(prev => prev - 1);
    }
  };

  const toggleAutoPlay = () => {
    setIsAutoPlaying(!isAutoPlaying);
  };

  // Speed control functions
  const speedOptions = [
    { label: '0.5x', value: 2000, icon: Rewind },
    { label: '1x', value: 1000, icon: Play },
    { label: '2x', value: 500, icon: FastForward },
    { label: '4x', value: 250, icon: FastForward },
    { label: '8x', value: 125, icon: FastForward },
    { label: 'Max', value: 0, icon: FastForward }
  ];

  const changeSpeed = (newSpeed: number) => {
    setAutoPlaySpeed(newSpeed);
  };

  const getCurrentSpeedLabel = () => {
    const currentOption = speedOptions.find(option => option.value === autoPlaySpeed);
    return currentOption ? currentOption.label : '1x';
  };

  // Create FULL chart data for performance comparison (all days, not progressive)
  const fullChartData = useMemo(() => {
    if (!simulationResult || simulationResult.results.length === 0) return [];
    
    const basePortfolioValue = simulationParams?.portfolioValue || 100000;
    const baseBenchmarkValue = simulationResult.results[0]?.benchmarkValue || basePortfolioValue;
    
    return simulationResult.results.map((day, index) => ({
      date: new Date(day.date).toLocaleDateString('en-US', { 
        month: 'short', 
        day: 'numeric',
        year: '2-digit'
      }),
      portfolioReturn: ((day.portfolioValue / basePortfolioValue - 1) * 100),
      benchmarkReturn: ((day.benchmarkValue / baseBenchmarkValue - 1) * 100),
      portfolioValue: day.portfolioValue,
      benchmarkValue: day.benchmarkValue,
      dayIndex: index // Add index for navigation
    }));
  }, [simulationResult, simulationParams?.portfolioValue]);

  // Create progressive chart data for animation (slice based on currentDayIndex)
  const chartData = useMemo(() => {
    if (!fullChartData || fullChartData.length === 0) return [];
    return fullChartData.map((day, index) => ({
      ...day,
      // Add opacity for days beyond current index
      opacity: index <= currentDayIndex ? 1 : 0.3
    }));
  }, [fullChartData, currentDayIndex]);

  // Calculate rebalance periods data
  const rebalancePeriods = useMemo(() => {
    return calculateRebalancePeriods();
  }, [simulationResult, simulationParams]);

  // Chart data for rebalance periods
  const rebalanceChartData = useMemo(() => {
    return rebalancePeriods.map((period, index) => ({
      periodLabel: period.periodLabel,
      returnPercent: period.returnPercent,
      startDate: period.startDate,
      endDate: period.endDate,
      index: index
    }));
  }, [rebalancePeriods]);

  // Calculate period returns for different time periods
  const monthlyReturns = useMemo(() => calculatePeriodReturns('monthly'), [simulationResult]);
  const quarterlyReturns = useMemo(() => calculatePeriodReturns('quarterly'), [simulationResult]);
  const yearlyReturns = useMemo(() => calculatePeriodReturns('yearly'), [simulationResult]);

  // Get current chart data based on selected return type
  const currentChartData = useMemo(() => {
    if (activeReturnType === 'rebalance') return rebalanceChartData;
    
    const periodReturns = activeReturnType === 'monthly' ? monthlyReturns :
                         activeReturnType === 'quarterly' ? quarterlyReturns : yearlyReturns;
    
    return periodReturns.map((period, index) => ({
      periodLabel: period.periodLabel,
      returnPercent: period.returnPercent,
      startDate: period.startDate,
      endDate: period.endDate,
      index: index
    }));
  }, [activeReturnType, rebalanceChartData, monthlyReturns, quarterlyReturns, yearlyReturns]);

  // Helper function to get current benchmark return
  const getCurrentBenchmarkReturn = () => {
    if (!simulationResult || !currentResult || simulationResult.results.length === 0) return 0;
    const baseBenchmarkValue = simulationResult.results[0]?.benchmarkValue || (simulationParams?.portfolioValue || 100000);
    return ((currentResult.benchmarkValue / baseBenchmarkValue - 1) * 100);
  };

  const currentResult = simulationResult?.results[currentDayIndex];

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-600">Running simulation...</p>
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

  if (!simulationResult || !currentResult) {
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
            <span className="font-semibold text-gray-900">Simulation Results</span>
          </div>
        </div>

        {/* Top Control Section */}
        <Card className="mb-6">
          <CardContent className="p-6">
            <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
              {/* Universe Selection */}
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-3">Universe</h3>
                <div className="bg-blue-50 p-3 rounded-lg">
                  <div className="flex items-center justify-between">
                    <span className="font-medium">{simulationParams?.universe}</span>
                    <Badge variant="outline">
                      {simulationParams?.universe === 'NIFTY50' ? '50' : 
                       simulationParams?.universe === 'NIFTY100' ? '100' : '500'} stocks
                    </Badge>
                  </div>
                </div>
              </div>

              {/* Simulation Period */}
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-3">Simulation Period</h3>
                <div className="bg-green-50 p-3 rounded-lg">
                  <div className="text-sm">
                    <div>{simulationParams?.startDate} to {simulationParams?.endDate}</div>
                    <div className="text-gray-600 mt-1">
                      {simulationResult.results.length} trading periods
                    </div>
                    {isRestoredFromCache && (
                      <div className="text-xs text-green-600 mt-1 flex items-center gap-1">
                        ⚡ Restored from cache
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Rebalance Configuration */}
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-3">Rebalance Config</h3>
                <div className="bg-purple-50 p-3 rounded-lg">
                  <div className="text-sm">
                    <div className="font-medium">
                      {simulationParams?.rebalanceFreq === 'monthly' ? 'Monthly' : 
                       simulationParams?.rebalanceFreq === 'weekly' ? 'Weekly' : 'Dynamic'}
                    </div>
                    <div className="text-gray-600 mt-1">
                      {simulationParams?.rebalanceType === 'equal_weight' ? 'Equal Weight' : 'Skewed Allocation'}
                    </div>
                    <div className="text-gray-500 text-xs mt-1">
                      Max {simulationParams?.maxHoldings} holdings
                    </div>
                  </div>
                </div>
              </div>

              {/* Navigation Controls */}
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-3">Controls</h3>
                
                {/* Playback Controls */}
                <div className="flex items-center gap-2 mb-3">
                  <Button size="sm" onClick={prevDay} disabled={currentDayIndex === 0}>
                    <SkipBack className="h-4 w-4" />
                  </Button>
                  <Button size="sm" onClick={toggleAutoPlay}>
                    {isAutoPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                  </Button>
                  <Button 
                    size="sm" 
                    onClick={nextDay} 
                    disabled={currentDayIndex >= simulationResult.results.length - 1}
                  >
                    <SkipForward className="h-4 w-4" />
                  </Button>
                  <div className="ml-4 text-sm text-gray-600">
                    Day {currentDayIndex + 1} of {simulationResult.results.length}
                  </div>
                </div>

                {/* Speed Controls */}
                <div className="border-t border-gray-200 pt-3">
                  <div className="flex items-center gap-2 mb-2">
                    <Gauge className="h-4 w-4 text-gray-500" />
                    <span className="text-sm font-medium text-gray-700">Speed</span>
                    <Badge variant="outline" className="ml-2">
                      {getCurrentSpeedLabel()}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-1 flex-wrap">
                    {speedOptions.map((option) => (
                      <Button
                        key={option.value}
                        size="sm"
                        variant={autoPlaySpeed === option.value ? "primary" : "outline"}
                        onClick={() => changeSpeed(option.value)}
                        className="text-xs px-2 py-1"
                      >
                        <option.icon className="h-3 w-3 mr-1" />
                        {option.label}
                      </Button>
                    ))}
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    Current interval: {autoPlaySpeed === 0 ? 'Max speed (1ms)' : `${autoPlaySpeed}ms between days`}
                  </div>
                </div>
                
                {/* View All Days Button */}
                <div className="mt-4 pt-4 border-t border-gray-200">
                  <div className="text-sm font-medium text-gray-700 mb-2">Detailed View</div>
                  <Link 
                    href="/analytics/simulator/run/detailed-view"
                    className="block"
                  >
                    <Button variant="outline" className="w-full">
                      View All Days at Once
                    </Button>
                  </Link>
                </div>

                {/* Download Tradebook Button */}
                <div className="mt-4 pt-4 border-t border-gray-200">
                  <div className="text-sm font-medium text-gray-700 mb-2">Export Report</div>
                  <DownloadTradebookButton
                    simulationResults={{
                      params: {
                        strategy_id: simulationParams?.strategyId || 'unknown',
                        universe: simulationParams?.universe,
                        start_date: simulationParams?.startDate,
                        end_date: simulationParams?.endDate,
                        portfolio_base_value: simulationParams?.portfolioValue,
                        max_holdings: simulationParams?.maxHoldings,
                        rebalance_frequency: simulationParams?.rebalanceFreq,
                        rebalance_type: simulationParams?.rebalanceType,
                        momentum_ranking: simulationParams?.momentumRanking,
                        include_brokerage: simulationResult?.summary?.brokerageEnabled || false,
                        exchange: simulationResult?.results?.[0]?.exchangeUsed || 'NSE',
                        benchmark_symbol: simulationResult?.benchmark_symbol || simulationParams?.benchmarkSymbol || 'NIFTY50'
                      },
                      final_portfolio_value: simulationResult?.results?.[simulationResult.results.length - 1]?.portfolioValue || 0,
                      final_benchmark_value: simulationResult?.results?.[simulationResult.results.length - 1]?.benchmarkValue || 0,
                      initial_portfolio_value: simulationParams?.portfolioValue || 100000,
                      initial_benchmark_value: simulationResult?.results?.[0]?.benchmarkValue || simulationParams?.portfolioValue || 100000,
                      portfolio_history: simulationResult?.results?.map(result => ({
                        date: result.date,
                        portfolio_value: result.portfolioValue,
                        benchmark_value: result.benchmarkValue || result.portfolioValue,
                        rebalanced: result.newAdded?.length > 0 || result.exited?.length > 0
                      })) || [],
                      trades: simulationResult?.results?.flatMap(result => [
                        // Add buy trades for new additions
                        ...(result.newAdded || []).map(symbol => {
                          const holding = result.holdings?.find(h => h.symbol === symbol);
                          return holding ? {
                            date: result.date,
                            symbol: symbol,
                            action: 'BUY',
                            quantity: holding.quantity,
                            price: holding.avgPrice,
                            value: holding.quantity * holding.avgPrice,
                            pnl: 0
                          } : null;
                        }),
                        // Add sell trades for exits
                        ...(result.exitedDetails || []).map(exit => ({
                          date: result.date,
                          symbol: exit.symbol,
                          action: 'SELL',
                          quantity: exit.quantity,
                          price: exit.currentPrice,
                          value: exit.quantity * exit.currentPrice,
                          pnl: exit.pnl
                        }))
                      ]).filter(Boolean) || [],
                      cumulative_charges: simulationResult?.results?.[simulationResult.results.length - 1]?.cumulativeCharges || 0,
                      charge_impact_percent: simulationResult?.results?.[simulationResult.results.length - 1]?.chargeImpactPercent || 0,
                      summary: {
                        total_return: simulationResult?.summary?.totalReturn || 0,
                        benchmark_return: simulationResult?.summary?.benchmarkReturn || 0,
                        alpha: simulationResult?.summary?.alpha || 0,
                        max_drawdown: simulationResult?.summary?.maxDrawdown || 0,
                        sharpe_ratio: simulationResult?.summary?.sharpeRatio || 0,
                        total_trades: simulationResult?.summary?.totalTrades || 0,
                        brokerage_enabled: simulationResult?.summary?.brokerageEnabled || false,
                        charge_impact: simulationResult?.summary?.chargeImpact || 0,
                        theoretical_return_without_charges: simulationResult?.summary?.theoreticalReturnWithoutCharges || null
                      },
                      charge_analytics: simulationResult?.chargeAnalytics || null
                    }}
                    strategyName={`Strategy_${simulationParams?.strategyId || 'Report'}`}
                    disabled={!simulationResult?.results?.length}
                  />
                </div>
              </div>
            </div>
            
            {/* Current Date and Performance */}
            <div className="mt-6 pt-6 border-t border-gray-200">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="text-center">
                  <div className="text-2xl font-bold text-gray-900">
                    {new Date(currentResult.date).toLocaleDateString()}
                  </div>
                  <div className="text-sm text-gray-600">Current Date</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-green-600">
                    ₹{(currentResult.portfolioValue || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                  </div>
                  <div className="text-sm text-gray-600">
                    Portfolio Value
                    {simulationResult?.summary.brokerageEnabled && (
                      <span className="text-xs text-gray-500 block">(net of charges)</span>
                    )}
                  </div>
                </div>
                <div className="text-center">
                  <div className={`text-2xl font-bold ${((currentResult.portfolioValue || 0) / (simulationParams?.portfolioValue || 100000) - 1) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {((currentResult.portfolioValue || 0) / (simulationParams?.portfolioValue || 100000) - 1) >= 0 ? '+' : ''}
                    {(((currentResult.portfolioValue || 0) / (simulationParams?.portfolioValue || 100000) - 1) * 100).toFixed(2)}%
                  </div>
                  <div className="text-sm text-gray-600">
                    Total Return
                    {simulationResult?.summary.brokerageEnabled && (
                      <span className="text-xs text-gray-500 block">(after charges)</span>
                    )}
                  </div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-blue-600">
                    ₹{(currentResult.cash || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                  </div>
                  <div className="text-sm text-gray-600">Available Cash</div>
                </div>
                {/* Brokerage Charges Display */}
                {simulationResult?.summary.brokerageEnabled && (
                  <div className="text-center">
                    <div className="text-2xl font-bold text-orange-600">
                      ₹{(currentResult.cumulativeCharges || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                    </div>
                    <div className="text-sm text-gray-600">Total Charges</div>
                  </div>
                )}
                {simulationResult?.summary.brokerageEnabled && (
                  <div className="text-center">
                    <div className="text-2xl font-bold text-red-600">
                      -{(currentResult.chargeImpactPercent || 0).toFixed(3)}%
                    </div>
                    <div className="text-sm text-gray-600">Charge Impact</div>
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Middle Section - Holdings */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
          {/* Current Holdings */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Target className="h-5 w-5" />
                Current Holdings ({(currentResult.holdings || []).length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3 max-h-96 overflow-y-auto">
                {(currentResult.holdings || []).map((holding) => (
                  <div key={holding.symbol} className="border border-gray-200 rounded-lg p-3">
                    <div className="flex items-center justify-between mb-2">
                      <div>
                        <div className="font-medium text-gray-900">{holding.symbol}</div>
                        <div className="text-xs text-gray-600">{holding.companyName}</div>
                      </div>
                      <div className="text-right">
                        <Badge variant={holding.pnl >= 0 ? 'default' : 'secondary'}>
                          {holding.pnlPercent >= 0 ? '+' : ''}{holding.pnlPercent.toFixed(2)}%
                        </Badge>
                        <div className="text-xs text-gray-500 mt-1">
                          {holding.weight?.toFixed(1)}% weight
                        </div>
                      </div>
                    </div>
                    
                    {/* Display allocation info for skewed rebalancing */}
                    {simulationParams?.rebalanceType === 'skewed' && holding.holdingPeriods !== undefined && (
                      <div className="mb-2 p-2 bg-purple-50 rounded border">
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-purple-700 font-medium">
                            Held: {holding.holdingPeriods} periods
                          </span>
                          <span className="text-purple-600">
                            Weight: {holding.allocationWeight?.toFixed(1)}x
                          </span>
                        </div>
                        <div className="text-xs text-purple-600 mt-1">
                          {holding.holdingPeriods === 0 ? 'New stock' : 
                           `${((holding.allocationWeight! - 1) * 100).toFixed(0)}% extra allocation`}
                        </div>
                      </div>
                    )}
                    
                    <div className="grid grid-cols-2 gap-2 text-xs text-gray-600">
                      <div>Qty: {holding.quantity}</div>
                      <div>Avg: ₹{holding.avgPrice.toFixed(2)}</div>
                      <div>Current: ₹{holding.currentPrice.toFixed(2)}</div>
                      <div>Value: ₹{holding.marketValue.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</div>
                    </div>
                  </div>
                ))}
                {(currentResult.holdings || []).length === 0 && (
                  <div className="text-center py-6 text-gray-500">
                    No holdings for this date
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* New Additions */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-green-600">
                <TrendingUp className="h-5 w-5" />
                New Additions ({(currentResult.newAdded || []).length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3 max-h-96 overflow-y-auto">
                {(currentResult?.newAdded || []).map((symbolName: string) => {
                  // Find the stock details from holdings
                  const stockDetails = currentResult?.holdings?.find(h => h.symbol === symbolName);
                  if (!stockDetails) return null;
                  
                  return (
                    <div key={symbolName} className="bg-green-50 border border-green-200 rounded-lg p-3">
                      <div className="font-medium text-gray-900">{symbolName}</div>
                      <div className="text-xs text-gray-600">{stockDetails.companyName || symbolName}</div>
                      <div className="text-xs text-green-600 mt-1">
                        Added {(stockDetails.quantity || 0).toFixed(2)} shares @ ₹{(stockDetails.avgPrice || 0).toFixed(2)}
                      </div>
                    </div>
                  );
                })}
                {(currentResult?.newAdded || []).length === 0 && (
                  <div className="text-center py-6 text-gray-500">
                    No new additions
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Exits */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-red-600">
                <Activity className="h-5 w-5" />
                Exits ({currentResult.exited.length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3 max-h-96 overflow-y-auto">
                {currentResult.exitedDetails && currentResult.exitedDetails.length > 0 ? (
                  // Show detailed exit information with performance
                  currentResult.exitedDetails.map((exitedStock) => (
                    <div key={exitedStock.symbol} className="bg-red-50 border border-red-200 rounded-lg p-3">
                      <div className="flex items-center justify-between mb-2">
                        <div>
                          <div className="font-medium text-gray-900">{exitedStock.symbol}</div>
                          <div className="text-xs text-gray-600">{exitedStock.companyName}</div>
                        </div>
                        <Badge variant={exitedStock.pnl >= 0 ? 'default' : 'secondary'}>
                          {exitedStock.pnlPercent >= 0 ? '+' : ''}{exitedStock.pnlPercent.toFixed(2)}%
                        </Badge>
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-xs text-gray-600">
                        <div>Qty: {exitedStock.quantity.toFixed(2)}</div>
                        <div>Avg: ₹{exitedStock.avgPrice.toFixed(2)}</div>
                        <div>Exit: ₹{exitedStock.currentPrice.toFixed(2)}</div>
                        <div className={`font-medium ${exitedStock.pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          P&L: ₹{exitedStock.pnl.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                        </div>
                      </div>
                      <div className="text-xs text-red-600 mt-1">
                        Removed from portfolio
                      </div>
                    </div>
                  ))
                ) : (
                  // Fallback to basic display if no detailed exit data
                  currentResult.exited.map((symbolName: string) => (
                    <div key={symbolName} className="bg-red-50 border border-red-200 rounded-lg p-3">
                      <div className="font-medium text-gray-900">{symbolName}</div>
                      <div className="text-xs text-gray-600">{symbolName}</div>
                      <div className="text-xs text-red-600 mt-1">
                        Removed from portfolio
                      </div>
                    </div>
                  ))
                )}
                {currentResult.exited.length === 0 && (
                  <div className="text-center py-6 text-gray-500">
                    No exits
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Bottom Section - Performance Chart */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 justify-between">
              <div className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5" />
                Performance vs {simulationResult?.benchmark_symbol || simulationParams?.benchmarkSymbol || '50 EQL Wgt'}
                <Badge variant="outline" className="ml-2 text-xs">Click chart to navigate</Badge>
              </div>
              {isAutoPlaying && (
                <div className="flex items-center gap-2 text-sm text-green-600">
                  <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                  Live
                </div>
              )}
            </CardTitle>
            <p className="text-xs text-gray-500 mt-1">
              💡 Full simulation loaded - Click anywhere on the chart to jump to that day instantly
            </p>
          </CardHeader>
          <CardContent>
            <div className="h-96">
              {chartData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart 
                    data={chartData}
                    margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                    onClick={(e) => {
                      if (e && e.activeLabel) {
                        const clickedIndex = chartData.findIndex(d => d.date === e.activeLabel);
                        if (clickedIndex !== -1) {
                          setCurrentDayIndex(clickedIndex);
                          setIsAutoPlaying(false); // Stop autoplay when clicking
                        }
                      }
                    }}
                    style={{ cursor: 'pointer' }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                    <XAxis 
                      dataKey="date" 
                      tick={{ fontSize: 11 }}
                      tickMargin={5}
                      interval="preserveStartEnd"
                      axisLine={{ stroke: '#d1d5db' }}
                      tickLine={{ stroke: '#d1d5db' }}
                    />
                    <YAxis 
                      tick={{ fontSize: 11 }}
                      tickFormatter={(value) => `${value.toFixed(1)}%`}
                      domain={['dataMin - 2', 'dataMax + 2']}
                      axisLine={{ stroke: '#d1d5db' }}
                      tickLine={{ stroke: '#d1d5db' }}
                    />
                    <Tooltip 
                      contentStyle={{
                        backgroundColor: '#f8f9fa',
                        border: '1px solid #dee2e6',
                        borderRadius: '6px',
                        fontSize: '12px',
                        boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
                      }}
                      formatter={(value: number, name: string) => {
                        const displayName = name === 'portfolioReturn' ? 'Portfolio' : 'Benchmark';
                        return [`${value.toFixed(2)}%`, displayName];
                      }}
                      labelFormatter={(label) => `Date: ${label}`}
                      animationDuration={150}
                    />
                    <Line 
                      type="monotone" 
                      dataKey="portfolioReturn" 
                      stroke="#2563eb" 
                      strokeWidth={2.5}
                      dot={false}
                      activeDot={{ 
                        r: 6, 
                        fill: "#2563eb", 
                        stroke: "#ffffff", 
                        strokeWidth: 2
                      }}
                      name="portfolioReturn"
                      animationDuration={0}
                      connectNulls={false}
                      strokeOpacity={(entry: any) => entry.opacity || 1}
                    />
                    <Line 
                      type="monotone" 
                      dataKey="benchmarkReturn" 
                      stroke="#dc2626" 
                      strokeWidth={2.5}
                      dot={false}
                      activeDot={{ 
                        r: 6, 
                        fill: "#dc2626", 
                        stroke: "#ffffff", 
                        strokeWidth: 2
                      }}
                      name="benchmarkReturn"
                      animationDuration={0}
                      connectNulls={false}
                      strokeOpacity={(entry: any) => entry.opacity || 1}
                    />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full bg-gray-50 rounded-lg flex items-center justify-center">
                  <div className="text-center text-gray-500">
                    <BarChart3 className="h-12 w-12 mx-auto mb-3 text-gray-300" />
                    <p>Performance chart will load when simulation starts</p>
                  </div>
                </div>
              )}
              
              {/* Chart Legend */}
              <div className="flex justify-center gap-6 mt-4 text-sm">
                <div className="flex items-center gap-2">
                  <div className="w-4 h-0.5 bg-blue-600"></div>
                  <span>Portfolio ({((currentResult.portfolioValue / (simulationParams?.portfolioValue || 100000) - 1) * 100).toFixed(2)}%)</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-0.5 bg-red-600"></div>
                  <span>Benchmark ({getCurrentBenchmarkReturn().toFixed(2)}%)</span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Rebalance Period Analysis Section */}
      <div className="mb-6">
        <Card>
          <CardHeader className="pb-4">
            <CardTitle className="flex items-center gap-2">
              <Clock className="h-5 w-5" />
              Period Returns Analysis
            </CardTitle>
            <div className="flex items-center justify-between">
              <p className="text-sm text-gray-600">
                Analyze portfolio returns across different time periods
              </p>
              {/* Period Type Selector */}
              <div className="flex bg-gray-100 rounded-lg p-1">
                {[
                  { key: 'rebalance', label: 'Rebalance', icon: Activity },
                  { key: 'monthly', label: 'Monthly', icon: Calendar },
                  { key: 'quarterly', label: 'Quarterly', icon: BarChart3 },
                  { key: 'yearly', label: 'Yearly', icon: TrendingUp }
                ].map(({ key, label, icon: Icon }) => (
                  <button
                    key={key}
                    onClick={() => {
                      setActiveReturnType(key as any);
                      setSelectedRebalancePeriod(null); // Clear selection when switching
                    }}
                    className={`flex items-center gap-1 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                      activeReturnType === key 
                        ? 'bg-white text-blue-600 shadow-sm' 
                        : 'text-gray-600 hover:text-gray-900'
                    }`}
                  >
                    <Icon className="h-3 w-3" />
                    {label}
                  </button>
                ))}
              </div>
            </div>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              {/* Returns Chart */}
              <div className="lg:col-span-2">
                <div className="h-64">
                  {currentChartData.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart 
                        data={currentChartData}
                        margin={{ top: 10, right: 10, left: 10, bottom: 20 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                        <XAxis 
                          dataKey="periodLabel" 
                          tick={{ fontSize: 10 }}
                          tickMargin={5}
                          axisLine={{ stroke: '#d1d5db' }}
                          tickLine={{ stroke: '#d1d5db' }}
                          angle={-45}
                          textAnchor="end"
                          height={60}
                        />
                        <YAxis 
                          tick={{ fontSize: 10 }}
                          tickFormatter={(value) => `${value.toFixed(1)}%`}
                          axisLine={{ stroke: '#d1d5db' }}
                          tickLine={{ stroke: '#d1d5db' }}
                        />
                        <Tooltip 
                          contentStyle={{
                            backgroundColor: '#f8f9fa',
                            border: '1px solid #dee2e6',
                            borderRadius: '6px',
                            fontSize: '11px',
                            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
                          }}
                          formatter={(value: number) => [`${value.toFixed(2)}%`, 'Return']}
                          labelFormatter={(label, payload) => {
                            if (payload && payload[0]) {
                              const data = payload[0].payload;
                              return `${label} (${new Date(data.startDate).toLocaleDateString()} - ${new Date(data.endDate).toLocaleDateString()})`;
                            }
                            return label;
                          }}
                        />
                        <Bar 
                          dataKey="returnPercent" 
                          radius={[2, 2, 0, 0]}
                          cursor="pointer"
                          onClick={(data) => {
                            if (activeReturnType === 'rebalance' && data && rebalancePeriods[data.index]) {
                              setSelectedRebalancePeriod(rebalancePeriods[data.index]);
                            }
                          }}
                        >
                          {currentChartData.map((entry, index) => (
                            <Cell 
                              key={`cell-${index}`} 
                              fill={entry.returnPercent >= 0 ? '#10B981' : '#EF4444'} 
                            />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="h-full bg-gray-50 rounded-lg flex items-center justify-center">
                      <div className="text-center text-gray-500">
                        <BarChart3 className="h-8 w-8 mx-auto mb-2 text-gray-300" />
                        <p className="text-xs">Returns will appear when simulation starts</p>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Period Statistics */}
              <div>
                <h3 className="text-sm font-semibold mb-3">Statistics</h3>
                {currentChartData.length > 0 ? (
                  <div className="space-y-2">
                    {(() => {
                      const returns = currentChartData.map(d => d.returnPercent);
                      const positiveReturns = returns.filter(r => r > 0);
                      const negativeReturns = returns.filter(r => r < 0);
                      const avgReturn = returns.reduce((sum, r) => sum + r, 0) / returns.length;
                      const maxReturn = Math.max(...returns);
                      const minReturn = Math.min(...returns);
                      const winRate = (positiveReturns.length / returns.length) * 100;
                      
                      return (
                        <div className="grid grid-cols-2 gap-2 text-xs">
                          <div className="bg-gray-50 p-2 rounded">
                            <div className="text-gray-600">Total Periods</div>
                            <div className="font-medium">{returns.length}</div>
                          </div>
                          <div className="bg-gray-50 p-2 rounded">
                            <div className="text-gray-600">Win Rate</div>
                            <div className="font-medium">{winRate.toFixed(1)}%</div>
                          </div>
                          <div className="bg-gray-50 p-2 rounded">
                            <div className="text-gray-600">Avg Return</div>
                            <div className={`font-medium ${avgReturn >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                              {avgReturn >= 0 ? '+' : ''}{avgReturn.toFixed(2)}%
                            </div>
                          </div>
                          <div className="bg-gray-50 p-2 rounded">
                            <div className="text-gray-600">Best Period</div>
                            <div className="font-medium text-green-600">+{maxReturn.toFixed(2)}%</div>
                          </div>
                          <div className="bg-gray-50 p-2 rounded">
                            <div className="text-gray-600">Worst Period</div>
                            <div className="font-medium text-red-600">{minReturn.toFixed(2)}%</div>
                          </div>
                          <div className="bg-gray-50 p-2 rounded">
                            <div className="text-gray-600">Volatility</div>
                            <div className="font-medium">
                              {Math.sqrt(returns.reduce((sum, r) => sum + Math.pow(r - avgReturn, 2), 0) / returns.length).toFixed(2)}%
                            </div>
                          </div>
                        </div>
                      );
                    })()}
                  </div>
                ) : (
                  <div className="text-center py-8 text-gray-500 text-xs">
                    <Calendar className="h-8 w-8 mx-auto mb-2 text-gray-300" />
                    <p>Statistics will appear when simulation starts</p>
                  </div>
                )}
              </div>
            </div>

            {/* Brokerage Analytics Section - Only show when brokerage is enabled */}
            {simulationResult?.summary.brokerageEnabled && simulationResult?.chargeAnalytics && (
              <div className="mt-6 pt-4 border-t border-gray-200">
                <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
                  <DollarSign className="h-4 w-4" />
                  Brokerage Charges Analytics
                </h3>
                <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                  <div className="text-xs text-blue-700">
                    <strong>Note:</strong> Portfolio Value and Total Return shown above are <strong>net of all charges</strong>. 
                    This represents the actual amount you would have after paying all transaction costs.
                  </div>
                </div>
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                  {/* Overall Impact */}
                  <div className="space-y-3">
                    <h4 className="text-xs font-medium text-gray-700 uppercase tracking-wide">Overall Impact</h4>
                    <div className="space-y-2">
                      <div className="bg-red-50 p-3 rounded-lg">
                        <div className="text-red-600 font-semibold">
                          ₹{simulationResult.chargeAnalytics.total_cumulative_charges.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                        </div>
                        <div className="text-xs text-red-500">Total Charges Paid</div>
                      </div>
                      <div className="bg-orange-50 p-3 rounded-lg">
                        <div className="text-orange-600 font-semibold">
                          -{simulationResult.chargeAnalytics.charge_impact_percent.toFixed(3)}%
                        </div>
                        <div className="text-xs text-orange-500">Portfolio Impact</div>
                      </div>
                      <div className="bg-blue-50 p-3 rounded-lg">
                        <div className="text-blue-600 font-semibold">
                          {simulationResult.chargeAnalytics.total_rebalances}
                        </div>
                        <div className="text-xs text-blue-500">Total Rebalances</div>
                      </div>
                    </div>
                  </div>

                  {/* Charge Breakdown */}
                  {simulationResult.chargeAnalytics.component_breakdown && (
                    <div className="space-y-3">
                      <h4 className="text-xs font-medium text-gray-700 uppercase tracking-wide">Charge Components</h4>
                      <div className="space-y-2">
                        <div className="flex justify-between items-center py-1">
                          <span className="text-xs text-gray-600">STT (0.1%)</span>
                          <span className="text-xs font-medium">₹{simulationResult.chargeAnalytics.component_breakdown.stt.toFixed(0)}</span>
                        </div>
                        <div className="flex justify-between items-center py-1">
                          <span className="text-xs text-gray-600">Transaction Charges</span>
                          <span className="text-xs font-medium">₹{simulationResult.chargeAnalytics.component_breakdown.transaction_charges.toFixed(0)}</span>
                        </div>
                        <div className="flex justify-between items-center py-1">
                          <span className="text-xs text-gray-600">SEBI Charges</span>
                          <span className="text-xs font-medium">₹{simulationResult.chargeAnalytics.component_breakdown.sebi_charges.toFixed(0)}</span>
                        </div>
                        <div className="flex justify-between items-center py-1">
                          <span className="text-xs text-gray-600">Stamp Duty</span>
                          <span className="text-xs font-medium">₹{simulationResult.chargeAnalytics.component_breakdown.stamp_duty.toFixed(0)}</span>
                        </div>
                        <div className="flex justify-between items-center py-1">
                          <span className="text-xs text-gray-600">GST (18%)</span>
                          <span className="text-xs font-medium">₹{simulationResult.chargeAnalytics.component_breakdown.gst.toFixed(0)}</span>
                        </div>
                        <div className="border-t pt-2 mt-2">
                          <div className="flex justify-between items-center py-1 font-medium">
                            <span className="text-xs text-gray-800">Total</span>
                            <span className="text-xs">₹{simulationResult.chargeAnalytics.total_cumulative_charges.toFixed(0)}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Performance Comparison */}
                  <div className="space-y-3">
                    <h4 className="text-xs font-medium text-gray-700 uppercase tracking-wide">Performance Impact</h4>
                    <div className="space-y-2">
                      <div className="bg-green-50 p-3 rounded-lg">
                        <div className="text-green-600 font-semibold">
                          {simulationResult.summary.totalReturn.toFixed(2)}%
                        </div>
                        <div className="text-xs text-green-500">Actual Return (net of charges)</div>
                      </div>
                      {simulationResult.summary.theoreticalReturnWithoutCharges && (
                        <div className="bg-gray-50 p-3 rounded-lg">
                          <div className="text-gray-600 font-semibold">
                            {simulationResult.summary.theoreticalReturnWithoutCharges.toFixed(2)}%
                          </div>
                          <div className="text-xs text-gray-500">Theoretical (gross, before charges)</div>
                        </div>
                      )}
                      <div className="bg-red-50 p-3 rounded-lg">
                        <div className="text-red-600 font-semibold">
                          -{simulationResult.chargeAnalytics.charge_drag_on_returns.toFixed(3)}%
                        </div>
                        <div className="text-xs text-red-500">Return Impact from Charges</div>
                      </div>
                      <div className="bg-yellow-50 p-3 rounded-lg">
                        <div className="text-yellow-600 font-semibold">
                          ₹{simulationResult.chargeAnalytics.avg_cost_per_rebalance.toFixed(0)}
                        </div>
                        <div className="text-xs text-yellow-500">Avg Cost per Rebalance</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Rebalance Period Details - Only show for rebalance periods */}
            {activeReturnType === 'rebalance' && selectedRebalancePeriod && (
              <div className="mt-6 pt-4 border-t border-gray-200">
                <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
                  <Target className="h-4 w-4" />
                  Rebalance Period Details
                </h3>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  {/* Period Summary */}
                  <div className="bg-gray-50 rounded-lg p-3">
                    <div className="grid grid-cols-2 gap-3 text-xs">
                      <div>
                        <span className="text-gray-600">Period:</span>
                        <div className="font-medium">{selectedRebalancePeriod.periodLabel}</div>
                      </div>
                      <div>
                        <span className="text-gray-600">Return:</span>
                        <div className={`font-medium ${selectedRebalancePeriod.returnPercent >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {selectedRebalancePeriod.returnPercent >= 0 ? '+' : ''}{selectedRebalancePeriod.returnPercent.toFixed(2)}%
                        </div>
                      </div>
                      <div>
                        <span className="text-gray-600">Start:</span>
                        <div className="font-medium">{new Date(selectedRebalancePeriod.startDate).toLocaleDateString()}</div>
                      </div>
                      <div>
                        <span className="text-gray-600">End:</span>
                        <div className="font-medium">{new Date(selectedRebalancePeriod.endDate).toLocaleDateString()}</div>
                      </div>
                      <div>
                        <span className="text-gray-600">Start Value:</span>
                        <div className="font-medium">₹{selectedRebalancePeriod.startValue.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</div>
                      </div>
                      <div>
                        <span className="text-gray-600">End Value:</span>
                        <div className="font-medium">₹{selectedRebalancePeriod.endValue.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</div>
                      </div>
                    </div>
                  </div>

                  {/* Stock Performance */}
                  <div>
                    <h4 className="font-medium mb-2 flex items-center gap-2 text-xs">
                      <Percent className="h-3 w-3" />
                      Stock Performance ({selectedRebalancePeriod.stockPerformance.length} stocks)
                    </h4>
                    <div className="space-y-1 max-h-48 overflow-y-auto">
                      {selectedRebalancePeriod.stockPerformance.map((stock, index) => (
                        <div 
                          key={stock.symbol} 
                          className="flex items-center justify-between p-2 bg-white border rounded text-xs"
                        >
                          <div className="flex-1 min-w-0">
                            <div className="font-medium truncate">{stock.symbol}</div>
                            <div className="text-gray-500 text-xs truncate">{stock.companyName}</div>
                          </div>
                          <div className="text-right ml-2">
                            <div className={`font-medium ${stock.returnPercent >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                              {stock.returnPercent >= 0 ? '+' : ''}{stock.returnPercent.toFixed(1)}%
                            </div>
                            <div className="text-gray-500 text-xs">
                              {stock.weight.toFixed(1)}% wt
                            </div>
                          </div>
                          {index === 0 && stock.returnPercent > 0 && (
                            <TrendingUp className="h-3 w-3 text-green-500 ml-1" />
                          )}
                          {index === selectedRebalancePeriod.stockPerformance.length - 1 && stock.returnPercent < 0 && (
                            <TrendingDown className="h-3 w-3 text-red-500 ml-1" />
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

const SimulationRunnerPage = () => {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>
    }>
      <SimulationRunnerContent />
    </Suspense>
  );
};

export default SimulationRunnerPage;
