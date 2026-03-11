# AI Document Search Platform

A production-ready AI-powered document search platform with semantic search, online search integration, and intelligent answer generation. Built for bioventure investing research with support for multiple document formats and background processing.

## ✨ Key Features

### 🔍 Intelligent Search Modes
- **Auto Mode** - Automatically selects the best search strategy based on query type
- **Files Only** - Search uploaded documents only
- **Online Only** - Real-time web search for current information
- **Both** - Parallel search of files and online sources with configurable priority
- **Sequential Analysis** - Extract from files first, then search online using extracted info

### 📄 Document Processing
- **Multi-format Support** - PDF, DOCX, PPTX, XLSX, CSV, TXT, MD, HTML, JSON, EML
- **ZIP Archive Processing** - Upload zip files with parallel processing of all contents
- **Background Processing** - Close browser while files continue processing on server
- **Vision AI for PDFs** - Extract text and data from images/charts using o4-mini
- **Folder Preservation** - Maintains folder structure in filenames (folder1/doc.pdf → folder1_doc.pdf)
- **Comprehensive Error Handling** - Detailed reporting of failed/skipped files with reasons

### 🤖 AI Models & Search
- **Multiple Reasoning Modes**:
  - Non-Reasoning (gpt-5.1) - Fast, balanced responses
  - Reasoning (o4-mini) - Extended reasoning chains
  - Reasoning GPT-5 (gpt-5-pro) - Advanced reasoning capabilities
  - Reasoning Gemini (gemini-pro-latest) - Google's reasoning model
  - Deep Research (o3-deep-research) - Comprehensive research synthesis
- **Hybrid Search** - Combines BM25 (keyword) and dense vector (semantic) search
- **Conversation History** - Context-aware multi-turn conversations
- **Conversation Management** - Create, switch, and delete conversation threads

### 🗄️ Storage & Infrastructure
- **Qdrant Vector Database** - High-performance vector search with on-disk payload storage
- **Alibaba-NLP Embeddings** - Fast multilingual embeddings (768 dimensions)
- **S3 Integration** - Document storage with AWS S3
- **PM2 Process Management** - Production deployment with auto-restart
- **Automated Backups** - Weekly Qdrant snapshots to S3

### 📊 HKEX Biotech Stock Tracker
- Real-time stock price tracking for HKEX 18A biotech companies
- Track 20+ companies including BeiGene, Innovent Biologics, Akeso
- Historical data and price change tracking

## 🏗️ Architecture

### Tech Stack

**Backend (FastAPI)**
- FastAPI web framework with async support
- Qdrant vector database
- Alibaba-NLP/gte-multilingual-base embeddings (768 dim)
- OpenAI API models:
  - gpt-5.1 (default/non-reasoning)
  - o4-mini (reasoning, vision, online search)
  - gpt-5-pro (advanced reasoning)
  - o3-deep-research (comprehensive research)
- Google Gemini API (gemini-pro-latest for reasoning)
- BM25Okapi for keyword search
- PyMuPDF for PDF processing with vision AI
- python-docx, openpyxl for Office documents
- AWS SDK (boto3) for S3 integration

**Frontend (React 19)**
- React 19 with Vite build tool
- React Router for navigation
- Axios for API communication
- Custom hooks for conversation management
- Markdown rendering with syntax highlighting

**Deployment**
- PM2 for process management
- Nginx as reverse proxy (production)
- systemd for Qdrant service
- cron for automated backups

### Project Structure

```
AI-search/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── routes/
│   │   │       ├── upload.py          # File upload & background processing
│   │   │       └── search.py          # Search & document management
│   │   ├── core/
│   │   │   ├── answer_generator.py   # GPT-based answer generation
│   │   │   ├── document_processor.py # Multi-format document processing
│   │   │   ├── embedding_generator.py # Vector embeddings
│   │   │   ├── vector_store.py       # Qdrant operations
│   │   │   └── job_tracker.py        # Background job tracking
│   │   ├── models/
│   │   │   └── schemas.py            # Pydantic models
│   │   ├── utils/
│   │   │   ├── aws_secrets.py        # AWS Secrets Manager
│   │   │   └── s3_storage.py         # S3 operations
│   │   └── config.py                 # Configuration settings
│   ├── main.py                       # FastAPI application
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── AISearch.jsx          # Main search interface
│   │   │   ├── Home.jsx              # Landing page
│   │   │   └── StockTracker.jsx      # Stock tracking
│   │   ├── hooks/
│   │   │   └── useChatHistory.js     # Conversation management
│   │   ├── services/
│   │   │   └── api.js                # API client
│   │   └── utils/
│   │       └── markdown.js           # Markdown utilities
│   ├── package.json
│   └── vite.config.js
│
├── scripts/
│   ├── backup_qdrant.sh              # Qdrant backup script
│   └── setup_optimization.sh         # Storage optimization setup
│
├── uploads/                          # Temporary upload directory
├── qdrant_storage/                   # Qdrant data directory
└── README.md

```

## 🚀 Getting Started

### Prerequisites

- **Python 3.9+** with pip
- **Node.js 18+** with npm
- **Docker** (for Qdrant)
- **OpenAI API Key** (required)
- **AWS Account** (optional, for S3 storage)

### 1. Backend Setup

```bash
# Navigate to backend
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys
```

### 2. Start Qdrant

```bash
# Using Docker
docker run -p 6333:6333 -p 6334:6334 \
  -v $(pwd)/qdrant_storage:/qdrant/storage:z \
  qdrant/qdrant
```

### 3. Run Backend

```bash
# Development
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Production with PM2
pm2 start "uvicorn backend.main:app --host 0.0.0.0 --port 8000" --name ai-search-backend
```

### 4. Frontend Setup

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### 5. Access Application

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Qdrant Dashboard**: http://localhost:6333/dashboard

## 📖 Usage

### Uploading Documents

1. **Single Files**: Drag & drop or click to browse (PDF, DOCX, XLSX, etc.)
2. **ZIP Archives**: Upload zip files for bulk processing
   - Automatically extracts and processes all supported files
   - Preserves folder structure in filenames
   - Reports skipped/failed files with reasons

### Search Modes

**Auto Mode (Recommended)**
```
Query: "What's the latest news about our drug candidate?"
→ Automatically selects: online_only (needs current info)
```

**Files Only**
```
Query: "Summarize our clinical trial results"
→ Searches only uploaded documents
```

**Sequential Analysis**
```
Query: "What's our drug efficacy and how does it compare to competitors?"
→ Extracts data from files → Searches online with that data
```

### Background Processing

- Upload files and get immediate response with job_id
- Close browser - processing continues on server
- Real-time progress updates when viewing page
- Detailed completion report with processed/failed/skipped files

### Conversation Management

- **New Chat**: Creates new conversation thread
- **Switch Conversations**: Access previous conversations from sidebar
- **Context Awareness**: Multi-turn conversations with full context
- **Document Isolation**: Each conversation has its own document set

## 🔧 Configuration

### Environment Variables (.env)

```bash
# OpenAI Configuration
OPENAI_API_KEY=sk-...
ANSWER_MODEL=gpt-5.1              # Base model for files_only mode
VISION_MODEL=o4-mini              # Model for PDF image/chart extraction
ONLINE_SEARCH_MODEL=o4-mini       # Used only for stock news analysis (not main search)

# Model Selection for Document Search:
# The model is automatically selected based on the reasoning mode you choose
# in the frontend dropdown. The ANSWER_MODEL/ONLINE_SEARCH_MODEL variables
# are NOT used for this - it's controlled by reasoning_mode only.
#
# Reasoning Mode → Model Used:
# - non_reasoning     → gpt-5.1
# - reasoning         → o4-mini
# - reasoning_gpt5    → gpt-5-pro
# - reasoning_gemini  → gemini-pro-latest
# - deep_research     → o3-deep-research

# Or use AWS Secrets Manager
USE_AWS_SECRETS=true
AWS_SECRET_NAME_OPENAI=openai-api-key
AWS_REGION=us-west-2

# Qdrant Configuration
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION_NAME=documents

# Embedding Configuration
EMBEDDING_MODEL=Alibaba-NLP/gte-multilingual-base

# Processing Configuration
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
MAX_FILE_SIZE_MB=100
MAX_CONCURRENT_VISION_CALLS=10

# S3 Configuration (Optional)
USE_S3_STORAGE=false
AWS_S3_BUCKET=your-bucket-name
```

### PM2 Ecosystem (ecosystem.config.js)

```javascript
module.exports = {
  apps: [
    {
      name: 'ai-search-backend',
      script: 'uvicorn',
      args: 'backend.main:app --host 0.0.0.0 --port 8000',
      cwd: '/opt/ai-search',
      env: {
        PYTHONPATH: '/opt/ai-search',
      }
    },
    {
      name: 'ai-search-frontend',
      script: 'npx',
      args: 'serve -s dist -l 5173',
      cwd: '/opt/ai-search/frontend'
    }
  ]
};
```

## 📊 API Endpoints

### Upload & Processing

**POST /api/upload**
```json
{
  "file": "<multipart file>",
  "conversation_id": "uuid" // optional
}
```
Response:
```json
{
  "success": true,
  "message": "File upload successful. Processing in background.",
  "file_name": "document.pdf",
  "file_id": "uuid",
  "job_id": "uuid",
  "status": "processing"
}
```

**GET /api/jobs/{job_id}**
```json
{
  "job_id": "uuid",
  "file_name": "archive.zip",
  "status": "completed",
  "total_files": 10,
  "processed_files": 8,
  "failed_files": 2,
  "total_chunks": 543,
  "file_results": [...]
}
```

### Search

**POST /api/search**
```json
{
  "query": "What are the clinical trial results?",
  "top_k": 10,
  "search_mode": "auto", // auto, files_only, online_only, both, sequential_analysis
  "reasoning_mode": "non_reasoning", // non_reasoning, reasoning, deep_research
  "priority_order": ["online_search", "files"],
  "conversation_history": [...],
  "conversation_id": "uuid"
}
```

### Document Management

- **GET /api/documents?conversation_id=uuid** - List documents
- **DELETE /api/documents/{file_id}** - Delete document

### Health Check

- **GET /api/health** - System status

## 🔒 Production Deployment

### 1. Set Up EC2 Instance

**Instance Type**: g4dn.xlarge (GPU-accelerated for fast embeddings)
- 4 vCPUs, 16 GB RAM, 1x NVIDIA T4 GPU
- 7-12x faster embeddings than CPU instances

**Important**: Use **Elastic IP** to maintain DNS stability during spot interruptions

```bash
# Install dependencies
sudo yum update -y
sudo yum install -y python3 python3-pip nodejs npm docker git

# Install PM2
sudo npm install -g pm2

# Start Docker & Qdrant with auto-restart
sudo systemctl start docker
sudo systemctl enable docker
docker run -d -p 6333:6333 -p 6334:6334 \
  -v /opt/qdrant_storage:/qdrant/storage:z \
  --restart always \
  --name ai-search-qdrant \
  qdrant/qdrant
```

**Critical for Spot Instances**: Use `--restart always` (not `unless-stopped`) to ensure Qdrant restarts after spot interruptions.

### 2. Deploy Application

```bash
# Clone repository
git clone https://github.com/your-repo/AI-search.git /opt/ai-search
cd /opt/ai-search

# Checkout the active branch
git checkout claude/upgrade-document-search-0146g7aVkVoKHACRKoW3X4y4

# Set up backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set up frontend
cd ../frontend
npm install
npm run build

# Start with PM2
cd ..
pm2 start ecosystem.config.js
pm2 save
pm2 startup
```

### 2.1. Quick Deployment (Updates)

Use the deployment script for quick updates:

```bash
cd /opt/ai-search
./deploy_unicode_fix.sh
```

This script:
- Pulls latest code from branch
- Builds frontend
- Restarts backend service
- Shows deployment status

### 3. Set Up Automated Backups

```bash
# Run optimization setup
bash scripts/setup_optimization.sh

# Install cron (if needed)
sudo yum install -y cronie
sudo systemctl start crond
sudo systemctl enable crond

# Verify cron job
crontab -l
# Should show: 0 2 * * 0 /opt/ai-search/scripts/backup_qdrant.sh
```

### 4. Configure Nginx

**Production Setup** - Serve built frontend and proxy API:

```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # Serve production frontend build
    location / {
        root /opt/ai-search/frontend/dist;
        try_files $uri $uri/ /index.html;

        # Cache static assets
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    # Proxy API requests to backend
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Long timeout for AI operations
        proxy_read_timeout 7200s;
        proxy_connect_timeout 7200s;
        proxy_send_timeout 7200s;
    }
}
```

### 5. Monitoring & Statistics

**Check User Activity (Last 7 Days)**

```bash
cd /opt/ai-search
sqlite3 -header -column data/db/search_jobs.db "
ATTACH DATABASE 'data/db/stocks.db' AS stocks;

SELECT
    u.email,
    COUNT(*) as searches,
    DATE(MIN(s.created_at)) as first_day,
    DATE(MAX(s.created_at)) as last_day
FROM search_jobs s
LEFT JOIN stocks.users u ON s.user_id = u.id
WHERE s.created_at >= datetime('now', '-7 days')
GROUP BY u.email
ORDER BY searches DESC;
"
```

**Daily Breakdown**

```bash
sqlite3 -header -column data/db/search_jobs.db "
ATTACH DATABASE 'data/db/stocks.db' AS stocks;

SELECT
    u.email,
    DATE(s.created_at) as date,
    COUNT(*) as searches
FROM search_jobs s
LEFT JOIN stocks.users u ON s.user_id = u.id
WHERE s.created_at >= datetime('now', '-7 days')
GROUP BY u.email, DATE(s.created_at)
ORDER BY date DESC, searches DESC;
"
```

**Check PM2 Status**

```bash
pm2 status
pm2 logs ai-search-backend --lines 50
pm2 monit
```

**Check Spot Instance Interruption History**

```bash
# View instance restart history
sudo journalctl -u amazon-ssm-agent | grep -i "reboot\|restart" | tail -20
```

## 🐛 Troubleshooting

### Backend Issues

**Qdrant Connection Failed**
```bash
# Check Qdrant is running
docker ps | grep qdrant
# Check port is accessible
curl http://localhost:6333/health
```

**Import Errors**
```bash
# Ensure PYTHONPATH is set
export PYTHONPATH=/path/to/AI-search
# Verify virtual environment
which python
```

**OpenAI API Errors**
```bash
# Check API key
echo $OPENAI_API_KEY
# Or check AWS Secrets Manager access
aws secretsmanager get-secret-value --secret-id openai-api-key
```

**NLTK Data Missing (Excel Upload Errors)**
```bash
# NLTK data is auto-downloaded on backend startup
# If missing, manually run:
cd /opt/ai-search/backend
source venv/bin/activate
python setup_nltk.py

# Then restart backend
pm2 restart ai-search-backend
```

### Frontend Issues

**API Connection Failed**
- Check backend is running: `curl http://localhost:8000/api/health`
- Verify CORS settings in backend config
- Check network tab in browser DevTools

**Build Errors**
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
```

## 📈 Recent Updates (This Branch)

### Latest Session Changes (December 2025)

**UX Improvements**
- ✅ **Claude-style Layout** - Search input moved below conversation for better UX
- ✅ **Auto-scroll** - Automatically scrolls to show latest messages
- ✅ **Unicode Support** - Proper display of Chinese characters and non-ASCII text
- ✅ **Cross-browser Sync** - Conversation history syncs across Chrome, Edge, etc.
- ✅ **Backend Conversation Storage** - All searches persisted to database

**Production Infrastructure**
- ✅ **GPU Acceleration** - Migrated to g4dn.xlarge for 7-12x faster embeddings
- ✅ **Spot Instance Resilience** - Auto-restart with Elastic IP for DNS stability
- ✅ **Qdrant Auto-restart** - Survives spot interruptions with `restart: always`
- ✅ **NLTK Data Setup** - Auto-downloads on startup for Excel file processing

**Bug Fixes**
- ✅ Fixed XLSX/Excel upload errors (missing NLTK tokenizer data)
- ✅ Fixed conversation history not syncing across browsers
- ✅ Fixed synchronous searches not saving to database
- ✅ Fixed JSON serialization for non-ASCII characters

### Previous Session Changes
- ✅ Migrated from HTML to React 19
- ✅ Implemented PM2 production deployment
- ✅ Switched from Qwen to Alibaba-NLP embeddings (768 dim)
- ✅ Migrated from ChromaDB to Qdrant vector database
- ✅ Added background file processing with job tracking
- ✅ Implemented zip file support with folder preservation
- ✅ Enhanced error handling with detailed failure reporting
- ✅ Added skipped file reporting (system files, unsupported types)
- ✅ Removed "Show all documents" checkbox - conversation-scoped files
- ✅ Updated o4-mini prompts to extract data points from charts
- ✅ Fixed sidebar collapse and file upload UI issues
- ✅ Added storage optimization with automated backups

### Breaking Changes from Previous Version
- Vector database changed: ChromaDB → Qdrant
- Embedding model changed: Qwen → Alibaba-NLP
- Upload response now returns job_id instead of immediate processing
- Frontend framework: HTML → React 19
- Conversation storage: localStorage → Backend database

## 🔄 Branching Strategy

### Current Branch
**Branch**: `claude/upgrade-document-search-0146g7aVkVoKHACRKoW3X4y4`

This branch contains all latest features and improvements listed above.

### To Continue Work in New Session

**Option 1: Continue on Same Branch (Recommended)**
```bash
# Just pull this branch - no merge needed
git checkout claude/upgrade-document-search-0146g7aVkVoKHACRKoW3X4y4
git pull origin claude/upgrade-document-search-0146g7aVkVoKHACRKoW3X4y4
```

**Option 2: Merge to Main First**
```bash
# Merge this branch to main
git checkout main
git merge claude/upgrade-document-search-0146g7aVkVoKHACRKoW3X4y4
git push origin main

# Then start new session from main
git checkout -b claude/new-feature-<session-id>
```

**For New Claude Code Session:**
1. You don't need to merge to main
2. Just specify this branch when starting the new session
3. Claude Code can read this README to understand all features
4. All work history is preserved in git commit messages

## 📝 Development Notes

### Key Design Decisions

**Why Qdrant over ChromaDB?**
- Better performance for large collections
- On-disk payload storage reduces memory usage
- Native support for filtering and hybrid search

**Why Alibaba-NLP Embeddings?**
- 3x faster than Qwen (critical for real-time search)
- Good multilingual support (English + Chinese)
- 768 dimensions - good balance of quality and speed

**Why Background Processing?**
- Large zip files can take minutes to process
- Better user experience - no browser timeouts
- Enables true "upload and forget" workflow

**Why Conversation-Scoped Documents?**
- Better organization for different research topics
- Prevents mixing unrelated documents in search results
- Cleaner UI without global document checkbox

## 🤝 Contributing

This is a production system for bioventure investing research. Contact the team before making changes.

## 📄 License

Proprietary - Internal use only

## 🆘 Support

For issues or questions:
1. Check the Troubleshooting section above
2. Review git commit messages for recent changes
3. Check PM2 logs: `pm2 logs`
4. Check application logs in the logs directory

---

**Last Updated**: 2025-12-17
**Current Version**: GPU-Accelerated + Cross-browser Sync + Claude-style UX
**Branch**: claude/upgrade-document-search-0146g7aVkVoKHACRKoW3X4y4
**Instance**: g4dn.xlarge GPU (AWS us-west-2c spot)
