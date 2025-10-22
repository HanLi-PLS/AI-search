# AI Document Search Tool

An internal AI-powered document search system with semantic search capabilities and support for multiple file formats.

## Features

- **Multi-Format Support**: PDF, DOCX, TXT, MD, CSV, XLSX, PPTX, HTML, JSON, EML
- **Advanced PDF Processing**: Extracts text, images, and tables using GPT-4o Vision
- **Semantic Search**: Vector-based similarity search using sentence-transformers
- **Modern Web Interface**: Clean, responsive HTML/CSS/JS interface
- **RESTful API**: FastAPI backend with comprehensive endpoints
- **Vector Database**: Qdrant for efficient similarity search
- **Easy Deployment**: Docker Compose for one-command setup

## Architecture

```
┌─────────────┐
│   Browser   │
│  (HTML/JS)  │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   FastAPI   │
│   Backend   │
└──────┬──────┘
       │
       ├──────► Qdrant (Vector DB)
       │
       ├──────► OpenAI GPT-4o (PDF Processing)
       │
       └──────► S3 (Optional)
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- OpenAI API key
- (Optional) AWS credentials for S3 integration

### Installation

1. **Clone the repository**
   ```bash
   cd AI-search
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and add your OpenAI API key
   ```

3. **Start the services**
   ```bash
   docker-compose up -d
   ```

4. **Access the application**
   - Web Interface: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Manual Setup (Without Docker)

1. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Start Qdrant**
   ```bash
   docker run -p 6333:6333 -p 6334:6334 \
       -v $(pwd)/qdrant_storage:/qdrant/storage \
       qdrant/qdrant
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

5. **Run the application**
   ```bash
   python -m uvicorn backend.app.main:app --reload
   ```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key (required) | - |
| `QDRANT_HOST` | Qdrant server host | localhost |
| `QDRANT_PORT` | Qdrant server port | 6333 |
| `EMBEDDING_MODEL` | Sentence-transformer model | all-MiniLM-L6-v2 |
| `CHUNK_SIZE` | Text chunk size | 1000 |
| `CHUNK_OVERLAP` | Text chunk overlap | 200 |
| `MAX_FILE_SIZE_MB` | Maximum file size | 100 |
| `AWS_S3_BUCKET` | S3 bucket (optional) | - |

### Embedding Models

You can use different embedding models by changing `EMBEDDING_MODEL`:

- `sentence-transformers/all-MiniLM-L6-v2` (default, fast, 384 dim)
- `BAAI/bge-base-en-v1.5` (better quality, 768 dim)
- `BAAI/bge-large-en-v1.5` (best quality, 1024 dim)

## API Endpoints

### Upload Endpoints

**POST /api/upload**
- Upload a single file
- Body: multipart/form-data with `file` field
- Response: Upload confirmation with chunk count

**POST /api/upload-batch**
- Upload multiple files
- Body: multipart/form-data with multiple `files`
- Response: Array of upload confirmations

### Search Endpoints

**POST /api/search**
- Search documents
- Body:
  ```json
  {
    "query": "your search query",
    "top_k": 10,
    "file_types": [".pdf", ".docx"],
    "date_from": "2025-01-01T00:00:00",
    "date_to": "2025-12-31T23:59:59"
  }
  ```
- Response: Search results with relevance scores

**GET /api/documents**
- List all uploaded documents
- Response: Array of document metadata

**DELETE /api/documents/{file_id}**
- Delete a document and its chunks
- Response: Deletion confirmation

**GET /api/health**
- Health check endpoint
- Response: System status

## Usage

### Web Interface

1. **Upload Documents**
   - Drag and drop files or click to browse
   - Supports batch uploads
   - Progress tracking for each file

2. **Search Documents**
   - Enter natural language queries
   - Adjust number of results
   - View relevance scores and metadata

3. **Manage Documents**
   - View all uploaded documents
   - Delete documents
   - See chunk counts and file sizes

### API Usage

```python
import requests

# Upload a file
with open('document.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/upload',
        files={'file': f}
    )
    print(response.json())

# Search
response = requests.post(
    'http://localhost:8000/api/search',
    json={
        'query': 'What is machine learning?',
        'top_k': 5
    }
)
results = response.json()
for result in results['results']:
    print(f"Score: {result['score']}")
    print(f"Content: {result['content']}\n")
```

## Supported File Formats

| Format | Extension | Loader |
|--------|-----------|--------|
| PDF | .pdf | PyMuPDF + GPT-4o Vision |
| Word | .docx, .doc | Docx2txt |
| Excel | .xlsx, .xls | UnstructuredExcel |
| PowerPoint | .pptx, .ppt | Azure AI Document Intelligence |
| Text | .txt | TextLoader |
| Markdown | .md | UnstructuredMarkdown |
| HTML | .html, .htm | UnstructuredHTML |
| CSV | .csv | CSVLoader |
| JSON | .json | JSONLoader |
| Email | .eml | UnstructuredFile |

## PDF Processing

The system uses a sophisticated PDF processing pipeline:

1. **Text Extraction**: Extracts raw text from each page
2. **Image Detection**: Identifies pages with embedded images or tables
3. **Vision Processing**: Uses GPT-4o to extract information from images and tables
4. **Metadata Preservation**: Keeps page numbers, image presence, table presence

## Deployment

### AWS EC2 Deployment

1. **Launch EC2 instance**
   - Amazon Linux 2 or Ubuntu
   - t3.medium or larger (for embedding model)
   - Open ports: 80, 443, 8000

2. **Install Docker**
   ```bash
   sudo yum install -y docker
   sudo service docker start
   sudo usermod -a -G docker ec2-user
   ```

3. **Install Docker Compose**
   ```bash
   sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
   sudo chmod +x /usr/local/bin/docker-compose
   ```

4. **Deploy application**
   ```bash
   git clone <your-repo>
   cd AI-search
   cp .env.example .env
   # Edit .env with production values
   docker-compose up -d
   ```

5. **Set up Nginx (optional)**
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;

       location / {
           proxy_pass http://localhost:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

### Production Considerations

- Use environment-specific `.env` files
- Set up SSL/TLS certificates
- Configure firewall rules
- Set up monitoring and logging
- Regular backups of Qdrant storage
- Consider using managed Qdrant Cloud

## Migrating to React (Future)

The current HTML/JS frontend can be easily migrated to React:

1. **Backend stays the same** (RESTful API)
2. **Create React app**
   ```bash
   npx create-react-app frontend-react
   ```
3. **Reuse API calls** from `app.js`
4. **Port components** from HTML to React components
5. **Keep same API endpoints**

Estimated effort: 3-4 days

## Troubleshooting

### Qdrant Connection Error
```bash
# Check if Qdrant is running
docker ps | grep qdrant

# Restart Qdrant
docker-compose restart qdrant
```

### Embedding Model Download Issues
```bash
# Models are downloaded on first use
# Check available disk space
df -h

# Manually download model
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"
```

### OpenAI API Errors
- Check API key is set in `.env`
- Verify API key is valid
- Check rate limits

## Contributing

This is an internal tool. For improvements:
1. Create a feature branch
2. Test thoroughly
3. Submit for review

## License

Internal use only.

## Support

For issues or questions, contact the development team.

---

**Built with**: FastAPI, Qdrant, OpenAI GPT-4o, LangChain, Sentence-Transformers
