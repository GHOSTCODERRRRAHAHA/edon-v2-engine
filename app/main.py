"""EDON CAV Engine - Main FastAPI application."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import time
import os
from pathlib import Path
from app import __version__
from app.routes import batch, telemetry, memory, dashboard, metrics
from app.routes.streaming import router as streaming_router
from app.routes.ingest import router as ingest_router
from app.routes.models import router as models_router

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass  # python-dotenv not installed, skip  


app = FastAPI(
    title="EDON CAV Engine",
    description="Context-Aware Vector scoring API for OEM partners",
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware for OEM integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(batch.router)
app.include_router(telemetry.router)
app.include_router(metrics.router)
app.include_router(memory.router)
app.include_router(streaming_router)
app.include_router(ingest_router)
from app.routes import debug_state
app.include_router(debug_state.router)
app.include_router(models_router, prefix="/models", tags=["models"])


# Mount dashboard
# Note: Dash integration requires WSGI-to-ASGI adapter
# For now, we'll serve it on a separate port or use a simpler approach
# The dashboard route is defined in dashboard.py
try:
    from app.routes.dashboard import get_dash_app
    dash_app = get_dash_app()
    
    # Mount Dash app using ASGI adapter
    from starlette.middleware.wsgi import WSGIMiddleware
    app.mount("/dashboard", WSGIMiddleware(dash_app.server))
except Exception as e:
    # Dashboard is optional - log error but don't fail
    import logging
    logging.warning(f"Dashboard not available: {e}")


@app.middleware("http")
async def track_latency(request: Request, call_next):
    """Middleware to track request latency for telemetry."""
    from app.routes import telemetry
    
    start_time = time.time()
    response = await call_next(request)
    latency_ms = (time.time() - start_time) * 1000.0
    
    # Record latency for telemetry (only for CAV endpoints)
    if request.url.path.startswith("/oem"):
        telemetry.record_request(latency_ms)
    
    return response


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "EDON CAV Engine",
        "version": __version__,
        "endpoints": {
            "batch": "POST /oem/cav/batch",
            "health": "GET /health",
            "telemetry": "GET /telemetry",
            "memory_summary": "GET /memory/summary",
            "memory_clear": "POST /memory/clear",
            "dashboard": "GET /dashboard",
            "models_info": "GET /models/info",
            "docs": "/docs"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

