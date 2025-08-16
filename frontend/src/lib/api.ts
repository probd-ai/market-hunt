import { URLConfig, URLFormData, DataOverview, ProcessingResponse, SymbolMapping, SymbolMappingResponse, StockPriceData, StockDataResponse, StockDataStatistics, DownloadStockDataRequest, SymbolMappingFilters, ProgressUpdate, HistoricalProcessing, DataGapInfo, ProcessEntry, TaskProgress, SchedulerData } from '@/types';

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
        queryParams.push(`index_filter=${encodeURIComponent(filters.index_name)}`);
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

      return await this.request<SymbolMappingResponse>(url);
    } catch (error) {
      console.error('Failed to fetch symbol mappings:', error);
      throw new Error(error instanceof Error ? error.message : 'Failed to fetch symbol mappings');
    }
  }

  async updateUpToDateStatus(symbols?: string[]): Promise<{ success: boolean; message: string; updated_count: number }> {
    try {
      return await this.request(`/stock/mappings/update-status`, {
        method: 'POST',
        body: JSON.stringify({ symbols })
      });
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : 'Failed to update up-to-date status');
    }
  }

  async refreshSymbolMappings(): Promise<{ success: boolean; message: string; total_mappings: number }> {
    try {
      return await this.request(`/stock/mappings/refresh`, {
        method: 'POST'
      });
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : 'Failed to refresh symbol mappings');
    }
  }

  async getStockData(symbol: string, startDate?: string, endDate?: string, limit: number = 100): Promise<StockDataResponse> {
    try {
      const params = new URLSearchParams();
      if (startDate) params.append('start_date', startDate);
      if (endDate) params.append('end_date', endDate);
      if (limit) params.append('limit', limit.toString());

      const url = `/stock/data/${encodeURIComponent(symbol)}${params.toString() ? `?${params.toString()}` : ''}`;
      return await this.request<StockDataResponse>(url);
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : 'Failed to fetch stock data');
    }
  }

  async getStockDataStatistics(): Promise<StockDataStatistics> {
    try {
      return await this.request<StockDataStatistics>('/stock/statistics');
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : 'Failed to fetch stock data statistics');
    }
  }

  async checkDataGaps(request: { symbol?: string; symbols?: string[]; index_name?: string; industry?: string; start_date: string; end_date: string; full_check?: boolean }): Promise<DataGapInfo[]> {
    try {
      // Use the backend gaps API for accurate gap analysis
      const gapRequest: any = {
        start_date: request.start_date,
        end_date: request.end_date
      };

      if (request.symbol) {
        gapRequest.symbol = request.symbol;
      } else if (request.index_name) {
        gapRequest.index_name = request.index_name;
      } else if (request.industry) {
        gapRequest.industry = request.industry;
      }

      const response: any = await this.directRequest('/stock/gaps', {
        method: 'POST',
        body: JSON.stringify(gapRequest),
      });

      // Convert backend response to frontend format
      const gaps: DataGapInfo[] = [];
      
      if (request.symbol && response.gaps) {
        const gapData = response.gaps;
        gaps.push({
          symbol: request.symbol,
          missing_dates: gapData.gaps?.map((gap: any) => `${gap.start} to ${gap.end}`) || [],
          first_date: gapData.has_data ? 'Has data' : 'No data available',
          last_date: gapData.has_data ? 'Current' : 'No data available',
          total_gaps: gapData.total_missing_days || 0,
          downloadable_gaps: gapData.total_missing_days || 0,
          realistic_start_date: gapData.date_range?.start || request.start_date,
          user_range_start: request.start_date,
          user_range_end: request.end_date,
          user_range_gaps: gapData.total_missing_days || 0,
          gaps_by_year: gapData.yearly_breakdown?.reduce((acc: any, year: any) => {
            if (year.missing_days > 0) { // Only include years with actual gaps
              acc[year.year] = year.missing_days;
            }
            return acc;
          }, {}) || {},
          data_available_from: gapData.date_range?.start || request.start_date,
          data_available_until: gapData.date_range?.end || request.end_date,
          total_data_points: gapData.total_actual_days || 0,
          full_period_gaps: (gapData.total_missing_days || 0) > 0
        });
      } else if (response.gaps) {
        // Handle multiple symbols (index/industry)
        Object.entries(response.gaps).forEach(([symbol, gapData]: [string, any]) => {
          gaps.push({
            symbol,
            missing_dates: gapData.gaps?.map((gap: any) => `${gap.start} to ${gap.end}`) || [],
            first_date: gapData.has_data ? 'Has data' : 'No data available',
            last_date: gapData.has_data ? 'Current' : 'No data available',
            total_gaps: gapData.total_missing_days || 0,
            downloadable_gaps: gapData.total_missing_days || 0,
            realistic_start_date: gapData.date_range?.start || request.start_date,
            user_range_start: request.start_date,
            user_range_end: request.end_date,
            user_range_gaps: gapData.total_missing_days || 0,
            gaps_by_year: gapData.yearly_breakdown?.reduce((acc: any, year: any) => {
              acc[year.year] = year.missing_days;
              return acc;
            }, {}) || {},
            data_available_from: gapData.date_range?.start || 'No data',
            data_available_until: gapData.date_range?.end || 'No data',
            total_data_points: gapData.total_actual_days || 0,
            full_period_gaps: (gapData.total_missing_days || 0) > 0
          });
        });
      }

      return gaps;
    } catch (error) {
      console.error('Error checking data gaps:', error);
      throw new Error(error instanceof Error ? error.message : 'Failed to check data gaps');
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
      const response: any = await this.request('/stock/download', {
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
      return await this.request<TaskProgress>(`/scheduler/processes/${processId}/progress`);
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
}

export const api = new APIClient();
export default api;
