"""
FastAPI Main Application
Demonstrates: Application structure, middleware, CORS, error handling
"""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging
import time

from .routes import router
from database import init_database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Personal Finance Intelligence API",
    description="Backend API for transaction analysis, categorization, and insights",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# ==================
# MIDDLEWARE
# ==================

# CORS - Allow frontend to access API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production: specify frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests with timing"""
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    logger.info(
        f"{request.method} {request.url.path} "
        f"completed in {process_time:.2f}s with status {response.status_code}"
    )
    
    return response

# ==================
# EXCEPTION HANDLERS
# ==================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "detail": exc.errors(),
            "status_code": 422
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "detail": str(exc),
            "status_code": 500
        }
    )

# ==================
# STARTUP/SHUTDOWN
# ==================

@app.on_event("startup")
async def startup_event():
    """Initialize database and load ML models on startup"""
    logger.info("🚀 Starting Personal Finance Intelligence API...")
    
    # Initialize database
    init_database()
    logger.info("✅ Database initialized")
    
    # Pre-load ML models (optional - loaded on first use)
    try:
        from ml import get_categorizer, get_anomaly_detector, get_insight_engine
        
        # This will load models into memory
        categorizer = get_categorizer()
        logger.info(f"✅ ML model loaded: {categorizer.get_model_info()['model_type']}")
        
        detector = get_anomaly_detector()
        logger.info("✅ Anomaly detector initialized")
        
        insight_engine = get_insight_engine()
        logger.info("✅ Insight engine initialized")
        
    except FileNotFoundError as e:
        logger.warning(f"⚠️  ML model not found: {e}")
        logger.warning("   Categorization will not be available until model is trained")
    except Exception as e:
        logger.error(f"❌ Error loading ML models: {e}")
    
    logger.info("🎉 API ready to accept requests")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("👋 Shutting down API...")

# ==================
# ROUTES
# ==================

# Include API routes
app.include_router(router, prefix="/api", tags=["API"])

# Health check endpoint
@app.get("/", tags=["Health"])
def root():
    """Root endpoint - health check"""
    return {
        "status": "healthy",
        "service": "Personal Finance Intelligence API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health", tags=["Health"])
def health_check():
    """Detailed health check"""
    from database import get_db_context, Transaction
    
    # Check database connection
    try:
        with get_db_context() as db:
            count = db.query(Transaction).count()
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    # Check ML model
    try:
        from ml import get_categorizer
        categorizer = get_categorizer()
        ml_status = "healthy"
        model_info = categorizer.get_model_info()
    except FileNotFoundError:
        ml_status = "model not found"
        model_info = None
    except Exception as e:
        ml_status = f"unhealthy: {str(e)}"
        model_info = None
    
    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "database": db_status,
        "ml_model": ml_status,
        "model_info": model_info
    }

# ==================
# MAIN (for development)
# ==================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )