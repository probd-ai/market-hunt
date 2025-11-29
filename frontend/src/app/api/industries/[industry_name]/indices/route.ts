import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = 'http://localhost:3001';

export async function GET(
  request: NextRequest,
  { params }: { params: { industry_name: string } }
) {
  try {
    const industryName = params.industry_name;
    const { searchParams } = new URL(request.url);
    const queryString = searchParams.toString();
    
    const url = `${BACKEND_URL}/api/industries/${encodeURIComponent(industryName)}/indices${queryString ? `?${queryString}` : ''}`;
    
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Backend responded with ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error proxying industry indices request:', error);
    return NextResponse.json(
      { error: 'Failed to fetch industry indices data' },
      { status: 500 }
    );
  }
}
