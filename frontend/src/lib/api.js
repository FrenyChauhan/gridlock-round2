import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
});

api.interceptors.request.use(async (config) => {
  let token = localStorage.getItem('gridlock_token');
  if (!token) {
    await new Promise(r => setTimeout(r, 100)); // hydration buffer
    token = localStorage.getItem('gridlock_token');
  }
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      console.warn("401 Unauthorized detected, but avoiding hard redirect to prevent loop.");
      // window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const auth = {
  login: (username, password) => {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);
    return api.post('/auth/login', formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    });
  }
};

export const dashboard = {
  getStats: () => api.get('/dashboard/stats'),
  getTeamForecast: () => api.get('/dashboard/team-availability-forecast'),
  getZonePerformance: () => api.get('/dashboard/zone-performance'),
  getAnalytics: () => api.get('/dashboard/analytics')
};

export const zones = {
  getZones: (params) => api.get('/zones/', { params }),
  getZoneById: (id) => api.get(`/zones/${id}`),
  getUnassignedRed: () => api.get('/zones/unassigned-red'),
  getHeatmap: () => api.get('/zones/heatmap')
};

export const teams = {
  getTeams: (params) => api.get('/teams/', { params }),
  addTeam: (data) => api.post('/teams/add', data),
  updateTeamStatus: (id, statusData) => api.patch(`/teams/${id}/status`, statusData)
};

export const assignments = {
  getAssignments: (params) => api.get('/assignments', { params }),
  createAssignment: (data) => api.post('/assignments/create', data),
  updateAssignmentStatus: (id, statusData) => api.post(`/assignments/${id}/status-update`, statusData),
  getActive: () => api.get('/assignments/active')
};

export default api;
