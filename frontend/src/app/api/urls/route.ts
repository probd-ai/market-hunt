import { NextRequest, NextResponse } from 'next/server';

// API configuration - FastAPI backend
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:3001';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const activeOnly = searchParams.get('active_only') === 'true';

    // Call FastAPI backend
    const response = await fetch(`${API_BASE_URL}/api/urls?active_only=${activeOnly}`);
    
    if (!response.ok) {
      throw new Error('Failed to fetch URLs from backend');
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('API Error:', error);
    return NextResponse.json(
      { error: 'Failed to fetch URLs' },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    
    // Call FastAPI backend to add URL
    const response = await fetch(`${API_BASE_URL}/api/urls`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });
    
    if (!response.ok) {
      throw new Error('Failed to add URL');
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('API Error:', error);
    return NextResponse.json(
      { error: 'Failed to add URL' },
      { status: 500 }
    );
  }
}
