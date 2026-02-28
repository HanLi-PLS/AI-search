import axios from 'axios';

// Use relative URLs - Nginx proxies /api requests to backend
// This works with both HTTP and HTTPS
const api = axios.create({
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 7200000, // 2 hours timeout for long-running requests like deep research mode
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('authToken');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Auth API
export const authAPI = {
  register: async (email, password, name) => {
    const response = await api.post('/api/auth/register', { email, password, name });
    return response.data;
  },

  login: async (email, password, rememberMe = false) => {
    const response = await api.post('/api/auth/login', {
      email,
      password,
      remember_me: rememberMe
    });
    return response.data;
  },

  getMe: async () => {
    const response = await api.get('/api/auth/me');
    return response.data;
  },

  forgotPassword: async (email) => {
    const response = await api.post('/api/auth/forgot-password', { email });
    return response.data;
  },

  resetPassword: async (token, newPassword) => {
    const response = await api.post('/api/auth/reset-password', {
      token,
      new_password: newPassword
    });
    return response.data;
  },

  // Admin functions
  getUsers: async () => {
    const response = await api.get('/api/auth/users');
    return response.data;
  },

  approveUser: async (userId) => {
    const response = await api.post(`/api/auth/users/${userId}/approve`);
    return response.data;
  },

  revokeUser: async (userId) => {
    const response = await api.post(`/api/auth/users/${userId}/revoke`);
    return response.data;
  },

  deleteUser: async (userId) => {
    const response = await api.delete(`/api/auth/users/${userId}`);
    return response.data;
  },

  toggleAdmin: async (userId) => {
    const response = await api.post(`/api/auth/users/${userId}/toggle-admin`);
    return response.data;
  },

  resetPassword: async (userId, newPassword) => {
    const response = await api.post(`/api/auth/users/${userId}/reset-password`, {
      new_password: newPassword
    });
    return response.data;
  },
};

export const stockAPI = {
  // Get all biotech companies
  getCompanies: async () => {
    const response = await api.get('/api/stocks/companies');
    return response.data;
  },

  // Get all stock prices
  getAllPrices: async (forceRefresh = false) => {
    const response = await api.get('/api/stocks/prices', {
      params: { force_refresh: forceRefresh }
    });
    return response.data;
  },

  // Get price for specific ticker
  getPrice: async (ticker) => {
    const response = await api.get(`/api/stocks/price/${ticker}`);
    return response.data;
  },

  // Get historical data from database
  getHistory: async (ticker, timeRange = '1M') => {
    // Convert time range to days
    const daysMap = {
      '1W': 7,
      '1M': 30,
      '3M': 90,
      '6M': 180,
      '1Y': 365,
    };
    const days = daysMap[timeRange] || 30;

    console.log(`[API] getHistory called: ticker=${ticker}, timeRange=${timeRange}, days=${days}`);
    const url = `/api/stocks/${ticker}/history`;
    console.log(`[API] Requesting: ${url}?days=${days}`);

    const response = await api.get(url, {
      params: { days },
    });

    console.log('[API] Raw response:', response.data);

    // Transform the response to match the expected format for the chart
    if (response.data && response.data.data) {
      const transformed = response.data.data.map(item => ({
        date: item.trade_date,
        close: item.close,
        open: item.open,
        high: item.high,
        low: item.low,
        volume: item.volume,
      }));
      // Reverse the array so oldest date is first (left side of chart)
      transformed.reverse();
      console.log(`[API] Transformed ${transformed.length} records for chart (oldest to newest)`);
      return transformed;
    }
    console.warn('[API] No data found in response.data.data');
    return [];
  },

  // Update single stock historical data
  updateStockHistory: async (ticker) => {
    const response = await api.post(`/api/stocks/${ticker}/update-history`);
    return response.data;
  },

  // Bulk update all stocks
  bulkUpdateHistory: async () => {
    const response = await api.post('/api/stocks/bulk-update-history');
    return response.data;
  },

  // Get database statistics
  getHistoryStats: async () => {
    const response = await api.get('/api/stocks/history/stats');
    return response.data;
  },

  // Get upcoming IPOs
  getUpcomingIPOs: async () => {
    const response = await api.get('/api/stocks/upcoming-ipos');
    return response.data;
  },

  // Get portfolio companies
  getPortfolioCompanies: async (forceRefresh = false) => {
    const response = await api.get('/api/stocks/portfolio', {
      params: { force_refresh: forceRefresh }
    });
    return response.data;
  },

  // Get returns (% gain/loss) for different time periods
  getReturns: async (ticker) => {
    const response = await api.get(`/api/stocks/${ticker}/returns`);
    return response.data;
  },

  // Get AI news analysis for a specific stock (async loading)
  getNewsAnalysis: async (ticker, forceRefresh = false, generalNews = false) => {
    const response = await api.get(`/api/stocks/price/${ticker}/news-analysis`, {
      params: {
        force_refresh: forceRefresh,
        general_news: generalNews
      }
    });
    return response.data;
  },
};

// Watchlist API (CapIQ integration)
export const watchlistAPI = {
  // Search for companies across markets
  searchCompanies: async (query, market = null, limit = 10) => {
    const params = { query, limit };
    if (market) params.market = market;
    const response = await api.get('/api/watchlist/search', { params });
    return response.data;
  },

  // Add company to watchlist
  addToWatchlist: async (ticker, market = 'US') => {
    const response = await api.post('/api/watchlist/add', null, {
      params: { ticker, market }
    });
    return response.data;
  },

  // Remove company from watchlist
  removeFromWatchlist: async (ticker, market = 'US') => {
    const response = await api.delete('/api/watchlist/remove', {
      params: { ticker, market }
    });
    return response.data;
  },

  // Get user's watchlist with live data
  getWatchlist: async () => {
    const response = await api.get('/api/watchlist/list');
    return response.data;
  },

  // Get detailed company information
  getCompanyDetails: async (ticker, market = 'US') => {
    const response = await api.get(`/api/watchlist/company/${ticker}`, {
      params: { market }
    });
    return response.data;
  },
};

// AI Search API functions (matching HTML version API)
export const uploadFile = async (file, conversationId = null, relativePath = null, abortSignal = null) => {
  const formData = new FormData();
  formData.append('file', file);
  if (conversationId) {
    formData.append('conversation_id', conversationId);
  }
  if (relativePath) {
    formData.append('relative_path', relativePath);
  }

  try {
    const response = await api.post('/api/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      signal: abortSignal, // Support abort during upload
    });
    return response.data;
  } catch (error) {
    if (error.name === 'CanceledError' || error.code === 'ERR_CANCELED') {
      throw new Error('Upload cancelled by user');
    }
    throw new Error(error.response?.data?.detail || 'Upload failed');
  }
};

export const searchDocuments = async (searchRequest, abortSignal = null) => {
  try {
    const response = await api.post('/api/search', searchRequest, {
      signal: abortSignal
    });
    return response.data;
  } catch (error) {
    if (error.name === 'CanceledError' || error.code === 'ERR_CANCELED') {
      throw new Error('Search cancelled by user');
    }
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

export const cancelJob = async (jobId) => {
  try {
    const response = await api.post(`/api/jobs/${jobId}/cancel`);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Failed to cancel job');
  }
};

// Search Job API (for long-running searches with reasoning_gpt5 and deep_research)
export const getSearchJobStatus = async (jobId) => {
  try {
    const response = await api.get(`/api/search-jobs/${jobId}`);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Failed to fetch search job status');
  }
};

export const cancelSearchJob = async (jobId) => {
  try {
    const response = await api.post(`/api/search-jobs/${jobId}/cancel`);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Failed to cancel search job');
  }
};

// IC Simulator API
export const icSimulatorAPI = {
  // Sync meeting notes from Confluence (optionally within a date range)
  syncConfluence: async (limit = 200, dateFrom = '', dateTo = '') => {
    const body = { limit };
    if (dateFrom) body.date_from = dateFrom;
    if (dateTo) body.date_to = dateTo;
    const response = await api.post('/api/ic-simulator/sync-confluence', body);
    return response.data;
  },

  // Get sync status
  getSyncStatus: async () => {
    const response = await api.get('/api/ic-simulator/sync-status');
    return response.data;
  },

  // Test Confluence connection
  testConnection: async () => {
    const response = await api.get('/api/ic-simulator/confluence-test');
    return response.data;
  },

  // List indexed meetings
  getMeetings: async () => {
    const response = await api.get('/api/ic-simulator/meetings');
    return response.data;
  },

  // Delete a meeting from the index
  deleteMeeting: async (pageId) => {
    const response = await api.delete(`/api/ic-simulator/meetings/${pageId}`);
    return response.data;
  },

  // Upload a meeting note file
  uploadMeeting: async (file, meetingDate = '') => {
    const formData = new FormData();
    formData.append('file', file);
    if (meetingDate) formData.append('meeting_date', meetingDate);
    const response = await api.post('/api/ic-simulator/upload-meeting', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  // Get extraction pipeline status
  getExtractionStatus: async () => {
    const response = await api.get('/api/ic-simulator/extraction/status');
    return response.data;
  },

  // Generate anticipated IC questions (optionally scoped to a date range of meetings)
  generateQuestions: async (projectDescription, files = [], dateFrom = '', dateTo = '') => {
    const formData = new FormData();
    formData.append('project_description', projectDescription || '');
    for (const file of files) {
      formData.append('files', file);
    }
    if (dateFrom) formData.append('date_from', dateFrom);
    if (dateTo) formData.append('date_to', dateTo);
    const response = await api.post('/api/ic-simulator/generate-questions', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 300000, // 5 min timeout for LLM generation
    });
    return response.data;
  },
};

export default api;
