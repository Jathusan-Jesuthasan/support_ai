import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from 'axios';

// Backend runs on http://localhost:8001
const API_BASE_URL = 'http://localhost:8001/api/v1';

let inMemoryToken: string | null = null;
let isRefreshing = false;
let refreshSubscribers: ((token: string) => void)[] = [];

export const setInMemoryToken = (token: string | null) => {
  inMemoryToken = token;
};

export const getInMemoryToken = () => inMemoryToken;

const subscribeTokenRefresh = (cb: (token: string) => void) => {
  refreshSubscribers.push(cb);
};

const onRefreshed = (token: string) => {
  refreshSubscribers.map((cb) => cb(token));
  refreshSubscribers = [];
};

export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request Interceptor: Attach Access Token + Active Company ID
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    if (inMemoryToken && config.headers) {
      config.headers.Authorization = `Bearer ${inMemoryToken}`;
    }
    // Inject active company ID header for workspace-scoped routes
    const activeCompanyId = localStorage.getItem('supportai_active_company_id');
    if (activeCompanyId && config.headers && !config.headers['X-Company-ID']) {
      config.headers['X-Company-ID'] = activeCompanyId;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response Interceptor: Handle Token Refreshing
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config;
    if (!originalRequest) return Promise.reject(error);

    // If 401 Unauthorized, try to refresh token
    const isUnauthorized = error.response?.status === 401;
    const isRefreshRoute = originalRequest.url?.includes('/auth/refresh');
    const isLoginRoute = originalRequest.url?.includes('/auth/login');

    // Avoid infinite loop if refreshing fails
    if (isUnauthorized && !isRefreshRoute && !isLoginRoute && !(originalRequest as any)._retry) {
      (originalRequest as any)._retry = true;

      const refreshToken = localStorage.getItem('supportai_refresh_token');
      if (!refreshToken) {
        // No refresh token, trigger logout/redirect
        setInMemoryToken(null);
        window.dispatchEvent(new Event('supportai_logout'));
        return Promise.reject(error);
      }

      if (!isRefreshing) {
        isRefreshing = true;

        try {
          const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          });

          const { access_token, refresh_token } = response.data.data;
          setInMemoryToken(access_token);
          localStorage.setItem('supportai_refresh_token', refresh_token);

          isRefreshing = false;
          onRefreshed(access_token);
        } catch (refreshError) {
          isRefreshing = false;
          // Refresh token expired or invalid, log out
          setInMemoryToken(null);
          localStorage.removeItem('supportai_refresh_token');
          window.dispatchEvent(new Event('supportai_logout'));
          return Promise.reject(refreshError);
        }
      }

      // Queue requests while refreshing is in progress
      return new Promise((resolve) => {
        subscribeTokenRefresh((newToken: string) => {
          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${newToken}`;
          }
          resolve(apiClient(originalRequest));
        });
      });
    }

    return Promise.reject(error);
  }
);
