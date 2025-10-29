# Quick Start Guide

Get the AI Document Search Tool running in 5 minutes!

## Prerequisites

- Docker and Docker Compose installed
- OpenAI API key

## Installation Steps

### 1. Set Up Environment

```bash
# Copy environment template
cp .env.example .env

# Edit and add your OpenAI API key
nano .env
# Set: OPENAI_API_KEY=your-key-here
```

### 2. Start the Application

```bash
# Easy way - using the startup script
./start.sh

# Or manually
docker-compose up -d
```

### 3. Access the Application

- **Web Interface**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Qdrant Dashboard**: http://localhost:6333/dashboard

## First Use

### Upload Your First Document

1. Open http://localhost:8000
2. Drag and drop a PDF, DOCX, or TXT file
3. Wait for processing to complete
4. You'll see confirmation with chunk count

### Search Your Documents

1. Enter a natural language query (e.g., "What is the main topic?")
2. Click Search
3. View results with relevance scores

### Manage Documents

1. Scroll to "Uploaded Documents" section
2. View all uploaded files
3. Click "Delete" to remove documents

## Common Commands

```bash
# Start services
./start.sh

# Stop services
./stop.sh

# View logs
docker-compose logs -f

# Restart services
docker-compose restart

# Stop and remove all data
docker-compose down -v
```

## Troubleshooting

### Port Already in Use

```bash
# Stop existing services
docker-compose down

# Or change port in docker-compose.yml
# Change "8000:8000" to "8080:8000"
```

### Qdrant Connection Error

```bash
# Restart Qdrant
docker-compose restart qdrant

# Wait a few seconds
sleep 5

# Restart backend
docker-compose restart backend
```

### Out of Memory

If you see memory errors:
1. Close other applications
2. Restart Docker Desktop
3. Increase Docker memory limit (Docker Settings → Resources)

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Check [DEPLOYMENT_AWS.md](DEPLOYMENT_AWS.md) for cloud deployment
- Explore the API at http://localhost:8000/docs

## Support

For issues:
1. Check logs: `docker-compose logs`
2. Ensure Docker is running
3. Verify .env file has valid API key
4. Check disk space: `df -h`

---

**Need help?** Check the logs and README.md for detailed troubleshooting.
