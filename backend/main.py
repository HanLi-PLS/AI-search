from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import stocks

app = FastAPI(
    title="HKEX Biotech Stock Tracker API",
    description="API for tracking HKEX 18A biotech company stock prices and upcoming IPOs",
    version="1.0.0"
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


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "HKEX Biotech Stock Tracker API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
