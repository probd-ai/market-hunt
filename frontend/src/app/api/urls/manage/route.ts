import { NextRequest, NextResponse } from 'next/server';

// API configuration - FastAPI backend
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:3001';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { url, index_name, description, tags, is_active } = body;

    // Validate required fields
    if (!url) {
      return NextResponse.json(
        { error: 'URL is required' },
        { status: 400 }
      );
    }

    // Call FastAPI backend to add URL
    const response = await fetch(`${API_BASE_URL}/api/urls`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ url, index_name, description, tags: tags || [], is_active: is_active !== false }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Failed to add URL');
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

export async function PUT(request: NextRequest) {
  try {
    const body = await request.json();
    const { id, ...updateData } = body;

    if (!id) {
      return NextResponse.json(
        { error: 'URL ID is required' },
        { status: 400 }
      );
    }

    // Note: FastAPI backend doesn't have PUT endpoint yet
    // For now, return success but this needs backend implementation
    console.log('URL update requested:', id, updateData);
    
    return NextResponse.json({
      success: true,
      message: 'URL update functionality needs backend implementation'
    });
  } catch (error) {
    console.error('API Error:', error);
    return NextResponse.json(
      { error: 'Failed to update URL' },
      { status: 500 }
    );
  }
}

export async function DELETE(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const id = searchParams.get('id');

    if (!id) {
      return NextResponse.json(
        { error: 'URL ID is required' },
        { status: 400 }
      );
    }

    // Call FastAPI backend to delete URL
    const response = await fetch(`${API_BASE_URL}/api/urls/${id}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Failed to delete URL');
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('API Error:', error);
    return NextResponse.json(
      { error: 'Failed to delete URL' },
      { status: 500 }
    );
  }
}
