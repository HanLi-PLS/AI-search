from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import stocks, ai_search

app = FastAPI(
    title="AI Search Platform API",
    description="API for AI-powered document search, RAG Q&A, and HKEX biotech stock tracking",
    version="2.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(stocks.router)
app.include_router(ai_search.router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "AI Search Platform API",
        "version": "2.0.0",
        "features": [
            "AI-powered document search and Q&A",
            "HKEX biotech stock tracking",
            "Company intelligence extraction"
        ],
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
