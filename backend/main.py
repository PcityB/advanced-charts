from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from config.settings import settings
from api import datafeed, replay, patterns, template_grid
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.DEBUG else logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Trading Simulator API",
    description="Bar Replay Trading Simulator with Pattern Detection",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True, # Allows cookies and authorization headers
    allow_methods=["*"],  # Allows all methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allows all headers
)

# Include routers
app.include_router(datafeed.router)
app.include_router(replay.router)
app.include_router(patterns.router)
app.include_router(template_grid.router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Trading Simulator API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "datafeed": "/api/v1/config, /api/v1/history, /api/v1/symbols",
            "replay": "/api/v1/replay/sessions",
            "patterns": "/api/v1/patterns/scan, /api/v1/patterns/signals",
            "docs": "/docs",
            "health": "/health"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        import asyncpg
        conn = await asyncpg.connect(
            host=settings.DATABASE_HOST,
            port=settings.DATABASE_PORT,
            user=settings.DATABASE_USER,
            password=settings.DATABASE_PASSWORD,
            database=settings.DATABASE_NAME
        )
        await conn.close()
        
        return {
            "status": "healthy",
            "database": "connected",
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Service unavailable: {str(e)}"
        )


@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    logger.info("Starting Trading Simulator API")
    logger.info(f"Database: {settings.DATABASE_HOST}:{settings.DATABASE_PORT}")
    logger.info(f"CORS Origins: {settings.CORS_ORIGINS}")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown"""
    logger.info("Shutting down Trading Simulator API")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_level="info" if settings.DEBUG else "warning"
    )
