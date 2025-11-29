# PDF Tradebook Integration Guide

## 🔗 Frontend Integration for PDF Download Feature

### **API Endpoint**
```
POST /api/simulation/download-tradebook
Content-Type: application/json
```

### **Request Format**
```javascript
const downloadTradebook = async (simulationResults, strategyName) => {
  try {
    const response = await fetch('/api/simulation/download-tradebook', {
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
      throw new Error('PDF generation failed');
    }

    // Create download
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${strategyName}_tradebook.pdf`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
    
  } catch (error) {
    console.error('Error downloading tradebook:', error);
    alert('Failed to generate PDF tradebook');
  }
};
```

### **React Component Example**
```jsx
import React, { useState } from 'react';

const DownloadTradebookButton = ({ simulationResults, strategyName }) => {
  const [isDownloading, setIsDownloading] = useState(false);

  const handleDownload = async () => {
    setIsDownloading(true);
    try {
      await downloadTradebook(simulationResults, strategyName);
    } catch (error) {
      console.error('Download failed:', error);
    } finally {
      setIsDownloading(false);
    }
  };

  return (
    <button 
      onClick={handleDownload}
      disabled={isDownloading}
      className="download-tradebook-btn"
    >
      {isDownloading ? (
        <>
          <span className="spinner"></span>
          Generating PDF...
        </>
      ) : (
        <>
          📄 Download Tradebook
        </>
      )}
    </button>
  );
};
```

### **Integration Points**

#### **1. Simulation Results Page**
Add the download button to the main simulation results page:
```jsx
// In your simulation results component
<div className="simulation-actions">
  <DownloadTradebookButton 
    simulationResults={simulationData}
    strategyName={strategy.name || "Strategy Report"}
  />
</div>
```

#### **2. Required Data Structure**
The `simulationResults` object should contain:
- `params`: All simulation parameters
- `final_portfolio_value`: Final portfolio value
- `portfolio_history`: Daily portfolio values
- `trades`: Complete trade history
- `cumulative_charges`: Total brokerage charges (if applicable)
- `charge_impact_percent`: Percentage impact of charges

#### **3. Styling Suggestions**
```css
.download-tradebook-btn {
  background: linear-gradient(135deg, #4472c4, #2c5aa0);
  color: white;
  border: none;
  padding: 12px 24px;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.3s ease;
}

.download-tradebook-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(68, 114, 196, 0.3);
}

.download-tradebook-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
  transform: none;
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid transparent;
  border-top: 2px solid white;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
```

### **4. Error Handling**
```javascript
const downloadTradebook = async (simulationResults, strategyName) => {
  try {
    const response = await fetch('/api/simulation/download-tradebook', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        strategy_name: strategyName,
        simulation_results: simulationResults
      })
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'PDF generation failed');
    }

    // Success handling...
    
  } catch (error) {
    console.error('Tradebook download error:', error);
    
    // User-friendly error messages
    if (error.message.includes('simulation_results')) {
      alert('Please run a simulation first before downloading the tradebook.');
    } else if (error.message.includes('500')) {
      alert('Server error generating PDF. Please try again.');
    } else {
      alert('Failed to download tradebook. Please check your connection.');
    }
  }
};
```

### **5. Feature Placement**
Add the download button in these strategic locations:

1. **Main Results Dashboard**: Primary download button at top
2. **Performance Summary Card**: Secondary download option
3. **Trade History Section**: Context-specific download
4. **Export Menu**: Part of a comprehensive export options menu

### **6. User Experience Enhancements**
```jsx
// Loading state with progress indication
const [downloadProgress, setDownloadProgress] = useState(0);

// Success notification
const showSuccessToast = () => {
  toast.success('📄 Tradebook PDF downloaded successfully!');
};

// File size preview
const getEstimatedSize = (tradesCount) => {
  const baseSize = 8; // KB
  const tradeSize = tradesCount * 0.1; // KB per trade
  return `~${Math.round(baseSize + tradeSize)} KB`;
};
```

### **7. Testing Checklist**
- [ ] Button appears on simulation results page
- [ ] Download triggers correctly with proper filename
- [ ] PDF opens and displays correctly
- [ ] Error handling works for failed requests
- [ ] Loading state shows during generation
- [ ] Multiple downloads work without conflicts
- [ ] Works across different browsers
- [ ] Strategy name appears correctly in filename

## 🎯 **Implementation Priority**
1. **High Priority**: Add basic download button to results page
2. **Medium Priority**: Add loading states and error handling
3. **Low Priority**: Add advanced features like progress indicators

The PDF tradebook system is **production-ready** and just needs this frontend integration to provide users with comprehensive downloadable reports!
