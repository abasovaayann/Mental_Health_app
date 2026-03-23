import api from './axios';

const setAuthState = (data) => {
  const refreshToken = data.refreshToken || data.refresh_token;

  if (data.token) {
    localStorage.setItem('token', data.token);
  }
  if (refreshToken) {
    localStorage.setItem('refreshToken', refreshToken);
  }
  if (data.user) {
    localStorage.setItem('user', JSON.stringify(data.user));
  }
};

const clearAuthState = () => {
  localStorage.removeItem('token');
  localStorage.removeItem('refreshToken');
  localStorage.removeItem('user');
};

export const authService = {
  // Login user
  login: async (email, password) => {
    const response = await api.post('/auth/login', { email, password });
    setAuthState(response.data);
    return response.data;
  },

  // Register user
  register: async (userData) => {
    // Convert camelCase to snake_case for backend
    const backendData = {
      email: userData.email,
      first_name: userData.firstName,
      last_name: userData.lastName,
      password: userData.password,
      age: userData.age ? parseInt(userData.age) : null,
      gender: userData.gender || null,
      degree: userData.degree || null,
      university: userData.university || null,
      city: userData.city || null,
      country: userData.country || null
    };
    const response = await api.post('/auth/register', backendData);
    setAuthState(response.data);
    return response.data;
  },

  // Logout user
  logout: () => {
    clearAuthState();
  },

  // Get current user
  getCurrentUser: () => {
    const userStr = localStorage.getItem('user');
    return userStr ? JSON.parse(userStr) : null;
  },

  // Check if user is authenticated
  isAuthenticated: () => {
    return !!localStorage.getItem('token');
  },
};
