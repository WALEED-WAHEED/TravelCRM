/**
 * Safe logout utility to prevent infinite redirect loops
 */

export const safeLogout = () => {
  // Clear all auth-related data
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  localStorage.removeItem('user_profile');
  
  // Clear any auth store state
  try {
    const authStore = localStorage.getItem('auth-storage');
    if (authStore) {
      localStorage.removeItem('auth-storage');
    }
  } catch (error) {
    console.warn('Failed to clear auth storage:', error);
  }

  // Only redirect if not already on login page
  const currentPath = window.location.pathname;
  if (currentPath !== '/login') {
    // Use a more reliable redirect method
    setTimeout(() => {
      window.location.href = '/login';
    }, 100);
  }
};

export default safeLogout;
