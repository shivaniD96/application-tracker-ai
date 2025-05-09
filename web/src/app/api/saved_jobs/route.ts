import { NextResponse } from 'next/server';

export async function GET() {
  const flaskUrl = 'http://127.0.0.1:5000/api/saved_jobs';
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
