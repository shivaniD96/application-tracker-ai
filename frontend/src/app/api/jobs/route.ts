import { NextRequest, NextResponse } from 'next/server';

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const keyword = searchParams.get('keyword') || '';
  const location = searchParams.get('location') || '';
  const platform = searchParams.get('platform') || '';
  const page = searchParams.get('page') || '1';

  // Proxy to Flask backend
  const flaskUrl = `http://127.0.0.1:5000/api/search?keyword=${encodeURIComponent(keyword)}&location=${encodeURIComponent(location)}&platform=${encodeURIComponent(platform)}&page=${encodeURIComponent(page)}`;
  const flaskRes = await fetch(flaskUrl, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
    },
  });

  let data = {};
  try {
    data = await flaskRes.json();
  } catch {
    data = { jobs: [], total: 0, pages: 1, current_page: 1 };
  }

  return NextResponse.json(data);
}
