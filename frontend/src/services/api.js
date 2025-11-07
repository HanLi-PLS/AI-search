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

export default api;
