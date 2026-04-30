import { NextRequest, NextResponse } from 'next/server';

const backendUrl = process.env.NEXT_BACKEND_URL || 'http://localhost:8000';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    const upstream = await fetch(`${backendUrl}/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
      cache: 'no-store',
    });

    if (!upstream.ok || !upstream.body) {
      const fallback = await upstream.text().catch(() => 'Upstream error');
      return NextResponse.json(
        { error: `Backend stream error (${upstream.status}): ${fallback}` },
        { status: upstream.status },
      );
    }

    return new NextResponse(upstream.body, {
      status: 200,
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache, no-transform',
        Connection: 'keep-alive',
      },
    });
  } catch (error) {
    return NextResponse.json(
      { error: `Proxy stream failure: ${(error as Error).message}` },
      { status: 500 },
    );
  }
}
