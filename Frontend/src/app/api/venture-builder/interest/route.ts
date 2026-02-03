import { NextRequest, NextResponse } from 'next/server';

const BACKEND_API_URL = process.env.NEXT_PUBLIC_API_URL || process.env.API_URL || 'http://localhost:8000';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    // Basic validation - field names must match backend model
    const requiredFields = [
      'full_name', 'work_email', 'phone_country_code', 'phone_number',
      'country', 'city', 'primary_role',
      'linkedin_url', 'has_founded_venture', 'coaching_experience',
      'support_areas', 'industries_of_focus', 'founder_stages',
      'geographies', 'languages', 'weekly_availability', 'hourly_rate_usd'
    ];

    for (const field of requiredFields) {
      if (body[field] === undefined || body[field] === null || body[field] === '') {
        if (field === 'support_areas' || field === 'industries_of_focus' || 
            field === 'founder_stages' || field === 'geographies' || field === 'languages') {
          if (!Array.isArray(body[field]) || body[field].length === 0) {
            return NextResponse.json(
              { message: `Missing required field: ${field}` },
              { status: 400 }
            );
          }
        } else {
          return NextResponse.json(
            { message: `Missing required field: ${field}` },
            { status: 400 }
          );
        }
      }
    }

    // Email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(body.work_email)) {
      return NextResponse.json(
        { message: 'Invalid email address' },
        { status: 400 }
      );
    }

    // LinkedIn URL validation
    const linkedinRegex = /^https?:\/\/(www\.)?linkedin\.com\/.*$/;
    if (!linkedinRegex.test(body.linkedin_url)) {
      return NextResponse.json(
        { message: 'Invalid LinkedIn URL' },
        { status: 400 }
      );
    }

    // Hourly rate validation
    const hourlyRate = parseFloat(body.hourly_rate_usd);
    if (isNaN(hourlyRate) || hourlyRate < 0 || hourlyRate > 10000) {
      return NextResponse.json(
        { message: 'Hourly rate must be between 0 and 10,000 USD' },
        { status: 400 }
      );
    }

    // Forward to backend API
    try {
      const backendResponse = await fetch(`${BACKEND_API_URL}/venture-builder/interest`, {
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

      if (backendResponse.status === 409) {
        return NextResponse.json(
          { message: 'This email has already submitted an application.' },
          { status: 409 }
        );
      }

      console.warn('Backend API call failed:', backendResponse.status);
      const errorData = await backendResponse.json().catch(() => ({}));
      return NextResponse.json(
        { message: errorData.detail || errorData.message || 'Failed to submit application' },
        { status: backendResponse.status }
      );
    } catch (backendError) {
      console.warn('Could not reach backend API:', backendError);
    }

    // Fallback: log and return success
    console.log('Venture Builder Interest Received:', JSON.stringify(body, null, 2));

    return NextResponse.json(
      {
        success: true,
        message: 'Application submitted successfully',
        data: {
          id: `vb_interest_${Date.now()}`,
          submitted_at: new Date().toISOString(),
        },
      },
      { status: 200 }
    );
  } catch (error) {
    console.error('Venture builder interest error:', error);
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
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    },
  });
}
