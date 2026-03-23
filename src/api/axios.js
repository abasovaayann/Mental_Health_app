import axios from 'axios';

const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

const clearAuthState = () => {
  localStorage.removeItem('token');
  localStorage.removeItem('refreshToken');
  localStorage.removeItem('user');
};

let isRefreshing = false;
let pendingRequests = [];

const subscribeTokenRefresh = (cb) => {
  pendingRequests.push(cb);
};

const onRefreshed = (token) => {
  pendingRequests.forEach((cb) => cb(token));
  pendingRequests = [];
};

const forceLogout = () => {
  clearAuthState();
  window.location.href = '/auth';
};

// Request interceptor to add token to requests
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (!error.response || !originalRequest) {
      return Promise.reject(error);
    }

    const isUnauthorized = error.response.status === 401;
    const isRefreshCall = originalRequest.url?.includes('/auth/refresh');

    if (!isUnauthorized || isRefreshCall || originalRequest._retry) {
      return Promise.reject(error);
    }

    const refreshToken = localStorage.getItem('refreshToken');
    if (!refreshToken) {
      forceLogout();
      return Promise.reject(error);
    }

    originalRequest._retry = true;

    if (isRefreshing) {
      return new Promise((resolve) => {
        subscribeTokenRefresh((newAccessToken) => {
          originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
          resolve(api(originalRequest));
        });
      });
    }

    isRefreshing = true;

    try {
      const refreshResponse = await api.post(
        '/auth/refresh',
        { refresh_token: refreshToken },
        { skipAuthRefresh: true }
      );

      const newAccessToken = refreshResponse.data?.token;
      const newRefreshToken = refreshResponse.data?.refreshToken;

      if (!newAccessToken || !newRefreshToken) {
        throw new Error('Invalid refresh response');
      }

      localStorage.setItem('token', newAccessToken);
      localStorage.setItem('refreshToken', newRefreshToken);
      onRefreshed(newAccessToken);

      originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
      return api(originalRequest);
    } catch (refreshError) {
      pendingRequests = [];
      forceLogout();
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  }
);

export default api;
