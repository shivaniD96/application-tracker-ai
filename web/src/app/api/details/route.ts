import { NextRequest, NextResponse } from 'next/server';

export async function GET() {
  const flaskUrl = 'http://127.0.0.1:5000/api/details';
  const flaskRes = await fetch(flaskUrl, {
    method: 'GET',
    headers: { 'Accept': 'application/json' },
  });
  let data;
  try {
    data = await flaskRes.json();
  } catch {
    data = { error: 'Invalid JSON from backend', status: flaskRes.status };
  }
  return NextResponse.json(data);
}

export async function POST(req: NextRequest) {
  const flaskUrl = 'http://127.0.0.1:8080/api/details';
  const formData = await req.formData();
  const fetchRes = await fetch(flaskUrl, {
    method: 'POST',
    body: formData,
  });
  let data;
  try {
    data = await fetchRes.json();
  } catch {
    data = { error: 'Invalid JSON from backend', status: fetchRes.status };
  }
  return NextResponse.json(data);
}
