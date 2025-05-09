import { NextRequest, NextResponse } from 'next/server';

export async function GET(req: NextRequest, context: { params: Promise<{ id: string }> }) {
  const params = await context.params;
  const { id } = params;
  const flaskUrl = `http://127.0.0.1:8080/api/job_details/${id}`;
  const flaskRes = await fetch(flaskUrl, {
    method: 'GET',
    headers: { 'Accept': 'application/json' },
  });
  const data = await flaskRes.json();
  return NextResponse.json(data);
}
