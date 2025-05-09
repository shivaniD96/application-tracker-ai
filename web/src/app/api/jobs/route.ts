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

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const keyword = searchParams.get('keyword') || '';
  const location = searchParams.get('location') || '';
  const platform = searchParams.get('platform') || '';
  const page = searchParams.get('page') || '1';

  // Proxy to Flask backend
  const flaskUrl = `http://127.0.0.1:8080/api/search?keyword=${encodeURIComponent(keyword)}&location=${encodeURIComponent(location)}&platform=${encodeURIComponent(platform)}&page=${encodeURIComponent(page)}`;
  
  try {
    const flaskRes = await fetchWithRetry(flaskUrl, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
      },
    });

    let data = {};
    try {
      data = await flaskRes.json();
    } catch (e) {
      console.error('JSON parse error:', e);
      data = { 
        jobs: [], 
        total: 0, 
        pages: 1, 
        current_page: 1,
        error: 'Invalid JSON response from backend'
      };
    }

    return NextResponse.json(data);
  } catch (e) {
    console.error('Fetch error:', e);
    return NextResponse.json({ 
      jobs: [], 
      total: 0, 
      pages: 1, 
      current_page: 1,
      error: 'Failed to connect to backend. Please try again in a few moments.'
    });
  }
}
