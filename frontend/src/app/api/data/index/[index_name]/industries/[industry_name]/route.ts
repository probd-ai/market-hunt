import { NextRequest, NextResponse } from 'next/server';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:3001';

export async function GET(
  request: NextRequest,
  { params }: { params: { index_name: string; industry_name: string } }
) {
  try {
    const { index_name, industry_name } = params;
    
    if (!index_name || !industry_name) {
      return NextResponse.json(
        { error: 'Index name and industry name are required' },
        { status: 400 }
      );
    }

    // URL encode the parameters to handle special characters and spaces
    const encodedIndexName = encodeURIComponent(index_name);
    const encodedIndustryName = encodeURIComponent(industry_name);

    const response = await fetch(`${API_BASE_URL}/api/data/index/${encodedIndexName}/industries/${encodedIndustryName}`);
    
    if (!response.ok) {
      throw new Error(`Backend responded with status: ${response.status}`);
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('API Error:', error);
    return NextResponse.json(
      { error: `Failed to fetch companies for industry: ${error instanceof Error ? error.message : 'Unknown error'}` },
      { status: 500 }
    );
  }
}
