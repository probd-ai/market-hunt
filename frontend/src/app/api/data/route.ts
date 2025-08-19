import { NextRequest, NextResponse } from 'next/server';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:3001';

export async function GET() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/data`);
    
    if (!response.ok) {
      throw new Error('Failed to fetch data from backend');
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('API Error:', error);
    return NextResponse.json(
      { error: 'Failed to fetch data overview' },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { url_ids } = body;

    if (!url_ids || !Array.isArray(url_ids)) {
      return NextResponse.json(
        { error: 'url_ids array is required' },
        { status: 400 }
      );
    }

    const response = await fetch(`${API_BASE_URL}/api/process`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ url_ids }),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Failed to process URLs');
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('API Error:', error);
    return NextResponse.json(
      { error: `Failed to process URLs: ${error instanceof Error ? error.message : 'Unknown error'}` },
      { status: 500 }
    );
  }
}
