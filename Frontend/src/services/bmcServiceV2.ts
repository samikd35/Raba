import { BMCResponse } from "@/types/bmc";
import toast from "react-hot-toast";

export class BMCService {
  private static instance: BMCService;
  
  public static getInstance(): BMCService {
    if (!BMCService.instance) {
      BMCService.instance = new BMCService();
    }
    return BMCService.instance;
  }

  /**
   * Fetch BMC data for a project
   */
  async fetchBMCData(
    projectId: string, 
    token: string, 
    signal?: AbortSignal
  ): Promise<BMCResponse> {
    if (process.env.NODE_ENV === 'development') {
      console.log('🔄 Fetching BMC data for project:', projectId);
    }

    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/api/v2/mvp/projects/${projectId}/bmc/v2`, 
      {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        signal,
      }
    );

    if (!response.ok) {
      if (response.status === 404) {
        throw new Error('BMC not found. Please generate your Business Model Canvas first.');
      }
      
      if (response.status === 403) {
        throw new Error('You do not have permission to access this Business Model Canvas. Please check your project access or contact your team administrator.');
      }
      
      if (response.status === 400) {
        // Try to get more detailed error information for 400 errors
        try {
          const responseText = await response.text();
          if (responseText && responseText.trim() !== '') {
            try {
              const errorData = JSON.parse(responseText);
              if (errorData.message) {
                // Handle specific access errors in 400
                if (errorData.message.includes('does not have access to project')) {
                  throw new Error('You do not have access to this project. Please contact your team administrator to get the necessary permissions.');
                }
                throw new Error(`HTTP ${response.status}: ${errorData.message}`);
              } else if (errorData.error) {
                throw new Error(`HTTP ${response.status}: ${errorData.error}`);
              } else if (errorData.detail) {
                throw new Error(`HTTP ${response.status}: ${errorData.detail}`);
              }
            } catch (jsonError) {
              // If JSON parsing fails, use the raw text as error message for short responses
              if (responseText.length < 200) {
                // Handle specific access errors in raw text
                if (responseText.includes('does not have access to project')) {
                  throw new Error('You do not have access to this project. Please contact your team administrator to get the necessary permissions.');
                }
                throw new Error(`HTTP ${response.status}: ${responseText}`);
              }
            }
          }
        } catch (textError) {
          // If we can't read the response, use a generic 400 message
          if (process.env.NODE_ENV === 'development') {
            console.error('❌ Could not read fetch error response:', textError);
          }
          throw new Error('Invalid request. Please check your project access and try again.');
        }
      }
      
      if (response.status === 500) {
        // Try to get more detailed error information for 500 errors
        try {
          const responseText = await response.text();
          if (responseText && responseText.trim() !== '') {
            try {
              const errorData = JSON.parse(responseText);
              if (errorData.message) {
                // Handle specific access errors
                if (errorData.message.includes('does not have access to project')) {
                  throw new Error('You do not have access to this project. Please contact your team administrator to get the necessary permissions.');
                }
                throw new Error(`HTTP ${response.status}: ${errorData.message}`);
              } else if (errorData.error) {
                throw new Error(`HTTP ${response.status}: ${errorData.error}`);
              } else if (errorData.detail) {
                throw new Error(`HTTP ${response.status}: ${errorData.detail}`);
              }
            } catch (jsonError) {
              // If JSON parsing fails, use the raw text as error message for short responses
              if (responseText.length < 200) {
                // Handle specific access errors in raw text
                if (responseText.includes('does not have access to project')) {
                  throw new Error('You do not have access to this project. Please contact your team administrator to get the necessary permissions.');
                }
                throw new Error(`HTTP ${response.status}: ${responseText}`);
              }
            }
          }
        } catch (textError) {
          // If we can't read the response, use a generic 500 message
          if (process.env.NODE_ENV === 'development') {
            console.error('❌ Could not read fetch error response:', textError);
          }
          throw new Error('Server error occurred. Please try again later or contact support if the problem persists.');
        }
      }
      
      let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
      
      // Try to get more detailed error information for other status codes
      try {
        const responseText = await response.text();
        if (responseText && responseText.trim() !== '') {
          try {
            const errorData = JSON.parse(responseText);
            if (errorData.message) {
              errorMessage = `HTTP ${response.status}: ${errorData.message}`;
            } else if (errorData.error) {
              errorMessage = `HTTP ${response.status}: ${errorData.error}`;
            } else if (errorData.detail) {
              errorMessage = `HTTP ${response.status}: ${errorData.detail}`;
            }
          } catch (jsonError) {
            // If JSON parsing fails, use the raw text as error message for short responses
            if (responseText.length < 200) {
              errorMessage = `HTTP ${response.status}: ${responseText}`;
            }
          }
        }
      } catch (textError) {
        // If we can't read the response, use the original message
        if (process.env.NODE_ENV === 'development') {
          console.error('❌ Could not read fetch error response:', textError);
        }
      }
      
      throw new Error(errorMessage);
    }

    const data: BMCResponse = await response.json();
    
    if (!data.success || !data.bmc) {
      throw new Error(data.message || 'Failed to load BMC data');
    }

    if (process.env.NODE_ENV === 'development') {
      console.log('✅ BMC data loaded successfully:', data.bmc);
    }

    return data;
  }

  /**
   * Generate BMC data for a project
   */
  async generateBMC(
    projectId: string, 
    token: string,
    creativityLevel: number = 0.7
  ): Promise<BMCResponse> {
    if (process.env.NODE_ENV === 'development') {
      console.log('🔄 Generating BMC for project:', projectId);
      console.log('🔄 Request URL:', `${process.env.NEXT_PUBLIC_API_URL}/api/v2/mvp/projects/${projectId}/bmc/v2/generate`);
      console.log('🔄 Request body:', { creativity_level: creativityLevel, include_context_summary: true });
      console.log('🔄 Token present:', !!token);
    }

    toast.success('Generating Business Model Canvas... This may take a few minutes.');

    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/api/v2/mvp/projects/${projectId}/bmc/v2/generate`, 
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          creativity_level: creativityLevel,
        }),
      }
    );

    if (!response.ok) {
      let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
      
      // Handle specific status codes
      if (response.status === 401) {
        throw new Error('Authentication failed. Please sign in again.');
      }
      
      if (response.status === 403) {
        throw new Error('You do not have permission to generate Business Model Canvas for this project. Please check your project access or contact your team administrator.');
      }
      
      if (response.status === 400) {
        // Try to get more detailed error information for 400 errors
        try {
          const responseText = await response.text();
          
          if (process.env.NODE_ENV === 'development') {
            console.error('❌ BMC Generation Response Text (400):', responseText);
          }
          
          // Only try to parse as JSON if we have content
          if (responseText && responseText.trim() !== '') {
            try {
              const errorData = JSON.parse(responseText);
              if (errorData.message) {
                // Handle specific access errors in 400
                if (errorData.message.includes('does not have access to project')) {
                  throw new Error('You do not have access to this project. Please contact your team administrator to get the necessary permissions.');
                }
                errorMessage = `HTTP ${response.status}: ${errorData.message}`;
              } else if (errorData.error) {
                errorMessage = `HTTP ${response.status}: ${errorData.error}`;
              } else if (errorData.detail) {
                errorMessage = `HTTP ${response.status}: ${errorData.detail}`;
              }
              
              if (process.env.NODE_ENV === 'development') {
                console.error('❌ BMC Generation Error Details (400):', errorData);
              }
            } catch (jsonError) {
              // If JSON parsing fails, use the raw text as error message
              if (responseText.length < 200) { // Only use short responses as error messages
                // Handle specific access errors in raw text
                if (responseText.includes('does not have access to project')) {
                  throw new Error('You do not have access to this project. Please contact your team administrator to get the necessary permissions.');
                }
                errorMessage = `HTTP ${response.status}: ${responseText}`;
              }
              
              if (process.env.NODE_ENV === 'development') {
                console.error('❌ Could not parse error response as JSON (400):', jsonError);
              }
            }
          }
        } catch (textError) {
          // If we can't read the response, use a generic 400 message
          if (process.env.NODE_ENV === 'development') {
            console.error('❌ Could not read fetch error response (400):', textError);
          }
          throw new Error('Invalid request. Please check your project access and try again.');
        }
      }
      
      if (response.status === 500) {
        throw new Error('Server error occurred while generating Business Model Canvas. Please try again later or contact support if the problem persists.');
      }
      
      // Try to get more detailed error information for other status codes
      try {
        const responseText = await response.text();
        
        if (process.env.NODE_ENV === 'development') {
          console.error('❌ BMC Generation Response Text:', responseText);
        }
        
        // Only try to parse as JSON if we have content
        if (responseText && responseText.trim() !== '') {
          try {
            const errorData = JSON.parse(responseText);
            if (errorData.message) {
              errorMessage = `HTTP ${response.status}: ${errorData.message}`;
            } else if (errorData.error) {
              errorMessage = `HTTP ${response.status}: ${errorData.error}`;
            } else if (errorData.detail) {
              errorMessage = `HTTP ${response.status}: ${errorData.detail}`;
            }
            
            if (process.env.NODE_ENV === 'development') {
              console.error('❌ BMC Generation Error Details:', errorData);
            }
          } catch (jsonError) {
            // If JSON parsing fails, use the raw text as error message
            if (responseText.length < 200) { // Only use short responses as error messages
              errorMessage = `HTTP ${response.status}: ${responseText}`;
            }
            
            if (process.env.NODE_ENV === 'development') {
              console.error('❌ Could not parse error response as JSON:', jsonError);
            }
          }
        }
      } catch (textError) {
        // If we can't read the response, use the original message
        if (process.env.NODE_ENV === 'development') {
          console.error('❌ Could not read fetch error response:', textError);
        }
      }
      
      throw new Error(errorMessage);
    }

    const data = await this.fetchBMCData(projectId, token);

    toast.success('Business Model Canvas generated successfully!');
    return data;
  }

  /**
   * Edit a BMC block (v2 API)
   * PUT /api/v2/mvp/projects/{project_id}/bmc/v2/v2/blocks/{block_name}
   */
  async editBlock(
    projectId: string,
    token: string,
    blockName: string,
    items: Array<{
      id: string;
      name: string;
      description: string;
      evidence?: string;
      [key: string]: any;
    }>
  ): Promise<BMCResponse> {
    if (process.env.NODE_ENV === 'development') {
      console.log('🔄 Editing BMC block:', blockName, 'for project:', projectId);
    }

    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/api/v2/mvp/projects/${projectId}/bmc/v2/blocks/${blockName}`,
      {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          block_data: {
            items
          }
        }),
      }
    );

    if (!response.ok) {
      const errorMessage = await this.handleErrorResponse(response, 'edit block');
      throw new Error(errorMessage);
    }

    const data: BMCResponse = await response.json();
    
    if (!data.success) {
      throw new Error(data.message || 'Failed to edit BMC block');
    }

    if (process.env.NODE_ENV === 'development') {
      console.log('✅ BMC block edited successfully:', blockName);
    }

    return data;
  }

  /**
   * Add an item to a BMC block (v2 API with AI enhancement)
   * POST /api/v2/mvp/projects/{project_id}/bmc/v2/v2/items/add
   */
  async addItem(
    projectId: string,
    token: string,
    blockName: string,
    label: string,
    description: string
  ): Promise<BMCResponse> {
    if (process.env.NODE_ENV === 'development') {
      console.log('🔄 Adding item to BMC block:', blockName, 'for project:', projectId);
    }

    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/api/v2/mvp/projects/${projectId}/bmc/v2/items/add`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          block_name: blockName,
          label,
          description
        }),
      }
    );

    if (!response.ok) {
      const errorMessage = await this.handleErrorResponse(response, 'add item');
      throw new Error(errorMessage);
    }

    const data: BMCResponse = await response.json();
    
    if (!data.success) {
      throw new Error(data.message || 'Failed to add item to BMC block');
    }

    if (process.env.NODE_ENV === 'development') {
      console.log('✅ Item added successfully to block:', blockName);
    }

    return data;
  }

  /**
   * Delete an item from a BMC block (v2 API)
   * DELETE /api/v2/mvp/projects/{project_id}/bmc/v2/v2/items/delete
   */
  async deleteItem(
    projectId: string,
    token: string,
    blockName: string,
    itemId: string
  ): Promise<BMCResponse> {
    if (process.env.NODE_ENV === 'development') {
      console.log('🔄 Deleting item from BMC block:', blockName, 'itemId:', itemId);
    }

    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/api/v2/mvp/projects/${projectId}/bmc/v2/items/delete`,
      {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          block_name: blockName,
          item_id: itemId
        }),
      }
    );

    if (!response.ok) {
      const errorMessage = await this.handleErrorResponse(response, 'delete item');
      throw new Error(errorMessage);
    }

    const data: BMCResponse = await response.json();
    
    if (!data.success) {
      throw new Error(data.message || 'Failed to delete item from BMC block');
    }

    if (process.env.NODE_ENV === 'development') {
      console.log('✅ Item deleted successfully from block:', blockName);
    }

    return data;
  }

  /**
   * Helper method to handle error responses
   */
  private async handleErrorResponse(response: Response, operation: string): Promise<string> {
    let errorMessage = `HTTP ${response.status}: ${response.statusText}`;

    if (response.status === 401) {
      return 'Authentication failed. Please sign in again.';
    }

    if (response.status === 403) {
      return `You do not have permission to ${operation} for this project.`;
    }

    try {
      const responseText = await response.text();
      if (responseText && responseText.trim() !== '') {
        try {
          const errorData = JSON.parse(responseText);
          if (errorData.message) {
            errorMessage = errorData.message;
          } else if (errorData.error) {
            errorMessage = errorData.error;
          } else if (errorData.detail) {
            errorMessage = errorData.detail;
          }
        } catch {
          if (responseText.length < 200) {
            errorMessage = responseText;
          }
        }
      }
    } catch {
      if (process.env.NODE_ENV === 'development') {
        console.error(`❌ Could not read ${operation} error response`);
      }
    }

    return errorMessage;
  }
}

// Export singleton instance
export const bmcService = BMCService.getInstance();
