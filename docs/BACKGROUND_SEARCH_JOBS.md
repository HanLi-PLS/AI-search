# Background Search Jobs - Long-Running Searches

## Overview

This feature enables long-running AI searches (like `reasoning_gpt5` and `deep_research` modes) to run in the background without timing out, even if the user closes their browser or computer goes to sleep.

## Problem Statement

Some reasoning models take 9+ minutes or even 30+ minutes to complete:
- `gpt-5-pro`: ~9-10 minutes
- `o3-deep-research`: 30+ minutes

Traditional HTTP requests timeout after 2-5 minutes, causing "search failed" errors even though the backend is still processing.

## Solution

Implement a background job system similar to file uploads:

1. **Detect long searches**: `reasoning_gpt5` and `deep_research` modes automatically use background processing
2. **Return immediately**: API returns a `job_id` instead of results
3. **Process in background**: Backend continues processing asynchronously
4. **Poll for status**: Frontend polls the job status endpoint
5. **Retrieve results**: When complete, frontend fetches and displays results

## Architecture

```
User initiates search (reasoning_gpt5 or deep_research)
    ↓
POST /api/search (returns job_id immediately)
    ↓
Backend creates search job in database
    ↓
Background worker processes search
    ↓
Frontend polls GET /api/search-jobs/{job_id}
    ↓
When status = "completed", retrieve results
```

## Database Schema

```sql
CREATE TABLE search_jobs (
    job_id TEXT PRIMARY KEY,
    query TEXT NOT NULL,
    search_mode TEXT NOT NULL,
    reasoning_mode TEXT NOT NULL,
    conversation_id TEXT,
    status TEXT NOT NULL,  -- pending, processing, completed, failed, cancelled
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    progress INTEGER DEFAULT 0,  -- 0-100%
    current_step TEXT DEFAULT '',  -- "Step 0", "Step 1", "Step 2", "Step 3"
    error_message TEXT,
    answer TEXT,
    extracted_info TEXT,
    online_search_response TEXT,
    results TEXT (JSON),
    total_results INTEGER DEFAULT 0,
    processing_time REAL DEFAULT 0.0
)
```

## API Endpoints

### 1. POST /api/search
**Behavior**:
- If `reasoning_mode` is `non_reasoning` or `reasoning`: Returns results immediately (synchronous)
- If `reasoning_mode` is `reasoning_gpt5` or `deep_research`: Returns job_id (asynchronous)

**Request**:
```json
{
  "query": "What are the competitors of PPInnova?",
  "search_mode": "sequential_analysis",
  "reasoning_mode": "reasoning_gpt5",  // or "deep_research"
  "top_k": 10
}
```

**Response (Async Mode)**:
```json
{
  "success": true,
  "job_id": "search_1234567890",
  "message": "Search is processing in background. Poll /api/search-jobs/{job_id} for status.",
  "estimated_time": "5-10 minutes"
}
```

**Response (Sync Mode)**:
```json
{
  "success": true,
  "answer": "...",
  "results": [...]
}
```

### 2. GET /api/search-jobs/{job_id}
**Get job status and results**

**Response (Processing)**:
```json
{
  "job_id": "search_1234567890",
  "status": "processing",
  "progress": 45,
  "current_step": "Step 2: Performing online search",
  "created_at": "2025-12-03T08:00:00",
  "updated_at": "2025-12-03T08:05:30"
}
```

**Response (Completed)**:
```json
{
  "job_id": "search_1234567890",
  "status": "completed",
  "progress": 100,
  "query": "What are the competitors of PPInnova?",
  "answer": "Full answer...",
  "extracted_info": "Step 1 results...",
  "online_search_response": "Step 2 results...",
  "results": [...],
  "total_results": 10,
  "processing_time": 546.2
}
```

### 3. POST /api/search-jobs/{job_id}/cancel
**Cancel a running search job**

**Response**:
```json
{
  "success": true,
  "message": "Search job cancelled"
}
```

## Progress Tracking

Jobs report progress at each step:

**Sequential Analysis Mode**:
- 0%: Job created
- 10%: Step 0 starting (Query Analysis)
- 20%: Step 0 complete
- 25%: Step 1 starting (Extraction)
- 40%: Step 1 complete
- 45%: Step 2 starting (Online Search)
- 80%: Step 2 complete
- 85%: Step 3 starting (Final Synthesis)
- 100%: Step 3 complete

**Other Modes**:
- 0%: Job created
- 20%: Processing started
- 50%: Generating answer
- 100%: Complete

## Frontend Integration

### Detect Async Mode
```javascript
// Frontend checks reasoning_mode before sending request
const isLongRunning = ['reasoning_gpt5', 'deep_research'].includes(reasoningMode);

if (isLongRunning) {
  // Start background job and poll for results
  const response = await searchDocuments({...});
  if (response.job_id) {
    pollSearchJob(response.job_id);
  }
} else {
  // Handle synchronous response as before
  const response = await searchDocuments({...});
  displayResults(response);
}
```

### Poll for Results
```javascript
const pollSearchJob = async (jobId) => {
  const interval = setInterval(async () => {
    const status = await getSearchJobStatus(jobId);

    updateProgress(status.progress, status.current_step);

    if (status.status === 'completed') {
      clearInterval(interval);
      displayResults(status);
    } else if (status.status === 'failed') {
      clearInterval(interval);
      showError(status.error_message);
    }
  }, 2000);  // Poll every 2 seconds
};
```

## Benefits

1. **No Timeouts**: Searches can run for hours without timing out
2. **Survives Disconnects**: Job continues even if user closes browser
3. **Progress Feedback**: User sees real-time progress updates
4. **Cancellable**: User can cancel long-running searches
5. **Persistent**: Results saved in database and retrievable later
6. **Scalable**: Multiple searches can run concurrently

## Configuration

Configure which modes use background processing:

```python
# backend/app/config.py
ASYNC_SEARCH_MODES = ["reasoning_gpt5", "deep_research"]  # Modes that use background jobs
SEARCH_JOB_POLL_INTERVAL = 2  # Frontend poll interval in seconds
SEARCH_JOB_MAX_RETENTION = 24  # Keep jobs for 24 hours
```

## Future Enhancements

1. **WebSocket Support**: Real-time push updates instead of polling
2. **Email Notifications**: Notify user when long search completes
3. **Job History**: View past search jobs and results
4. **Concurrent Limit**: Limit number of concurrent searches per user
5. **Priority Queue**: Priority-based job scheduling
