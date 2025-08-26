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

// Chart Types
export interface ChartData {
  name: string;
  value: number;
}

export interface IndustryChart {
  industry: string;
  companies: number;
}

export interface ChartConfig {
  [key: string]: {
    label: string;
    color: string;
  };
}

// Stock Data Management Types
export interface SymbolMapping {
  symbol: string;
  company_name: string;
  industry: string;
  index_names: string[];
  nse_scrip_code: string | null;
  nse_symbol: string | null;
  nse_name: string | null;
  match_confidence: number | null;
  last_updated: string | null;
}

export interface StockGapStatus {
  symbol: string;
  company_name: string;
  industry: string;
  index_names: string[];
  nse_scrip_code: string | null;
  has_data: boolean;
  record_count: number;
  date_range: {
    start: string | null;
    end: string | null;
  };
  data_freshness_days: number;
  coverage_percentage: number;
  last_price: number | null;
  needs_update: boolean;
  gap_details: string[];
}

export interface StockMappingsResponse {
  total_mappings: number;
  mapped_count: number;
  mappings: SymbolMapping[];
}

export interface StockDownloadRequest {
  symbol: string;
  start_date?: string;
  end_date?: string;
  force_refresh?: boolean;
}

export interface StockDownloadResponse {
  success: boolean;
  message: string;
  task_id?: string;
  result?: {
    symbol: string;
    records_processed: number;
    operation_summary: {
      inserts: number;
      updates: number;
      skipped: number;
    };
    processing_time: number;
  };
}

export interface StockStatistics {
  total_symbols: number;
  symbols_with_data: number;
  total_price_records: number;
  date_range: {
    earliest: string;
    latest: string;
  };
  collections: {
    [key: string]: number;
  };
  storage_info: {
    total_size_mb: number;
    index_size_mb: number;
  };
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
