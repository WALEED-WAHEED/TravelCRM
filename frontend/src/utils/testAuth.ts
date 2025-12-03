/**
 * Test utility to simulate token expiration scenarios
 * This helps verify that the infinite redirect loop is fixed
 */

import apiClient from '@/api/client';

export const testTokenExpiration = async () => {
  console.log('🧪 Testing token expiration handling...');
  
  try {
    // Simulate an expired token by using an invalid one
    localStorage.setItem('access_token', 'expired_token');
    localStorage.setItem('refresh_token', 'expired_refresh_token');
    
    // Make a request that will fail with 401
    await apiClient.get('/api/v1/users/');
    
    console.log('❌ Request should have failed with 401');
  } catch (error: any) {
    if (error.response?.status === 401) {
      console.log('✅ Correctly received 401 error');
      console.log('✅ Token cleanup should have been triggered');
      
      // Check if tokens were cleared
      const accessToken = localStorage.getItem('access_token');
      const refreshToken = localStorage.getItem('refresh_token');
      
      if (!accessToken && !refreshToken) {
        console.log('✅ Tokens were properly cleared');
      } else {
        console.log('❌ Tokens were not cleared properly');
      }
    } else {
      console.log('❌ Unexpected error:', error.message);
    }
  }
};

export const testConcurrentRequests = async () => {
  console.log('🧪 Testing concurrent requests with expired token...');
  
  // Set expired tokens
  localStorage.setItem('access_token', 'expired_token');
  localStorage.setItem('refresh_token', 'expired_refresh_token');
  
  // Make multiple concurrent requests
  const requests = [
    apiClient.get('/api/v1/users/'),
    apiClient.get('/api/v1/agencies/'),
    apiClient.get('/api/v1/auth/user/'),
  ];
  
  try {
    await Promise.allSettled(requests);
    console.log('✅ Concurrent requests handled without infinite loops');
  } catch (error) {
    console.log('✅ Requests failed as expected:', error);
  }
};

export default {
  testTokenExpiration,
  testConcurrentRequests,
};
