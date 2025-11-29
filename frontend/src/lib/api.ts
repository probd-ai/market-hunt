import { URLConfig, URLFormData, DataOverview, ProcessingResponse, SymbolMapping, StockMappingsResponse } from '@/types';

const API_BASE = '/api';
const BACKEND_API = 'http://localhost:3001/api';

class APIClient {
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ error: 'Request failed' }));
      throw new Error(errorData.error || `HTTP ${response.status}`);
    }

    return response.json();
  }

  private async directRequest<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const response = await fetch(`${BACKEND_API}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ error: 'Request failed' }));
      throw new Error(errorData.error || `HTTP ${response.status}`);
    }

    return response.json();
  }

  // URL Management
  async getUrls(): Promise<URLConfig[]> {
    try {
      return await this.request<URLConfig[]>('/urls');
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : 'Failed to fetch URLs');
    }
  }

  async createUrl(data: URLFormData): Promise<URLConfig> {
    try {
      return await this.request<URLConfig>('/urls', {
        method: 'POST',
        body: JSON.stringify(data),
      });
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : 'Failed to create URL');
    }
  }

  async updateUrl(id: string, data: URLFormData): Promise<URLConfig> {
    try {
      return await this.request<URLConfig>(`/urls/manage`, {
        method: 'PUT',
        body: JSON.stringify({ id, ...data }),
      });
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : 'Failed to update URL');
    }
  }

  async deleteUrl(id: string): Promise<void> {
    try {
      await this.request(`/urls/manage?id=${encodeURIComponent(id)}`, {
        method: 'DELETE',
      });
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : 'Failed to delete URL');
    }
  }

  // Backward compatibility alias for createUrl
  async addUrl(data: URLFormData): Promise<URLConfig> {
    return this.createUrl(data);
  }

  // Data Management
  async getDataOverview(): Promise<DataOverview> {
    try {
      return await this.request<DataOverview>('/data');
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : 'Failed to fetch data overview');
    }
  }

  async processUrls(urlIds: string[]): Promise<ProcessingResponse> {
    try {
      return await this.request<ProcessingResponse>('/data', {
        method: 'POST',
        body: JSON.stringify({ url_ids: urlIds }),
      });
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : 'Failed to process URLs');
    }
  }

  // Stock Data Management
  async getSymbolMappings(filters?: SymbolMappingFilters & {
    include_up_to_date?: boolean;
    limit?: number;
    offset?: number;
  }): Promise<SymbolMappingResponse> {
    try {
      let url = '/stock/mappings';
      const queryParams = [];
      
      if (filters?.index_name) {
        queryParams.push(`index_name=${encodeURIComponent(filters.index_name)}`);
      }
      if (filters?.industry) {
        queryParams.push(`industry=${encodeURIComponent(filters.industry)}`);
      }
      if (filters?.symbol_search) {
        queryParams.push(`symbol_search=${encodeURIComponent(filters.symbol_search)}`);
      }
      if (filters?.mapped_only !== undefined) {
        queryParams.push(`mapped_only=${filters.mapped_only}`);
      }
      if (filters?.include_up_to_date !== undefined) {
        queryParams.push(`include_up_to_date=${filters.include_up_to_date}`);
      }
      if (filters?.limit !== undefined) {
        queryParams.push(`limit=${filters.limit}`);
      }
      if (filters?.offset !== undefined) {
        queryParams.push(`offset=${filters.offset}`);
      }
      
      if (queryParams.length > 0) {
        url += `?${queryParams.join('&')}`;
      }

      return await this.request<SymbolMappingResponse>(url); // Use request instead of directRequest for proxy
    } catch (error) {
      console.error('Failed to fetch symbol mappings:', error);
      throw new Error(error instanceof Error ? error.message : 'Failed to fetch symbol mappings');
    }
  }

  // Backward compatibility alias for getSymbolMappings
  async getStockMappings(filters?: SymbolMappingFilters & {
    include_up_to_date?: boolean;
    limit?: number;
    offset?: number;
  }): Promise<SymbolMappingResponse> {
    return this.getSymbolMappings(filters);
  }

  async getIndicatorData(symbol: string, indicator: string, params: any): Promise<any> {
    try {
      const requestBody = {
        symbol,
        indicator_type: indicator, // Map 'indicator' to 'indicator_type' for backend
        start_date: params.startDate,
        end_date: params.endDate,
        base_symbol: params.baseSymbol,
        s1: params.s1,
        m2: params.m2,
        l3: params.l3,
        strength: params.strength,
        w_long: params.w_long,
        w_mid: params.w_mid,
        w_short: params.w_short,
        deadband_frac: params.deadband_frac
      };
      
      return await this.request(`/stock/indicators`, {
        method: 'POST',
        body: JSON.stringify(requestBody)
      });
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : 'Failed to fetch indicator data');
    }
  }

  async updateUpToDateStatus(symbols?: string[]): Promise<{ success: boolean; message: string; updated_count: number }> {
    try {
      return await this.directRequest(`/stock/mappings/update-status`, {
        method: 'POST',
        body: JSON.stringify({ symbols })
      });
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : 'Failed to update up-to-date status');
    }
  }

  async refreshSymbolMappings(): Promise<{ success: boolean; message: string; total_mappings: number }> {
    try {
      return await this.directRequest(`/stock/mappings/refresh`, {
        method: 'POST'
      });
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : 'Failed to refresh symbol mappings');
    }
  }

  // Backward compatibility alias for refreshSymbolMappings
  async refreshStockMappings(): Promise<{ success: boolean; message: string; total_mappings: number }> {
    return this.refreshSymbolMappings();
  }

  async getStockData(symbol: string, startDate?: string, endDate?: string, limit: number = 5000): Promise<StockDataResponse> {
    try {
      const params = new URLSearchParams();
      if (startDate) params.append('start_date', startDate);
      if (endDate) params.append('end_date', endDate);
      if (limit) params.append('limit', limit.toString());

      const url = `/stock/data/${encodeURIComponent(symbol)}${params.toString() ? `?${params.toString()}` : ''}`;
      return await this.request<StockDataResponse>(url); // Use request instead of directRequest for proxy
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : 'Failed to fetch stock data');
    }
  }

  async getStockDataStatistics(): Promise<StockDataStatistics> {
    try {
      return await this.directRequest<StockDataStatistics>('/stock/statistics');
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : 'Failed to fetch stock data statistics');
    }
  }

  async checkDataGaps(request: { symbol?: string; symbols?: string[]; index_name?: string; industry?: string; start_date: string; end_date: string; full_check?: boolean }): Promise<DataGapInfo[]> {
    try {
      // Build symbols array based on the request
      let symbols: string[] = [];
      
      if (request.symbol) {
        symbols = [request.symbol];
      } else if (request.symbols) {
        symbols = request.symbols;
      } else if (request.index_name) {
        // For index, get all symbols from that index
        const mappings = await this.getSymbolMappings();
        symbols = mappings.mappings
          .filter((mapping: SymbolMapping) => mapping.index_names?.includes(request.index_name!))
          .map((mapping: SymbolMapping) => mapping.symbol);
      } else if (request.industry) {
        // For industry, get all symbols from that industry
        const mappings = await this.getSymbolMappings();
        symbols = mappings.mappings
          .filter((mapping: SymbolMapping) => mapping.industry === request.industry)
          .map((mapping: SymbolMapping) => mapping.symbol);
      }

      if (symbols.length === 0) {
        return [];
      }

      const response: any = await this.request('/stock/gaps', {
        method: 'POST',
        body: JSON.stringify(symbols),
      });

      // Convert backend response to frontend format
      const gaps: DataGapInfo[] = [];
      
      if (Array.isArray(response)) {
        response.forEach((gapData: any) => {
          gaps.push({
            symbol: gapData.symbol,
            missing_dates: gapData.gap_details || [],
            first_date: gapData.date_range?.start || 'No data',
            last_date: gapData.date_range?.end || 'No data',
            total_gaps: gapData.needs_update ? 1 : 0,
            downloadable_gaps: gapData.needs_update ? 1 : 0,
            realistic_start_date: gapData.date_range?.start || request.start_date,
            user_range_start: request.start_date,
            user_range_end: request.end_date,
            user_range_gaps: gapData.needs_update ? 1 : 0,
            gaps_by_year: {},
            data_available_from: gapData.date_range?.start || request.start_date,
            data_available_until: gapData.date_range?.end || request.end_date,
            total_data_points: gapData.record_count || 0,
            full_period_gaps: gapData.needs_update || false
          });
        });
      }

      return gaps;
    } catch (error) {
      console.error('Error checking data gaps:', error);
      throw new Error(error instanceof Error ? error.message : 'Failed to check data gaps');
    }
  }

  // Backward compatibility alias for checkDataGaps
  async checkStockGaps(symbols: string[]): Promise<any[]> {
    try {
      // Call the gaps API directly and return the StockGapStatus objects
      const response: any = await this.request('/stock/gaps', {
        method: 'POST',
        body: JSON.stringify(symbols),
      });
      
      return response; // Return the StockGapStatus array directly
    } catch (error) {
      console.error('Error checking stock gaps:', error);
      throw new Error(error instanceof Error ? error.message : 'Failed to check stock gaps');
    }
  }

  async downloadStockData(request: DownloadStockDataRequest): Promise<{ success: boolean; message: string; task_id: string }> {
    // Convert new request format to existing backend format
    const legacyRequest: any = {
      start_date: request.start_date,
      end_date: request.end_date,
      sync_mode: request.sync_mode
    };
    
    if (request.symbol) {
      legacyRequest.symbol = request.symbol;
    } else if (request.index_name) {
      legacyRequest.index_name = request.index_name;
    } else if (request.industry) {
      // Backend expects 'industry_name' not 'industry'
      legacyRequest.industry_name = request.industry;
    } else if (request.symbols) {
      legacyRequest.symbols = request.symbols;
    }
    
    try {
      const response: any = await this.directRequest('/stock/download', {
        method: 'POST',
        body: JSON.stringify(legacyRequest),
      });
      
      return {
        success: true,
        message: response.message || 'Download started successfully',
        task_id: response.task_id || 'unknown'
      };
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : 'Failed to download stock data');
    }
  }

  async loadSymbolData(symbol: string, syncMode: 'load' | 'refresh' = 'load'): Promise<{ success: boolean; message: string }> {
    try {
      const response = await this.directRequest(`/stock/data/load/${encodeURIComponent(symbol)}?sync_mode=${syncMode}`, {
        method: 'POST',
      });
      
      return response as { success: boolean; message: string };
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : 'Failed to load symbol data');
    }
  }

  async updateSymbolStatus(symbols?: string[], forceUpdate: boolean = false): Promise<{ success: boolean; message: string; updated_count: number }> {
    try {
      const response = await this.directRequest('/stock/mappings/update-status', {
        method: 'POST',
        body: JSON.stringify({
          symbols: symbols,
          force_update: forceUpdate
        }),
      });
      
      return response as { success: boolean; message: string; updated_count: number };
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : 'Failed to update symbol status');
    }
  }

  async getHistoricalProcessing(limit: number = 10): Promise<HistoricalProcessing[]> {
    // Legacy compatibility - returns completed processes from scheduler
    try {
      const schedulerData = await this.getAllProcesses();
      return schedulerData.completed.slice(-limit).map(process => ({
        _id: process.id,
        task_id: process.id,
        request_type: process.type.includes('symbol') ? 'symbol' as const : 
                     process.type.includes('index') ? 'index' as const : 'industry' as const,
        request_params: {
          symbol: process.symbol,
          index_name: process.index_name,
          industry: process.industry,
          start_date: new Date().toISOString(),
          end_date: new Date().toISOString(),
          force_refresh: false
        },
        status: process.status as 'pending' | 'running' | 'completed' | 'failed',
        progress_percentage: process.total_items > 0 ? (process.items_processed / process.total_items) * 100 : 0,
        items_processed: process.items_processed,
        total_items: process.total_items,
        started_at: new Date(process.started_at || process.created_at),
        completed_at: process.completed_at ? new Date(process.completed_at) : undefined,
        error_message: process.error_message,
        processed_symbols: [], // Not tracked in current scheduler
        failed_symbols: [] // Not tracked in current scheduler
      }));
    } catch (error) {
      console.error('Failed to get historical processing:', error);
      return [];
    }
  }

  async getTaskProgress(taskId: string): Promise<ProgressUpdate | null> {
    try {
      const progressData = await this.getProcessProgress(taskId);
      return {
        task_id: progressData.task_id,
        status: progressData.status as 'pending' | 'running' | 'completed' | 'failed',
        progress_percentage: progressData.progress,
        current_count: progressData.items_processed,
        total_count: progressData.total_items,
        current_item: progressData.current_item,
        started_at: progressData.start_time ? new Date(progressData.start_time) : new Date(),
        completed_at: progressData.estimated_completion ? new Date(progressData.estimated_completion) : undefined
      };
    } catch (error) {
      console.error('Failed to get task progress:', error);
      return null;
    }
  }

  // New Scheduler API Methods
  async getAllProcesses(): Promise<SchedulerData> {
    try {
      return await this.request<SchedulerData>('/scheduler/processes');
    } catch (error) {
      console.error('Failed to get all processes:', error);
      throw new Error(error instanceof Error ? error.message : 'Failed to get processes');
    }
  }

  async getProcessProgress(processId: string): Promise<TaskProgress> {
    try {
      return await this.directRequest<TaskProgress>(`/scheduler/processes/${processId}/progress`);
    } catch (error) {
      console.error('Failed to get process progress:', error);
      throw new Error(error instanceof Error ? error.message : 'Failed to get process progress');
    }
  }

  async cancelProcess(processId: string): Promise<{ message: string }> {
    try {
      return await this.request<{ message: string }>(`/scheduler/processes/${processId}/cancel`, {
        method: 'POST'
      });
    } catch (error) {
      console.error('Failed to cancel process:', error);
      throw new Error(error instanceof Error ? error.message : 'Failed to cancel process');
    }
  }

  async deleteProcess(processId: string): Promise<{ message: string }> {
    try {
      return await this.request<{ message: string }>(`/scheduler/processes/${processId}`, {
        method: 'DELETE'
      });
    } catch (error) {
      console.error('Failed to delete process:', error);
      throw new Error(error instanceof Error ? error.message : 'Failed to delete process');
    }
  }

  async getProcessDetails(processId: string): Promise<ProcessEntry> {
    try {
      return await this.request<ProcessEntry>(`/scheduler/processes/${processId}/details`);
    } catch (error) {
      console.error('Failed to get process details:', error);
      throw new Error(error instanceof Error ? error.message : 'Failed to get process details');
    }
  }

  async deleteStockData(request: { symbol?: string; symbols?: string[]; index_name?: string; industry?: string }): Promise<{ success: boolean; message: string; deleted_count: number }> {
    // Stub implementation - returns success response for now
    // TODO: Implement backend endpoint /api/stock/delete
    console.log('Delete stock data request:', request);
    return {
      success: true,
      message: 'Delete functionality not yet implemented',
      deleted_count: 0
    };
  }

  // Index and industry data methods
  async getIndexIndustries(indexName: string): Promise<any> {
    try {
      return await this.request(`/data/index/${encodeURIComponent(indexName)}/industries`);
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : 'Failed to get index industries');
    }
  }

  async getIndexIndustryCompanies(indexName: string, industryName: string): Promise<any> {
    try {
      return await this.request(`/data/index/${encodeURIComponent(indexName)}/industries/${encodeURIComponent(industryName)}`);
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : 'Failed to get index industry companies');
    }
  }

  async getIndustriesOverview(): Promise<any> {
    try {
      return await this.request('/industries');
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : 'Failed to get industries overview');
    }
  }

  async getIndustryCompanies(industryName: string): Promise<any> {
    try {
      return await this.request(`/industries/${encodeURIComponent(industryName)}`);
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : 'Failed to get industry companies');
    }
  }

  async getIndustryIndices(industryName: string): Promise<any> {
    try {
      return await this.request(`/industries/${encodeURIComponent(industryName)}/indices`);
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : 'Failed to get industry indices');
    }
  }

  async getIndustryIndexCompanies(industryName: string, indexName: string): Promise<any> {
    try {
      return await this.request(`/industries/${encodeURIComponent(industryName)}/indices/${encodeURIComponent(indexName)}`);
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : 'Failed to get industry index companies');
    }
  }

  // Analytics API
  async getIndexDistribution(params: {
    indexSymbol?: string;
    startDate?: string;
    endDate?: string;
    scoreRanges?: string;
    metric?: string;
    includePrice?: boolean;
    includeSymbols?: boolean;
  } = {}): Promise<any> {
    try {
      const queryParams = new URLSearchParams();
      
      if (params.indexSymbol) queryParams.append('index_symbol', params.indexSymbol);
      if (params.startDate) queryParams.append('start_date', params.startDate);
      if (params.endDate) queryParams.append('end_date', params.endDate);
      if (params.scoreRanges) queryParams.append('score_ranges', params.scoreRanges);
      if (params.metric) queryParams.append('metric', params.metric);
      if (params.includePrice !== undefined) queryParams.append('include_price', params.includePrice.toString());
      if (params.includeSymbols !== undefined) queryParams.append('include_symbols', params.includeSymbols.toString());

      const endpoint = `/analytics/index-distribution${queryParams.toString() ? '?' + queryParams.toString() : ''}`;
      return await this.directRequest(endpoint);
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : 'Failed to get index distribution data');
    }
  }

  // Simulation API
  async saveStrategy(strategy: any): Promise<any> {
    try {
      return await this.directRequest('/simulation/strategies', {
        method: 'POST',
        body: JSON.stringify(strategy)
      });
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : 'Failed to save strategy');
    }
  }

  async getStrategies(): Promise<any> {
    try {
      return await this.directRequest('/simulation/strategies');
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : 'Failed to get strategies');
    }
  }

  async updateStrategy(strategyId: string, strategy: any): Promise<any> {
    try {
      return await this.directRequest(`/simulation/strategies/${strategyId}`, {
        method: 'PUT',
        body: JSON.stringify(strategy)
      });
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : 'Failed to update strategy');
    }
  }

  async deleteStrategy(strategyId: string): Promise<any> {
    try {
      return await this.directRequest(`/simulation/strategies/${strategyId}`, {
        method: 'DELETE'
      });
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : 'Failed to delete strategy');
    }
  }

  async runSimulation(params: any): Promise<any> {
    try {
      return await this.directRequest('/simulation/run', {
        method: 'POST',
        body: JSON.stringify(params)
      });
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : 'Failed to run simulation');
    }
  }
}

export const api = new APIClient();
export const apiClient = api; // Backward compatibility alias
export default api;
