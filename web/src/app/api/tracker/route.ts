import { NextResponse } from 'next/server';

export async function GET() {
  const flaskUrl = 'http://127.0.0.1:5000/api/tracker';
  const flaskRes = await fetch(flaskUrl, {
    method: 'GET',
    headers: { 'Accept': 'application/json' },
  });
  const data = await flaskRes.json();
  return NextResponse.json(data);
}
