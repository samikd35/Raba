import { NextRequest, NextResponse } from 'next/server';

const BACKEND_API_URL = process.env.NEXT_PUBLIC_API_URL || process.env.API_URL || 'http://localhost:8000';

export async function POST(
  request: NextRequest,
  { params }: { params: { submission_id: string } }
) {
  try {
    const { submission_id } = params;
    const body = await request.json();
    const authHeader = request.headers.get('Authorization');

    console.log('[API Route - Approve] Submission ID:', submission_id);
    console.log('[API Route - Approve] Request body:', JSON.stringify(body, null, 2));
    console.log('[API Route - Approve] Auth header present:', !!authHeader);

    // Build the request to backend
    const backendUrl = `${BACKEND_API_URL}/venture-builder/admin/interest/${submission_id}/approve`;
    console.log('[API Route - Approve] Backend URL:', backendUrl);

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    // Forward auth header if present
    if (authHeader) {
      headers['Authorization'] = authHeader;
    }

    // Prepare the payload - only include fields the backend expects
    const payload: Record<string, any> = {};
    
    // admin_notes is optional
    if (body.admin_notes && body.admin_notes.trim()) {
      payload.admin_notes = body.admin_notes.trim();
    }
    
    // send_invitation should be a boolean
    payload.send_invitation = body.send_invitation === true;

    console.log('[API Route - Approve] Final payload:', JSON.stringify(payload, null, 2));

    const backendResponse = await fetch(backendUrl, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload),
    });

    console.log('[API Route - Approve] Backend response status:', backendResponse.status);

    // Get response body
    const responseText = await backendResponse.text();
    console.log('[API Route - Approve] Backend response body:', responseText);

    let responseData: any;
    try {
      responseData = JSON.parse(responseText);
    } catch {
      responseData = { message: responseText || 'Unknown error' };
    }

    if (!backendResponse.ok) {
      // Extract error message
      const errorMessage = responseData.detail || responseData.error || responseData.message || 'Failed to approve submission';
      
      console.error('[API Route - Approve] Backend error:', errorMessage);
      
      return NextResponse.json(
        { 
          success: false, 
          error: errorMessage,
          details: responseData
        },
        { status: backendResponse.status }
      );
    }

    // Success
    return NextResponse.json(
      {
        success: true,
        message: 'Submission approved successfully',
        data: responseData
      },
      { status: 200 }
    );

  } catch (error: any) {
    console.error('[API Route - Approve] Exception:', error);
    return NextResponse.json(
      { 
        success: false, 
        error: error.message || 'Internal server error' 
      },
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
