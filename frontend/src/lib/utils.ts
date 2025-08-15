import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(date: Date | string): string {
  const d = new Date(date);
  return d.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
}

export function formatNumber(num: number): string {
  return new Intl.NumberFormat('en-US').format(num);
}

export function getStatusColor(status: boolean): string {
  return status ? 'text-green-600 bg-green-100' : 'text-red-600 bg-red-100';
}

export function getStatusText(status: boolean): string {
  return status ? 'Active' : 'Inactive';
}

export function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength) + '...';
}

export function generateId(): string {
  return Math.random().toString(36).substr(2, 9);
}

export function extractIndexNameFromUrl(url: string): string {
  try {
    const filename = url.split('/').pop() || '';
    const nameWithoutExt = filename.replace(/\.(csv|CSV)$/, '');
    
    // Common patterns for index names
    const patterns = [
      { regex: /nifty[_\-]?(\d+)/i, transform: (match: string) => `NIFTY ${match.match(/\d+/)?.[0] || ''}`.trim() },
      { regex: /sensex[_\-]?(\d+)?/i, transform: () => 'SENSEX' },
      { regex: /bse[_\-]?(\d+)/i, transform: (match: string) => `BSE ${match.match(/\d+/)?.[0] || ''}`.trim() },
      { regex: /ind[_\-]([a-zA-Z0-9]+)/i, transform: (match: string) => match.replace(/^ind[_\-]/i, '').toUpperCase() }
    ];
    
    for (const pattern of patterns) {
      const match = nameWithoutExt.match(pattern.regex);
      if (match) {
        return pattern.transform(match[0]);
      }
    }
    
    // Fallback: use filename without extension
    return nameWithoutExt.toUpperCase().replace(/[_\-]/g, ' ');
  } catch {
    return 'UNKNOWN_INDEX';
  }
}

export function validateUrl(url: string): { isValid: boolean; message: string } {
  try {
    new URL(url);
    
    if (!url.toLowerCase().includes('csv') && !url.toLowerCase().endsWith('.csv')) {
      return { isValid: false, message: 'URL should point to a CSV file or contain CSV in the path' };
    }
    
    return { isValid: true, message: 'Valid URL format' };
  } catch {
    return { isValid: false, message: 'Invalid URL format' };
  }
}

export function debounce<T extends (...args: unknown[]) => void>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout;
  return (...args: Parameters<T>) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
}

export function groupBy<T, K extends keyof T>(array: T[], key: K): Record<string, T[]> {
  return array.reduce((groups, item) => {
    const group = String(item[key]);
    groups[group] = groups[group] || [];
    groups[group].push(item);
    return groups;
  }, {} as Record<string, T[]>);
}
