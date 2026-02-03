const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL;
const API_TIMEOUT = 30000; // 30 seconds timeout

// Updated interface to better match actual backend response
export interface InsightsApiResponse {
  success: boolean;
  insights: BackendInsight[];
  report_id: string;
  total_insights: number;
  generation_time: null | string;
  metadata: {
    generated_at: string;
  };
}

export interface BackendInsight {
  id: string;
  insight_type: string;
  title: string;
  content: any; // Can be structured content or chat message format
  supporting_chunks: string[];
  confidence_score: number;
  generation_metadata: {
    model_used?: string;
    json_direct?: boolean;
    generated_at?: string;
    sources_count?: number;
    prompt_template?: string;
    structured_format?: boolean;
  };
  created_at: string;
}

// Helper function to identify actionable insights - FIXED
const isActionableInsight = (insight: BackendInsight): boolean => {
  return insight.insight_type === 'comprehensive_actionable_insights' && 
         insight.content && 
         typeof insight.content === 'object' &&
         'important_questions_industry_geography' in insight.content;
};

// Helper function to identify chat messages - FIXED
const isChatMessage = (insight: BackendInsight): boolean => {
  return insight.title.includes('Chat Message') && 
         insight.content && 
         typeof insight.content === 'object' &&
         'role' in insight.content;
};

// NEW: Helper function to filter out chat messages and get only actionable insights
export const filterActionableInsights = (insights: BackendInsight[]): BackendInsight[] => {
  return insights.filter(insight => 
    !isChatMessage(insight) && isActionableInsight(insight)
  );
};

// NEW: Helper function to extract chat messages
export const extractChatMessages = (insights: BackendInsight[]): BackendInsight[] => {
  return insights.filter(insight => isChatMessage(insight));
};

/**
 * Fetch the generated insights for a specific report with timeout and better error handling
 * FIXED: Updated endpoint and improved response handling
 */
export const fetchInsights = async (reportId: string, authToken: string): Promise<InsightsApiResponse> => {
  // Validate inputs
  if (!reportId || reportId.trim() === '') {
    throw new Error('Report ID is required');
  }
  if (!authToken || authToken.trim() === '') {
    throw new Error('Authentication token is required');
  }
  if (!API_BASE_URL) {
    throw new Error('API base URL is not configured');
  }

  // Create a controller for the fetch request to support timeout
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), API_TIMEOUT);

  try {
    // FIXED: Use the correct endpoint - the actionable insights are included in the main insights response
    const apiUrl = `${API_BASE_URL}/api/insights/${reportId}/actionable-insights`;
    console.log('Fetching insights from:', apiUrl);
    console.log('Report ID:', reportId);
    
    const response = await fetch(apiUrl, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${authToken}`,
        "Content-Type": "application/json",
      },
      signal: controller.signal
    });

    // Clear the timeout since the request completed
    clearTimeout(timeoutId);

    console.log("Response status:", response.status, response.statusText);

    if (!response.ok) {
      let errorMessage = `Failed to fetch insights: ${response.status} ${response.statusText}`;
      
      // Handle specific HTTP status codes
      switch (response.status) {
        case 401:
          throw new Error("Authentication failed. Please sign in again.");
        case 403:
          throw new Error("You don't have permission to access these insights.");
        case 404:
          throw new Error("Insights not found for this report. The report may not exist or insights may not have been generated yet.");
        case 408:
        case 504:
          throw new Error("Request timed out. Please try again later.");
        case 429:
          throw new Error("Too many requests. Please wait a moment and try again.");
        case 500:
          throw new Error("Server error. Please try again later.");
        case 502:
        case 503:
          throw new Error("Service temporarily unavailable. Please try again later.");
        default:
          // Try to get error message from response body
          try {
            const errorData = await response.text();
            if (errorData) {
              try {
                const parsedError = JSON.parse(errorData);
                errorMessage = parsedError.message || parsedError.error || errorMessage;
              } catch {
                errorMessage = errorData;
              }
            }
          } catch (_) {
            // Use default error message if we can't read the response
          }
          throw new Error(errorMessage);
      }
    }

    const data = await response.json().catch(err => {
      console.error('Failed to parse JSON response:', err);
      throw new Error("Failed to parse response from server. The response may be malformed.");
    });

    console.log("Raw insights data received:", data);
    console.log("Insights count:", data.insights?.length || 0);
    console.log("Report ID from response:", data.report_id);

    // FIXED: Check for success flag more robustly
    if (data.success === false) {
      throw new Error(data.message || data.error || "Failed to retrieve insights from the server");
    }

    // Validate response structure
    if (!data.insights || !Array.isArray(data.insights)) {
      console.warn("Invalid response format: insights array not found or not an array");
      // Return empty insights array but keep the structure
      return {
        ...data,
        insights: [],
        total_insights: 0
      };
    }

    // Log insight types for debugging
    console.log("=== Insight Analysis ===");
    data.insights.forEach((insight: BackendInsight, index: number) => {
      console.log(`Insight ${index + 1}:`, {
        id: insight.id,
        type: insight.insight_type,
        title: insight.title,
        hasStructuredContent: isActionableInsight(insight),
        isChatMessage: isChatMessage(insight),
        contentKeys: typeof insight.content === 'object' ? Object.keys(insight.content) : 'not object',
        confidence: insight.confidence_score
      });
    });

    // Log summary
    const actionableInsights = filterActionableInsights(data.insights);
    const chatMessages = extractChatMessages(data.insights);
    console.log("=== Summary ===");
    console.log(`Total insights: ${data.insights.length}`);
    console.log(`Actionable insights: ${actionableInsights.length}`);
    console.log(`Chat messages: ${chatMessages.length}`);
    console.log(`Other insights: ${data.insights.length - actionableInsights.length - chatMessages.length}`);

    return data as InsightsApiResponse;
  } catch (error) {
    // Clear the timeout in case of error
    clearTimeout(timeoutId);
    
    console.error("Error in fetchInsights:", error);
    
    if (error.name === 'AbortError') {
      throw new Error(`Request timed out after ${API_TIMEOUT/1000} seconds. Please try again.`);
    }
    
    // Handle network errors
    if (error instanceof TypeError) {
      if (error.message.includes('Failed to fetch')) {
        throw new Error("Network error. Please check your connection and try again.");
      }
    }
    
    // Re-throw the error if it's already an Error instance
    if (error instanceof Error) {
      throw error;
    }
    
    // Handle any other unknown errors
    throw new Error("An unknown error occurred while fetching insights");
  }
};

// NEW: Utility function to get only actionable insights (filtered)
export const fetchActionableInsights = async (reportId: string, authToken: string): Promise<BackendInsight[]> => {
  const response = await fetchInsights(reportId, authToken);
  return filterActionableInsights(response.insights);
};