import { NextRequest, NextResponse } from 'next/server';

const BACKEND_API_URL = process.env.NEXT_PUBLIC_API_URL || process.env.API_URL || 'http://localhost:8000';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ email: string }> }
) {
  try {
    const { email } = await params;
    const decodedEmail = decodeURIComponent(email);

    // Email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(decodedEmail)) {
      return NextResponse.json(
        { message: 'Invalid email address' },
        { status: 400 }
      );
    }

    // Forward to backend API
    try {
      const backendResponse = await fetch(
        `${BACKEND_API_URL}/venture-builder/interest/status/${encodeURIComponent(decodedEmail)}`,
        {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );

      if (backendResponse.ok) {
        const data = await backendResponse.json();
        return NextResponse.json(data, { status: 200 });
      }

      // If 404, email not found = can submit
      if (backendResponse.status === 404) {
        return NextResponse.json(
          { exists: false, already_submitted: false },
          { status: 200 }
        );
      }

      console.warn('Backend status check failed:', backendResponse.status);
    } catch (backendError) {
      console.warn('Could not reach backend API for status check:', backendError);
    }

    // Fallback: allow submission if backend unavailable
    return NextResponse.json(
      { exists: false, already_submitted: false },
      { status: 200 }
    );
  } catch (error) {
    console.error('Status check error:', error);
    return NextResponse.json(
      { message: 'Internal server error' },
      { status: 500 }
    );
  }
}

export async function OPTIONS() {
  return new NextResponse(null, {
    status: 200,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    },
  });
}
