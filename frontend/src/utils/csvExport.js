/**
 * CSV Export Utilities
 * Helper functions for exporting data to CSV files
 */

/**
 * Convert array of objects to CSV string
 * @param {Array} data - Array of objects to convert
 * @param {Array} columns - Column definitions [{ key, header }]
 * @returns {string} CSV string
 */
export const convertToCSV = (data, columns) => {
  if (!data || data.length === 0) {
    return '';
  }

  // Create header row
  const headers = columns.map(col => col.header).join(',');

  // Create data rows
  const rows = data.map(item => {
    return columns.map(col => {
      let value = col.accessor ? col.accessor(item) : item[col.key];

      // Handle null/undefined
      if (value === null || value === undefined) {
        return '';
      }

      // Convert to string
      value = String(value);

      // Escape quotes and wrap in quotes if contains comma, quote, or newline
      if (value.includes(',') || value.includes('"') || value.includes('\n')) {
        value = `"${value.replace(/"/g, '""')}"`;
      }

      return value;
    }).join(',');
  });

  return [headers, ...rows].join('\n');
};

/**
 * Download CSV file
 * @param {string} csvContent - CSV content as string
 * @param {string} filename - Filename (without .csv extension)
 */
export const downloadCSV = (csvContent, filename) => {
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');

  if (link.download !== undefined) {
    // Create download link
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `${filename}.csv`);
    link.style.visibility = 'hidden';

    // Trigger download
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    // Clean up
    URL.revokeObjectURL(url);
  }
};

/**
 * Export watchlist to CSV
 * @param {Array} watchlist - Array of watchlist items
 */
export const exportWatchlistToCSV = (watchlist) => {
  const columns = [
    { key: 'company_name', header: 'Company Name' },
    { key: 'ticker', header: 'Ticker' },
    { key: 'market', header: 'Market' },
    { key: 'exchange_symbol', header: 'Exchange' },
    { key: 'industry', header: 'Industry' },
    {
      key: 'price',
      header: 'Price',
      accessor: (item) => item.live_data?.price_close || 'N/A'
    },
    {
      key: 'volume',
      header: 'Volume',
      accessor: (item) => item.live_data?.volume || 'N/A'
    },
    {
      key: 'market_cap',
      header: 'Market Cap',
      accessor: (item) => item.live_data?.market_cap || 'N/A'
    },
    {
      key: 'ttm_revenue',
      header: 'Revenue (LTM)',
      accessor: (item) => item.live_data?.ttm_revenue || 'N/A'
    },
    {
      key: 'ttm_revenue_currency',
      header: 'Revenue Currency',
      accessor: (item) => item.live_data?.ttm_revenue_currency || 'N/A'
    },
    {
      key: 'exchange_rate_used',
      header: 'Exchange Rate Used',
      accessor: (item) => item.live_data?.exchange_rate_used || 'N/A'
    },
    {
      key: 'ps_ratio',
      header: 'P/S Ratio',
      accessor: (item) => item.live_data?.ps_ratio || 'N/A'
    },
    {
      key: 'listing_date',
      header: 'Listing Date',
      accessor: (item) => item.live_data?.listing_date || 'N/A'
    },
    {
      key: 'pricing_date',
      header: 'Data Date',
      accessor: (item) => item.live_data?.pricing_date || 'N/A'
    },
    { key: 'webpage', header: 'Website' },
    {
      key: 'added_at',
      header: 'Added At',
      accessor: (item) => new Date(item.added_at).toLocaleString()
    }
  ];

  const csvContent = convertToCSV(watchlist, columns);
  const timestamp = new Date().toISOString().split('T')[0];
  downloadCSV(csvContent, `watchlist_export_${timestamp}`);
};

/**
 * Export stock tracker data to CSV
 * @param {Array} stocks - Array of stock items
 * @param {string} tabName - Name of the tab (for filename)
 */
export const exportStockTrackerToCSV = (stocks, tabName = 'stocks') => {
  const columns = [
    { key: 'name', header: 'Company Name' },
    { key: 'ticker', header: 'Ticker' },
    { key: 'current_price', header: 'Current Price' },
    { key: 'change', header: 'Change' },
    { key: 'change_percent', header: 'Change %' },
    { key: 'volume', header: 'Volume' },
    { key: 'market_cap', header: 'Market Cap' },
    { key: 'day_high', header: 'Day High' },
    { key: 'day_low', header: 'Day Low' },
    { key: 'open', header: 'Open' },
    { key: 'previous_close', header: 'Previous Close' }
  ];

  const csvContent = convertToCSV(stocks, columns);
  const timestamp = new Date().toISOString().split('T')[0];
  const filename = `${tabName}_export_${timestamp}`;
  downloadCSV(csvContent, filename);
};
