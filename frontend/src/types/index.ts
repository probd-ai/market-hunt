// URL Management Types
export interface URLConfig {
  _id: string;
  url: string;
  index_name: string;
  description: string;
  tags: string[];
  is_active: boolean;
  is_valid: boolean;
  validation_message: string;
  created_at: Date;
  updated_at: Date;
  last_downloaded: Date | null;
  download_count: number;
  last_error: string | null;
}

export interface URLFormData {
  url: string;
  index_name?: string;
  description: string;
  tags: string[];
  is_active: boolean;
}

// Data Overview Types
export interface IndexStat {
  _id: string;
  count: number;
  last_update: Date;
}

export interface DataOverview {
  total_documents: number;
  index_stats: Array<{
    _id: string;
    count: number;
    last_update: string;
  }>;
}

// Index Data Types
export interface IndexConstituent {
  _id: string;
  'Company Name': string;
  'Industry': string;
  'Symbol': string;
  'Series': string;
  'ISIN Code': string;
  data_source: string;
  download_timestamp: Date;
  index_name: string;
}

// API Response Types
export interface APIResponse<T = unknown> {
  success: boolean;
  data?: T;
  message?: string;
  error?: string;
}

export interface ProcessingResponse {
  success: boolean;
  message: string;
  processed_count: number;
  total_count: number;
  results: Array<{
    url_id: string;
    index_name: string;
    success: boolean;
    documents_loaded?: number;
    message: string;
  }>;
}

// UI Component Types
export interface TableColumn<T = unknown> {
  id: string;
  header: string;
  accessorKey?: keyof T;
  cell?: (value: T) => React.ReactNode;
  sortable?: boolean;
}

export interface FilterOptions {
  search: string;
  status: 'all' | 'active' | 'inactive';
  tags: string[];
}

// Navigation Types
export interface NavItem {
  name: string;
  href: string;
  icon: React.ComponentType<React.SVGProps<SVGSVGElement>>;
  current: boolean;
}

// Stock Data Management Types
export interface SymbolMapping {
  symbol: string;
  company_name: string;
  industry: string;
  index_names: string[];
  nse_scrip_code: number | null;
  nse_symbol: string | null;
  nse_name: string | null;
  match_confidence: number | null;
  last_updated: string | null;
  is_up_to_date?: boolean | null; // Up-to-date status stored in database
  data_quality_score?: number | null; // Quality score 0-100 based on data completeness
  last_status_check?: string | null; // When status was last calculated
  last_data_update?: string | null; // When data was last loaded/synced
}

export interface SymbolMappingResponse {
  total_mappings: number;
  mapped_count: number;
  mappings: SymbolMapping[];
}

export interface StockPriceData {
  scrip_code: number;
  symbol: string;
  date: string; // API returns ISO string, not Date object
  open_price: number;
  high_price: number;
  low_price: number;
  close_price: number;
  volume: number;
  value: number;
  year_partition: number;
}

export interface StockDataResponse {
  symbol: string;
  total_records: number;
  data: StockPriceData[];
}

export interface StockDataStatistics {
  collections: {
    [key: string]: {
      record_count: number;
    };
  };
  total_records: number;
  symbols_with_data: string[];
  date_range: {
    earliest: string;
    latest: string;
  };
  unique_symbols_count: number;
}

export interface DownloadStockDataRequest {
  symbol?: string;
  symbols?: string[];
  index_name?: string;
  industry?: string;
  start_date?: string;
  end_date?: string;
  sync_mode?: 'load' | 'sync' | 'refresh' | 'delete';
}

export interface ProgressUpdate {
  task_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress_percentage: number;
  current_count: number;
  total_count: number;
  current_item?: string;
  message?: string;
  started_at: Date;
  completed_at?: Date;
  error?: string;
}

export interface HistoricalProcessing {
  _id: string;
  task_id: string;
  request_type: 'symbol' | 'index' | 'industry';
  request_params: DownloadStockDataRequest;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress_percentage: number;
  items_processed: number;
  total_items: number;
  started_at: Date;
  completed_at?: Date;
  error_message?: string;
  processed_symbols: string[];
  failed_symbols: string[];
}

export interface DataGapInfo {
  symbol: string;
  missing_dates: string[];
  first_date: string;
  last_date: string;
  total_gaps: number;
  full_period_gaps?: boolean;
  earliest_missing?: string;
  latest_missing?: string;
  user_range_start?: string;
  user_range_end?: string;
  user_range_gaps?: number;
  data_available_from?: string;
  data_available_until?: string;
  total_data_points?: number;
  realistic_start_date?: string; // Earliest date when data is actually downloadable
  gaps_by_year?: { [year: string]: number }; // Missing days grouped by year (year -> missing_days_count)
  downloadable_gaps?: number; // Only gaps in downloadable period
}

export interface SymbolMappingFilters {
  index_name?: string;
  symbols?: string[];
  mapped_only?: boolean;
  industry?: string;
  symbol_search?: string;
}

// Chart Types
export interface ChartData {
  name: string;
  value: number;
  color?: string;
}

// Statistics Types
export interface URLStatistics {
  total_urls: number;
  active_urls: number;
  valid_urls: number;
  unique_indices: number;
  recent_downloads: Array<{
    url: string;
    index_name: string;
    last_downloaded: Date;
  }>;
}

// Scheduler Types
export interface ProcessingDetail {
  symbol: string;
  status: 'success' | 'error' | 'skipped';
  records_added?: number;
  records_updated?: number;
  records_skipped?: number;
  processing_time?: string;
  error_message?: string;
}

export interface ProcessEntry {
  id: string;
  type: string;
  status: string;
  symbol?: string;
  index_name?: string;
  industry?: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  items_processed: number;
  total_items: number;
  current_item?: string;
  error_message?: string;
  processing_details?: ProcessingDetail[];
  summary?: Record<string, any>;
  request_type?: string;
  request_params?: Record<string, any>;
}

export interface TaskProgress {
  task_id: string;
  status: string;
  progress: number; // This is the percentage (0-100)
  current_item?: string;
  items_processed: number;
  total_items: number;
  start_time?: string;
  estimated_completion?: string;
}

export interface SchedulerData {
  pending: ProcessEntry[];
  running: ProcessEntry[];
  completed: ProcessEntry[];
}
