module.exports = {
  apps: [
    {
      name: 'ai-search-backend',
      cwd: '/home/user/AI-search',
      script: '/usr/local/bin/python3',
      args: '-m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '6G',
      env: {
        NODE_ENV: 'production',
      },
      error_file: '/home/user/AI-search/logs/backend-error.log',
      out_file: '/home/user/AI-search/logs/backend-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
    },
    {
      name: 'ai-search-frontend',
      cwd: '/home/user/AI-search/frontend',
      script: 'npx',
      args: 'serve -s dist -l 5173',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '500M',
      env: {
        NODE_ENV: 'production',
      },
      error_file: '/home/user/AI-search/logs/frontend-error.log',
      out_file: '/home/user/AI-search/logs/frontend-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
    }
  ]
};
