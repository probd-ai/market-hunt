import { URLConfig, URLFormData, DataOverview, ProcessingResponse, SymbolMapping, StockPriceData, StockDataResponse, StockDataStatistics, DownloadStockDataRequest, SymbolMappingFilters, ProgressUpdate, HistoricalProcessing, DataGapInfo } from '@/types';

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
  async getSymbolMappings(filters?: SymbolMappingFilters): Promise<SymbolMapping[]> {
    try {
      const queryParams = new URLSearchParams();
      if (filters?.mapped_only) queryParams.append('mapped_only', 'true');
      if (filters?.index_name) queryParams.append('index_name', filters.index_name);
      if (filters?.industry) queryParams.append('industry', filters.industry);

      const url = `/stock/mappings${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;
      const response = await this.directRequest<{
        total_mappings: number;
        mapped_count: number;
        mappings: SymbolMapping[];
      }>(url);
      
      // Extract the mappings array from the response
      return response.mappings || [];
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : 'Failed to fetch symbol mappings');
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

  async getStockData(symbol: string, startDate?: string, endDate?: string, limit: number = 100): Promise<StockDataResponse> {
    try {
      const params = new URLSearchParams();
      if (startDate) params.append('start_date', startDate);
      if (endDate) params.append('end_date', endDate);
      if (limit) params.append('limit', limit.toString());

      const url = `/stock/data/${encodeURIComponent(symbol)}${params.toString() ? `?${params.toString()}` : ''}`;
      return await this.directRequest<StockDataResponse>(url);
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
          missing_dates: gapData.gaps.map((gap: any) => `${gap.start} to ${gap.end}`),
          first_date: gapData.has_data ? 'Has data' : 'No data available',
          last_date: gapData.has_data ? 'Current' : 'No data available',
          total_gaps: gapData.total_missing_days,
          downloadable_gaps: gapData.total_missing_days,
          realistic_start_date: gapData.date_range.start,
          user_range_start: request.start_date,
          user_range_end: request.end_date,
          user_range_gaps: gapData.total_missing_days,
          gaps_by_year: gapData.yearly_breakdown.map((year: any) => ({
            year: year.year,
            missing_days: year.missing_days,
            total_days: year.expected_days
          })),
          data_available_from: gapData.date_range.start,
          data_available_until: gapData.date_range.end,
          total_data_points: gapData.total_actual_days,
          full_period_gaps: gapData.total_missing_days > 0
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
            gaps_by_year: gapData.yearly_breakdown?.map((year: any) => ({
              year: year.year,
              missing_days: year.missing_days,
              total_days: year.expected_days
            })) || [],
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

  async getHistoricalProcessing(limit: number = 10): Promise<HistoricalProcessing[]> {
    // Stub implementation - returns empty array for now
    // TODO: Implement backend endpoint /api/stock/history
    return [];
  }

  async getTaskProgress(taskId: string): Promise<ProgressUpdate | null> {
    // Stub implementation - returns null for now
    // TODO: Implement backend endpoint /api/stock/tasks/{taskId}/progress
    return null;
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
      return await this.directRequest(`/data/index/${encodeURIComponent(indexName)}/industries`);
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : 'Failed to get index industries');
    }
  }

  async getIndexIndustryCompanies(indexName: string, industryName: string): Promise<any> {
    try {
      return await this.directRequest(`/data/index/${encodeURIComponent(indexName)}/industries/${encodeURIComponent(industryName)}`);
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : 'Failed to get index industry companies');
    }
  }

  async getIndustriesOverview(): Promise<any> {
    try {
      return await this.directRequest('/industries');
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : 'Failed to get industries overview');
    }
  }

  async getIndustryCompanies(industryName: string): Promise<any> {
    try {
      return await this.directRequest(`/industries/${encodeURIComponent(industryName)}`);
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : 'Failed to get industry companies');
    }
  }

  async getIndustryIndices(industryName: string): Promise<any> {
    try {
      return await this.directRequest(`/industries/${encodeURIComponent(industryName)}/indices`);
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : 'Failed to get industry indices');
    }
  }

  async getIndustryIndexCompanies(industryName: string, indexName: string): Promise<any> {
    try {
      return await this.directRequest(`/industries/${encodeURIComponent(industryName)}/indices/${encodeURIComponent(indexName)}`);
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : 'Failed to get industry index companies');
    }
  }
}

export const api = new APIClient();
export default api;
