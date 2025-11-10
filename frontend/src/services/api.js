import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

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

// AI Search API functions
export const searchDocuments = async (query) => {
  try {
    const response = await api.post('/api/ai-search/search', query);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Search failed');
  }
};

export const getIndexStatus = async () => {
  try {
    const response = await api.get('/api/ai-search/status');
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Failed to get index status');
  }
};

export const indexDocuments = async (indexRequest) => {
  try {
    const response = await api.post('/api/ai-search/index', indexRequest);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Indexing failed');
  }
};

export const getCompanyInfo = async (companyName, kBm = 100, kJd = 100) => {
  try {
    const response = await api.post('/api/ai-search/company-info', null, {
      params: { company_name: companyName, k_bm: kBm, k_jd: kJd },
    });
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Failed to extract company info');
  }
};

export default api;
