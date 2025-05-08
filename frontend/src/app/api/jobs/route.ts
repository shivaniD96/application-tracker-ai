import { NextRequest, NextResponse } from 'next/server';

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const keyword = searchParams.get('keyword') || '';
  const location = searchParams.get('location') || '';
  const platform = searchParams.get('platform') || '';

  // Proxy to Flask backend
  const flaskUrl = `http://127.0.0.1:5000/api/search?keyword=${encodeURIComponent(keyword)}&location=${encodeURIComponent(location)}&platform=${encodeURIComponent(platform)}`;
  const flaskRes = await fetch(flaskUrl, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
    },
  });

  // If Flask returns HTML, you may need to adjust the backend to return JSON for API requests
  let jobs = [];
  try {
    const data = await flaskRes.json();
    jobs = data.jobs || [];
  } catch {
    // fallback: try to parse as text or return empty
    jobs = [];
  }

  return NextResponse.json({ jobs });
}
