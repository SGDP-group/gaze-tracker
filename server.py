"""
FastAPI main application for the Focus Management System.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn

from src.database.database import create_tables
from src.api.routes import router
from src.services.image_stream_server import image_stream_server


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    try:
        create_tables()
        print("Database initialized successfully")
        image_stream_server.start()
        print("Image stream server started")
    except Exception as e:
        print(f"Failed to initialize services: {e}")
        raise
    yield
    try:
        image_stream_server.stop()
        print("Image stream server stopped")
    except Exception as e:
        print(f"Failed to stop image stream server: {e}")

# Create FastAPI app
app = FastAPI(
    title="Focus Management System API",
    description="API for personalized focus tracking and productivity analysis",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router, prefix="/api/v1", tags=["focus-management"])


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)}
    )


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Focus Management System API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health"
    }


if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8002,
        reload=True,
        log_level="info"
    )
