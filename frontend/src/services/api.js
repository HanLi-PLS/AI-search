import axios from 'axios';

// Use window.location.hostname to connect to the same server serving the frontend
const API_BASE_URL = `http://${window.location.hostname}:8000`;

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const stockAPI = {
  // Get all biotech companies
  getCompanies: async () => {
    const response = await api.get('/api/stocks/companies');
    return response.data;
  },

  // Get all stock prices
  getAllPrices: async () => {
    const response = await api.get('/api/stocks/prices');
    return response.data;
  },

  // Get price for specific ticker
  getPrice: async (ticker) => {
    const response = await api.get(`/api/stocks/price/${ticker}`);
    return response.data;
  },

  // Get historical data
  getHistory: async (ticker, period = '1mo') => {
    const response = await api.get(`/api/stocks/history/${ticker}`, {
      params: { period },
    });
    return response.data;
  },

  // Get upcoming IPOs
  getUpcomingIPOs: async () => {
    const response = await api.get('/api/stocks/upcoming-ipos');
    return response.data;
  },
};

// AI Search API functions (matching HTML version API)
export const uploadFile = async (file, conversationId = null) => {
  const formData = new FormData();
  formData.append('file', file);
  if (conversationId) {
    formData.append('conversation_id', conversationId);
  }

  try {
    const response = await axios.post(`${API_BASE_URL}/api/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Upload failed');
  }
};

export const searchDocuments = async (searchRequest) => {
  try {
    const response = await api.post('/api/search', searchRequest);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Search failed');
  }
};

export const getDocuments = async (conversationId = null) => {
  try {
    const params = conversationId ? { conversation_id: conversationId } : {};
    const response = await api.get('/api/documents', { params });
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Failed to fetch documents');
  }
};

export const deleteDocument = async (fileId) => {
  try {
    const response = await api.delete(`/api/documents/${fileId}`);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Failed to delete document');
  }
};

export const healthCheck = async () => {
  try {
    const response = await api.get('/api/health');
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Health check failed');
  }
};

export const getJobStatus = async (jobId) => {
  try {
    const response = await api.get(`/api/jobs/${jobId}`);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Failed to fetch job status');
  }
};

export const listJobs = async (conversationId = null) => {
  try {
    const params = conversationId ? { conversation_id: conversationId } : {};
    const response = await api.get('/api/jobs', { params });
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Failed to fetch jobs');
  }
};

export default api;
