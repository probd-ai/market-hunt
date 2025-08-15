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
  async getUrls(activeOnly = false): Promise<URLConfig[]> {
    return this.directRequest<URLConfig[]>(`/urls?active_only=${activeOnly}`);
  }

  async addUrl(data: URLFormData): Promise<{ success: boolean; id: string; message: string }> {
    return this.request('/urls/manage', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateUrl(urlId: string, updateData: Partial<URLConfig>): Promise<URLConfig> {
    return await this.directRequest<URLConfig>(`/api/urls/${urlId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(updateData),
    });
  }

  async getIndexCompanies(indexName: string): Promise<{ index_name: string; total_companies: number; companies: any[] }> {
    try {
      return await this.directRequest<{ index_name: string; total_companies: number; companies: any[] }>(`/data/index/${encodeURIComponent(indexName)}`);
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : 'Failed to fetch index companies');
    }
  }

  async getIndexIndustries(indexName: string): Promise<{ index_name: string; total_industries: number; industries: any[] }> {
    try {
      return await this.directRequest<{ index_name: string; total_industries: number; industries: any[] }>(`/data/index/${encodeURIComponent(indexName)}/industries`);
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : 'Failed to fetch index industries');
    }
  }

  async getIndexIndustryCompanies(indexName: string, industryName: string): Promise<{ index_name: string; industry_name: string; total_companies: number; companies: any[] }> {
    try {
      return await this.directRequest<{ index_name: string; industry_name: string; total_companies: number; companies: any[] }>(`/data/index/${encodeURIComponent(indexName)}/industries/${encodeURIComponent(industryName)}`);
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : 'Failed to fetch index industry companies');
    }
  }

  async getIndustriesOverview(): Promise<{ total_companies: number; total_industries: number; industry_stats: any[] }> {
    try {
      return await this.directRequest<{ total_companies: number; total_industries: number; industry_stats: any[] }>('/industries');
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : 'Failed to fetch industries overview');
    }
  }

  async getIndustryCompanies(industryName: string): Promise<{ industry_name: string; total_companies: number; companies: any[] }> {
    try {
      return await this.directRequest<{ industry_name: string; total_companies: number; companies: any[] }>(`/industries/${encodeURIComponent(industryName)}`);
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : 'Failed to fetch industry companies');
    }
  }

  async getIndustryIndices(industryName: string): Promise<{ industry_name: string; total_indices: number; indices: any[] }> {
    try {
      return await this.directRequest<{ industry_name: string; total_indices: number; indices: any[] }>(`/industries/${encodeURIComponent(industryName)}/indices`);
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : 'Failed to fetch industry indices');
    }
  }

  async getIndustryIndexCompanies(industryName: string, indexName: string): Promise<{ industry_name: string; index_name: string; total_companies: number; companies: any[] }> {
    try {
      return await this.directRequest<{ industry_name: string; index_name: string; total_companies: number; companies: any[] }>(`/industries/${encodeURIComponent(industryName)}/indices/${encodeURIComponent(indexName)}`);
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : 'Failed to fetch industry index companies');
    }
  }

  async deleteUrl(id: string): Promise<{ success: boolean; message: string }> {
    return this.request(`/urls/manage?id=${id}`, {
      method: 'DELETE',
    });
  }

  // Data Management
  async getDataOverview(): Promise<DataOverview> {
    return this.directRequest<DataOverview>('/data');
  }

  async processUrls(urlIds: string[]): Promise<ProcessingResponse> {
    return this.directRequest<ProcessingResponse>('/process', {
      method: 'POST',
      body: JSON.stringify({ url_ids: urlIds }),
    });
  }

  // Health Check
  async healthCheck(): Promise<{ status: string; timestamp: string }> {
    try {
      return this.request('/health');
    } catch {
      return { status: 'error', timestamp: new Date().toISOString() };
    }
  }

  // Stock Data Management
  async getSymbolMappings(filters: SymbolMappingFilters = {}): Promise<SymbolMapping[]> {
    const params = new URLSearchParams();
    if (filters.index_name) params.append('index_name', filters.index_name);
    if (filters.mapped_only) params.append('mapped_only', 'true');
    if (filters.industry) params.append('industry', filters.industry);
    if (filters.symbols) {
      filters.symbols.forEach(symbol => params.append('symbols', symbol));
    }
    
    const queryString = params.toString();
    const response = await this.directRequest<{
      total_mappings: number;
      mapped_count: number;
      mappings: SymbolMapping[];
    }>(`/stock/mappings${queryString ? '?' + queryString : ''}`);
    return response.mappings;
  }

  async refreshSymbolMappings(): Promise<{ success: boolean; message: string; processed_count: number }> {
    return this.directRequest('/stock/mappings/refresh', {
      method: 'POST',
    });
  }

  async getStockData(symbol: string, startDate?: string, endDate?: string): Promise<StockDataResponse> {
    const params = new URLSearchParams();
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    
    const queryString = params.toString();
    return this.directRequest<StockDataResponse>(`/stock/data/${symbol}${queryString ? '?' + queryString : ''}`);
  }

  async downloadStockData(request: DownloadStockDataRequest): Promise<{ success: boolean; message: string; task_id: string }> {
    // Convert new request format to existing backend format
    const legacyRequest: any = {
      start_date: request.start_date,
      end_date: request.end_date
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
      const response = await this.directRequest('/stock/download', {
        method: 'POST',
        body: JSON.stringify(legacyRequest),
      });
      
      return {
        success: true,
        message: 'Download started successfully',
        task_id: Date.now().toString() // Generate a temporary task ID
      };
    } catch (error) {
      throw error;
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

      const response = await this.directRequest('/stock/gaps', {
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
          full_period_gaps: gapData.total_missing_days > 0,
          gap_percentage: gapData.gap_percentage
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
            full_period_gaps: (gapData.total_missing_days || 0) > 0,
            gap_percentage: gapData.gap_percentage || 0
          });
        });
      }

      return gaps;
    } catch (error) {
      console.error('Error checking data gaps:', error);
      throw new Error(error instanceof Error ? error.message : 'Failed to check data gaps');
    }
  }
        });
      } else {
        // We have some data - analyze gaps
        const availableDates = dbData.map((d: StockPriceData) => new Date(d.date).toISOString().split('T')[0]).sort();
        const earliestAvailable = availableDates[0];
        const latestAvailable = availableDates[availableDates.length - 1];
        
        // Create a map of available dates for gap detection
        const dataMap = new Map(dbData.map((d: StockPriceData) => [new Date(d.date).toISOString().split('T')[0], d]));
        const missingDates: string[] = [];
        
        // Check for gaps from 2005 (or a reasonable start date) to current date
        // This will show ALL missing data, assuming it should be downloadable
        const checkStartDate = new Date(discoveryStartDate);
        const checkEndDate = new Date(currentDate);
        
        const currentCheckDate = new Date(checkStartDate);
        while (currentCheckDate <= checkEndDate) {
          const dateStr = currentCheckDate.toISOString().split('T')[0];
          const dayOfWeek = currentCheckDate.getDay();
          
          // Skip weekends (0 = Sunday, 6 = Saturday)
          if (dayOfWeek !== 0 && dayOfWeek !== 6) {
            if (!dataMap.has(dateStr)) {
              missingDates.push(dateStr);
            }
          }
          
          currentCheckDate.setDate(currentCheckDate.getDate() + 1);
        }
        
        // Calculate gaps in user's selected range
        const userRangeGaps = missingDates.filter(date => 
          date >= request.start_date && date <= request.end_date
        );
        
        // Group gaps by year for visualization
        const gapsByYear = this.calculateYearlyGaps(discoveryStartDate, currentDate, missingDates);
        
        // Calculate some statistics
        const totalTradingDays = this.calculateTradingDays(discoveryStartDate, currentDate);
        const dataGapPercentage = ((missingDates.length / totalTradingDays) * 100).toFixed(1);
        
        gaps.push({
          symbol: request.symbol,
          missing_dates: missingDates.slice(0, 10), // Show first 10 for reference
          first_date: earliestAvailable,
          last_date: latestAvailable,
          total_gaps: missingDates.length,
          full_period_gaps: true,
          earliest_missing: missingDates[0] || 'None',
          latest_missing: missingDates[missingDates.length - 1] || 'None',
          user_range_start: request.start_date,
          user_range_end: request.end_date,
          user_range_gaps: userRangeGaps.length,
          data_available_from: earliestAvailable,
          data_available_until: latestAvailable,
          total_data_points: dbData.length,
          realistic_start_date: discoveryStartDate, // Assume all data from 2005 should be downloadable
          downloadable_gaps: missingDates.length,
          gaps_by_year: gapsByYear
        });
      }
    }
    
    // Handle multiple symbols from index or industry
    if (request.index_name || request.industry) {
      const mappings = await this.getSymbolMappings({ 
        index_name: request.index_name, 
        industry: request.industry 
      });
      
      // Check gaps for each symbol (limit to 3 for performance)
      for (const mapping of mappings.slice(0, 3)) {
        const symbolGaps = await this.checkDataGaps({
          symbol: mapping.symbol,
          start_date: request.start_date,
          end_date: request.end_date,
          full_check: true
        });
        gaps.push(...symbolGaps);
      }
    }
    
    return gaps;
  }

  // Helper method to calculate trading days between two dates
  private calculateTradingDays(startDate: string, endDate: string): number {
    let count = 0;
    const current = new Date(startDate);
    const end = new Date(endDate);
    
    while (current <= end) {
      const dayOfWeek = current.getDay();
      // Skip weekends (0 = Sunday, 6 = Saturday)
      if (dayOfWeek !== 0 && dayOfWeek !== 6) {
        count++;
      }
      current.setDate(current.getDate() + 1);
    }
    
    return count;
  }

  // Helper method to calculate trading days by year
  private calculateYearlyTradingDays(startDate: string, endDate: string): { [year: string]: number } {
    const yearlyDays: { [year: string]: number } = {};
    const current = new Date(startDate);
    const end = new Date(endDate);
    
    while (current <= end) {
      const year = current.getFullYear().toString();
      const dayOfWeek = current.getDay();
      
      // Skip weekends
      if (dayOfWeek !== 0 && dayOfWeek !== 6) {
        yearlyDays[year] = (yearlyDays[year] || 0) + 1;
      }
      current.setDate(current.getDate() + 1);
    }
    
    return yearlyDays;
  }

  // Helper method to calculate missing days grouped by year
  private calculateYearlyGaps(startDate: string, endDate: string, missingDates: string[]): { [year: string]: number } {
    const gapsByYear: { [year: string]: number } = {};
    
    // Initialize all years in the range
    const startYear = new Date(startDate).getFullYear();
    const endYear = new Date(endDate).getFullYear();
    
    for (let year = startYear; year <= endYear; year++) {
      gapsByYear[year.toString()] = 0;
    }
    
    // Count missing dates by year
    missingDates.forEach(date => {
      const year = new Date(date).getFullYear().toString();
      if (gapsByYear[year] !== undefined) {
        gapsByYear[year]++;
      }
    });
    
    // Remove years with 0 gaps for cleaner display
    Object.keys(gapsByYear).forEach(year => {
      if (gapsByYear[year] === 0) {
        delete gapsByYear[year];
      }
    });
    
    return gapsByYear;
  }

  async getTaskProgress(taskId: string): Promise<ProgressUpdate> {
    // Temporary implementation - return mock progress data
    return {
      task_id: taskId,
      status: 'completed',
      progress_percentage: 100,
      current_count: 1,
      total_count: 1,
      message: 'Task completed successfully',
      started_at: new Date(),
      completed_at: new Date()
    };
  }

  async getHistoricalProcessing(limit: number = 20): Promise<HistoricalProcessing[]> {
    // Temporary implementation - return empty array
    return [];
  }

  async deleteStockData(request: { symbol?: string; symbols?: string[]; index_name?: string; industry?: string }): Promise<{ success: boolean; message: string; deleted_count: number }> {
    // Temporary implementation - return mock response
    return {
      success: true,
      message: 'Delete functionality not implemented in backend yet',
      deleted_count: 0
    };
  }

  async getStockStatistics(): Promise<StockDataStatistics> {
    return this.directRequest<StockDataStatistics>('/stock/statistics');
  }
}

export const apiClient = new APIClient();
