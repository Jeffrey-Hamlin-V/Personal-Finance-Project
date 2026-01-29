/**
 * API Service - Handles all backend API calls
 * Base URL: http://localhost:8000 (backend FastAPI server)
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Generic API request handler
 */
async function apiRequest(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  
  const config = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  };

  // Remove Content-Type for FormData (file uploads)
  if (options.body instanceof FormData) {
    delete config.headers['Content-Type'];
  }

  try {
    const response = await fetch(url, config);
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(errorData.detail || errorData.error || `HTTP error! status: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error(`API Error (${endpoint}):`, error);
    throw error;
  }
}

/**
 * Health Check
 */
export async function checkHealth() {
  return apiRequest('/health');
}

/**
 * Authentication & User Management
 */
export async function createUser(userData) {
  // Note: Backend doesn't have a dedicated signup endpoint yet
  // For now, we'll create a user when they first upload data
  // This is a placeholder for future implementation
  return { success: true, message: 'User will be created on first data upload' };
}

/**
 * Transaction Upload
 */
export async function uploadTransactions(file, userId) {
  const formData = new FormData();
  formData.append('file', file);
  
  return apiRequest(`/api/upload?user_id=${userId}`, {
    method: 'POST',
    body: formData,
  });
}

/**
 * Get Upload Status
 */
export async function getUploadStatus(uploadId) {
  return apiRequest(`/api/uploads/${uploadId}/status`);
}

/**
 * Get Transactions
 */
export async function getTransactions(userId, filters = {}) {
  const params = new URLSearchParams({ user_id: userId });
  
  if (filters.category) params.append('category', filters.category);
  if (filters.is_anomaly !== undefined) params.append('is_anomaly', filters.is_anomaly);
  if (filters.page) params.append('page', filters.page);
  if (filters.page_size) params.append('page_size', filters.page_size);
  
  return apiRequest(`/api/transactions?${params.toString()}`);
}

/**
 * Get Single Transaction
 */
export async function getTransaction(transactionId) {
  return apiRequest(`/api/transactions/${transactionId}`);
}

/**
 * Get Dashboard Data
 */
export async function getDashboard(userId) {
  return apiRequest(`/api/dashboard?user_id=${userId}`);
}

/**
 * Get Insights
 */
export async function getInsights(userId) {
  return apiRequest(`/api/insights?user_id=${userId}`);
}

/**
 * Get Analytics
 */
export async function getAnalytics(userId) {
  return apiRequest(`/api/analytics?user_id=${userId}`);
}

// Export API base URL for reference
export { API_BASE_URL };
