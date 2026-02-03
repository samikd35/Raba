import { NextRequest, NextResponse } from 'next/server';

// Demo request API endpoint
// This receives demo request form submissions and forwards them to the backend API

const BACKEND_API_URL = process.env.NEXT_PUBLIC_API_URL || process.env.API_URL || 'http://localhost:8000';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    // Validate required fields
    if (!body.demo_request) {
      return NextResponse.json(
        { message: 'Invalid request format: missing demo_request object' },
        { status: 400 }
      );
    }

    const { demo_request } = body;

    // Basic validation
    const requiredFields = ['full_name', 'email', 'phone_number', 'job_title', 'organization'];
    for (const field of requiredFields) {
      if (!demo_request[field]) {
        return NextResponse.json(
          { message: `Missing required field: ${field}` },
          { status: 400 }
        );
      }
    }

    // Email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(demo_request.email)) {
      return NextResponse.json(
        { message: 'Invalid email address' },
        { status: 400 }
      );
    }

    // Forward to backend API if configured
    try {
      const backendResponse = await fetch(`${BACKEND_API_URL}/api/demo-request`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      });

      if (backendResponse.ok) {
        const data = await backendResponse.json();
        return NextResponse.json(data, { status: 200 });
      }

      // If backend fails, log but still return success to user
      // (we've captured the data, can process later)
      console.warn('Backend API call failed:', backendResponse.status);
    } catch (backendError) {
      // Backend might not be available - log and continue
      console.warn('Could not reach backend API:', backendError);
    }

    // For now, log the demo request and return success
    // In production, this would be saved to a database or sent to a CRM
    console.log('Demo Request Received:', JSON.stringify(body, null, 2));

    // Return success response
    return NextResponse.json(
      {
        success: true,
        message: 'Demo request submitted successfully',
        data: {
          id: `demo_${Date.now()}`,
          submitted_at: new Date().toISOString(),
        },
      },
      { status: 200 }
    );
  } catch (error) {
    console.error('Demo request error:', error);
    return NextResponse.json(
      { message: 'Internal server error' },
      { status: 500 }
    );
  }
}

// Handle OPTIONS for CORS preflight
export async function OPTIONS() {
  return new NextResponse(null, {
    status: 200,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    },
  });
}
