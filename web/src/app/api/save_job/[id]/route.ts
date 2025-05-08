import { NextRequest, NextResponse } from 'next/server';

export async function POST(req: NextRequest, context: { params: Promise<{ id: string }> }) {
  const params = await context.params;
  const { id } = params;
  const flaskUrl = `http://127.0.0.1:5000/api/save_job/${id}`;
  const flaskRes = await fetch(flaskUrl, {
    method: 'POST',
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

export async function DELETE(req: NextRequest, context: { params: Promise<{ id: string }> }) {
  const params = await context.params;
  const { id } = params;
  const flaskUrl = `http://127.0.0.1:5000/api/save_job/${id}`;
  const flaskRes = await fetch(flaskUrl, {
    method: 'DELETE',
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
