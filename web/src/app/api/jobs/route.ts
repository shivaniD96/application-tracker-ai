import { NextRequest, NextResponse } from 'next/server';

const MAX_RETRIES = 3;
const RETRY_DELAY = 1000; // 1 second

async function fetchWithRetry(url: string, options: RequestInit, retries = MAX_RETRIES): Promise<Response> {
  try {
    const response = await fetch(url, options);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response;
  } catch (error) {
    if (retries > 0) {
      console.log(`Retrying... ${retries} attempts left`);
      await new Promise(resolve => setTimeout(resolve, RETRY_DELAY));
      return fetchWithRetry(url, options, retries - 1);
    }
    throw error;
  }
}

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const keyword = searchParams.get('keyword') || '';
  const location = searchParams.get('location') || '';
  const platform = searchParams.get('platform') || '';
  const page = searchParams.get('page') || '1';
  const sortBy = searchParams.get('sort_by') || 'date_posted';
  const sortOrder = searchParams.get('sort_order') || 'desc';

  try {
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/api/search?` +
      new URLSearchParams({
        keyword,
        location,
        platform,
        page,
        sort_by: sortBy,
        sort_order: sortOrder
      })
    );

    if (!response.ok) {
      throw new Error('Failed to fetch jobs');
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error fetching jobs:', error);
    return NextResponse.json(
      { error: 'Failed to fetch jobs' },
      { status: 500 }
    );
  }
}
