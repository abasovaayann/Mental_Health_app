import api from './axios';

export const authService = {
  // Login user
  login: async (email, password) => {
    const response = await api.post('/auth/login', { email, password });
    if (response.data.token) {
      localStorage.setItem('token', response.data.token);
      localStorage.setItem('user', JSON.stringify(response.data.user));
    }
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
    if (response.data.token) {
      localStorage.setItem('token', response.data.token);
      localStorage.setItem('user', JSON.stringify(response.data.user));
    }
    return response.data;
  },

  // Logout user
  logout: () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
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
