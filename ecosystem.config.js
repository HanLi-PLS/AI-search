module.exports = {
  apps: [
    {
      name: 'ai-search-backend',
      script: './start_backend.sh',
      interpreter: 'bash',
      instances: 6,  // Run 6 instances for load balancing
      exec_mode: 'cluster',  // Use PM2 cluster mode for load balancing
      autorestart: true,
      watch: false,
      max_memory_restart: '6G',
      env: {
        NODE_ENV: 'production',
      },
      error_file: './logs/backend-error.log',
      out_file: './logs/backend-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
    },
    {
      name: 'ai-search-frontend',
      cwd: './frontend',
      script: 'npm',
      args: 'run dev -- --host 0.0.0.0',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '500M',
      env: {
        NODE_ENV: 'development',
      },
      error_file: '../logs/frontend-error.log',
      out_file: '../logs/frontend-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
    }
  ]
};
