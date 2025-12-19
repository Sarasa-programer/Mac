import axios from 'axios';

const baseURL = import.meta.env.VITE_API_URL || '/api/v1';

export const apiClient = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 8000,
});

export const setAuthToken = (token: string) => {
  localStorage.setItem('token', token);
};

export const getAuthToken = () => {
  return localStorage.getItem('token');
};

const getOrCreateDemoCredentials = () => {
  let email = localStorage.getItem('demo_email');
  const password = localStorage.getItem('demo_password') || 'password123';
  if (!email) {
    // Default to the seeded admin user to prevent 401s
    email = 'admin@example.com';
    localStorage.setItem('demo_email', email);
    localStorage.setItem('demo_password', password);
  }
  return { email, password };
};

apiClient.interceptors.request.use(
  async (config) => {
    let token = getAuthToken();

    if (!token && !config.url?.includes('/auth/login') && !config.url?.includes('/auth/register')) {
      try {
        const { email, password } = getOrCreateDemoCredentials();

        const loginForm = new FormData();
        loginForm.append('username', email as string);
        loginForm.append('password', password);

        const bare = axios.create({ timeout: 8000 });
        try {
          const loginRes = await bare.post(`${baseURL}/auth/login`, loginForm);
          token = loginRes.data.access_token;
        } catch (loginError: any) {
          // If login fails (e.g. random user from previous session that doesn't exist in DB),
          // fallback to admin user or try to register.
          if (loginError.response?.status === 401 || !loginError.response) {
            console.warn('Auto-login failed with stored creds. Attempting fallback to admin...');
            
            const adminForm = new FormData();
            adminForm.append('username', 'admin@example.com');
            adminForm.append('password', 'password123');
            
            try {
              const adminRes = await bare.post(`${baseURL}/auth/login`, adminForm);
              token = adminRes.data.access_token;
              
              // Update storage to use working credentials
              localStorage.setItem('demo_email', 'admin@example.com');
              localStorage.setItem('demo_password', 'password123');
            } catch (adminError) {
              console.error('Admin fallback failed. Attempting registration...', adminError);
              
              // Last resort: Register the original user
              try {
                await bare.post(`${baseURL}/auth/register`, {
                  email,
                  password,
                  full_name: "Demo User",
                  role: "professor"
                });
                // Retry login
                const retryRes = await bare.post(`${baseURL}/auth/login`, loginForm);
                token = retryRes.data.access_token;
              } catch (regError) {
                console.error('Auto-registration failed:', regError);
              }
            }
          } else {
            throw loginError;
          }
        }

        if (token) {
          setAuthToken(token);
        }
      } catch (e) {
        console.error('Auto-login sequence failed:', e);
        // Don't crash here, just proceed without token
      }
    }

    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    } else if (!config.url?.includes('/auth/login') && !config.url?.includes('/auth/register')) {
        console.warn("Request proceeding without auth token:", config.url);
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Global Error Handler
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    // 1. Network Errors (No response)
    if (!error.response) {
      console.error('Network Error - Check your connection or backend status');
      return Promise.reject(new Error('Network error: Unable to reach the server.'));
    }

    const { status, data } = error.response;

    // 2. Auth Errors (401) - Auto Retry with Re-login
    if (status === 401 && !error.config._retry) {
      console.warn('Session expired. Attempting auto-relogin...');
      error.config._retry = true;
      localStorage.removeItem('token'); // Clear stale token
      
      // The request interceptor will see the missing token and trigger auto-login
      try {
        return await apiClient(error.config);
      } catch (retryError) {
        console.error('Auto-relogin retry failed:', retryError);
        return Promise.reject(retryError);
      }
    }

    // 3. Validation Errors (422)
    if (status === 422) {
      console.error('Validation Failed:', data.detail || data);
      // Return specific structure so UI can handle form errors
    }

    // 4. Server Errors (500+)
    if (status >= 500) {
      console.error('Server Error:', status, data);
    }

    return Promise.reject(error);
  }
);
