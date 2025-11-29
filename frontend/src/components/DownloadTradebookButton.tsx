'use client';

import React, { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Download, FileText } from 'lucide-react';

interface DownloadTradebookButtonProps {
  simulationResults: any;
  strategyName: string;
  disabled?: boolean;
}

export const DownloadTradebookButton: React.FC<DownloadTradebookButtonProps> = ({
  simulationResults,
  strategyName,
  disabled = false
}) => {
  const [isDownloading, setIsDownloading] = useState(false);

  const downloadTradebook = async () => {
    if (!simulationResults || !strategyName) {
      alert('Please ensure simulation data is available before downloading.');
      return;
    }

    setIsDownloading(true);
    
    try {
      const response = await fetch('http://localhost:3001/api/simulation/download-tradebook', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          strategy_name: strategyName,
          simulation_results: simulationResults
        })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Server error: ${response.status}`);
      }

      // Create download
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      
      // Clean strategy name for filename
      const safeStrategyName = strategyName.replace(/[^a-zA-Z0-9\s\-_]/g, '').trim();
      a.download = `${safeStrategyName}_tradebook.pdf`;
      
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      // Success feedback
      console.log('✅ PDF tradebook downloaded successfully');
      
    } catch (error) {
      console.error('❌ Error downloading tradebook:', error);
      
      // User-friendly error messages
      if (error.message.includes('simulation_results')) {
        alert('Please run a simulation first before downloading the tradebook.');
      } else if (error.message.includes('500')) {
        alert('Server error generating PDF. Please try again in a moment.');
      } else if (error.message.includes('404')) {
        alert('PDF generation service not available. Please contact support.');
      } else {
        alert('Failed to download tradebook. Please check your connection and try again.');
      }
    } finally {
      setIsDownloading(false);
    }
  };

  return (
    <Button
      onClick={downloadTradebook}
      disabled={disabled || isDownloading || !simulationResults}
      variant="outline"
      className="flex items-center gap-2 bg-gradient-to-r from-blue-50 to-indigo-50 hover:from-blue-100 hover:to-indigo-100 border-blue-200 text-blue-700 transition-all duration-200 hover:shadow-md"
    >
      {isDownloading ? (
        <>
          <div className="animate-spin rounded-full h-4 w-4 border-2 border-blue-600 border-t-transparent" />
          Generating PDF...
        </>
      ) : (
        <>
          <FileText className="h-4 w-4" />
          Download Tradebook
        </>
      )}
    </Button>
  );
};
