import { NextRequest, NextResponse } from 'next/server';

const BACKEND_BASE_URL = process.env.BACKEND_URL || 'http://localhost:3001';

export async function GET(request: NextRequest) {
  try {
    // Extract query parameters
    const { searchParams } = new URL(request.url);
    const index_name = searchParams.get('index_name');
    const industry = searchParams.get('industry');
    const limit = searchParams.get('limit');
    const search = searchParams.get('search');

    // Build query string for backend
    const params = new URLSearchParams();
    if (index_name) params.append('index_name', index_name);
    if (industry) params.append('industry', industry);
    if (limit) params.append('limit', limit);
    if (search) params.append('search', search);

    const queryString = params.toString();
    const backendUrl = `${BACKEND_BASE_URL}/api/stock/available${queryString ? `?${queryString}` : ''}`;

    // Try to fetch from backend
    try {
      const response = await fetch(backendUrl, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        return NextResponse.json(data);
      } else {
        console.log(`Backend responded with status ${response.status}, falling back to mock data`);
      }
    } catch (backendError) {
      console.log('Backend not available, using mock data:', backendError);
    }

    // Fallback to mock data if backend is not available
    const mockSymbols = [
      { symbol: 'TCS', name: 'Tata Consultancy Services Ltd', sector: 'Information Technology' },
      { symbol: 'INFY', name: 'Infosys Ltd', sector: 'Information Technology' },
      { symbol: 'RELIANCE', name: 'Reliance Industries Ltd', sector: 'Oil Gas & Consumable Fuels' },
      { symbol: 'HDFCBANK', name: 'HDFC Bank Ltd', sector: 'Banks' },
      { symbol: 'ICICIBANK', name: 'ICICI Bank Ltd', sector: 'Banks' },
      { symbol: 'HINDUNILVR', name: 'Hindustan Unilever Ltd', sector: 'Household & Personal Products' },
      { symbol: 'ITC', name: 'ITC Ltd', sector: 'Tobacco' },
      { symbol: 'KOTAKBANK', name: 'Kotak Mahindra Bank Ltd', sector: 'Banks' },
      { symbol: 'LT', name: 'Larsen & Toubro Ltd', sector: 'Construction & Engineering' },
      { symbol: 'SBIN', name: 'State Bank of India', sector: 'Banks' },
      { symbol: 'BHARTIARTL', name: 'Bharti Airtel Ltd', sector: 'Wireless Telecommunication Services' },
      { symbol: 'ASIANPAINT', name: 'Asian Paints Ltd', sector: 'Chemicals' },
      { symbol: 'MARUTI', name: 'Maruti Suzuki India Ltd', sector: 'Automobiles' },
      { symbol: 'TITAN', name: 'Titan Company Ltd', sector: 'Textiles Apparel & Luxury Goods' },
      { symbol: 'NESTLEIND', name: 'Nestle India Ltd', sector: 'Food Products' },
      { symbol: 'ULTRACEMCO', name: 'UltraTech Cement Ltd', sector: 'Construction Materials' },
      { symbol: 'POWERGRID', name: 'Power Grid Corporation of India Ltd', sector: 'Electric Utilities' },
      { symbol: 'BAJFINANCE', name: 'Bajaj Finance Ltd', sector: 'Consumer Finance' },
      { symbol: 'HCLTECH', name: 'HCL Technologies Ltd', sector: 'Information Technology' },
      { symbol: 'WIPRO', name: 'Wipro Ltd', sector: 'Information Technology' },
      { symbol: 'TECHM', name: 'Tech Mahindra Ltd', sector: 'Information Technology' },
      { symbol: 'SUNPHARMA', name: 'Sun Pharmaceutical Industries Ltd', sector: 'Pharmaceuticals' },
      { symbol: 'ONGC', name: 'Oil & Natural Gas Corporation Ltd', sector: 'Oil Gas & Consumable Fuels' },
      { symbol: 'NTPC', name: 'NTPC Ltd', sector: 'Independent Power and Renewable Electricity Producers' },
      { symbol: 'TATASTEEL', name: 'Tata Steel Ltd', sector: 'Steel' },
      { symbol: 'JSWSTEEL', name: 'JSW Steel Ltd', sector: 'Steel' },
      { symbol: 'COALINDIA', name: 'Coal India Ltd', sector: 'Oil Gas & Consumable Fuels' },
      { symbol: 'IOC', name: 'Indian Oil Corporation Ltd', sector: 'Oil Gas & Consumable Fuels' },
      { symbol: 'GRASIM', name: 'Grasim Industries Ltd', sector: 'Construction Materials' },
      { symbol: 'BRITANNIA', name: 'Britannia Industries Ltd', sector: 'Food Products' },
      { symbol: 'DRREDDY', name: 'Dr. Reddy\'s Laboratories Ltd', sector: 'Pharmaceuticals' },
      { symbol: 'BAJAJFINSV', name: 'Bajaj Finserv Ltd', sector: 'Diversified Financial Services' },
      { symbol: 'CIPLA', name: 'Cipla Ltd', sector: 'Pharmaceuticals' },
      { symbol: 'DIVISLAB', name: 'Divi\'s Laboratories Ltd', sector: 'Pharmaceuticals' },
      { symbol: 'EICHERMOT', name: 'Eicher Motors Ltd', sector: 'Automobiles' },
      { symbol: 'SHREECEM', name: 'Shree Cement Ltd', sector: 'Construction Materials' },
      { symbol: 'APOLLOHOSP', name: 'Apollo Hospitals Enterprise Ltd', sector: 'Health Care Providers & Services' },
      { symbol: 'HEROMOTOCO', name: 'Hero MotoCorp Ltd', sector: 'Automobiles' },
      { symbol: 'HINDALCO', name: 'Hindalco Industries Ltd', sector: 'Metals & Mining' },
      { symbol: 'ADANIPORTS', name: 'Adani Ports and Special Economic Zone Ltd', sector: 'Transportation Infrastructure' },
      { symbol: 'INDUSINDBK', name: 'IndusInd Bank Ltd', sector: 'Banks' },
      { symbol: 'TATACONSUM', name: 'Tata Consumer Products Ltd', sector: 'Food Products' },
      { symbol: 'BPCL', name: 'Bharat Petroleum Corporation Ltd', sector: 'Oil Gas & Consumable Fuels' },
      { symbol: 'AXISBANK', name: 'Axis Bank Ltd', sector: 'Banks' },
      { symbol: 'M&M', name: 'Mahindra & Mahindra Ltd', sector: 'Automobiles' },
      { symbol: 'TATAMOTORS', name: 'Tata Motors Ltd', sector: 'Automobiles' },
      { symbol: 'VEDL', name: 'Vedanta Ltd', sector: 'Metals & Mining' },
      { symbol: 'BAJAJ-AUTO', name: 'Bajaj Auto Ltd', sector: 'Automobiles' },
      { symbol: 'ADANIENT', name: 'Adani Enterprises Ltd', sector: 'Trading Companies & Distributors' },
      { symbol: 'TRENT', name: 'Trent Ltd', sector: 'Specialty Retail' }
    ];

    // Apply search filter if provided
    let filteredSymbols = mockSymbols;
    if (search) {
      const searchLower = search.toLowerCase();
      filteredSymbols = mockSymbols.filter(symbol =>
        symbol.symbol.toLowerCase().includes(searchLower) ||
        symbol.name.toLowerCase().includes(searchLower) ||
        symbol.sector.toLowerCase().includes(searchLower)
      );
    }

    // Apply limit if provided
    if (limit) {
      const limitNum = parseInt(limit, 10);
      if (!isNaN(limitNum)) {
        filteredSymbols = filteredSymbols.slice(0, limitNum);
      }
    }

    return NextResponse.json({
      success: true,
      total: filteredSymbols.length,
      symbols: filteredSymbols
    });

  } catch (error) {
    console.error('Error fetching available symbols:', error);
    return NextResponse.json(
      { error: 'Failed to fetch available symbols' },
      { status: 500 }
    );
  }
}
