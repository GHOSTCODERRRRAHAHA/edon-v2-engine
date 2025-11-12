"""Telemetry and health check routes."""

import time
from fastapi import APIRouter
from app.models import HealthResponse, TelemetryResponse
from app import __version__
from app.routes.models import _discover_model

router = APIRouter(tags=["System"])

# Telemetry state (in-memory, resets on restart)
_start_time = time.time()
_request_count = 0
_latency_sum = 0.0


def record_request(latency_ms: float):
    """Record a request for telemetry."""
    global _request_count, _latency_sum
    _request_count += 1
    _latency_sum += latency_ms


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """
    Health check endpoint.
    
    Returns:
        HealthResponse with service status and model identifier
    """
    model_data = _discover_model()
    model_info = f"{model_data['name']} sha256={model_data['sha256'][:16]}... features={model_data['features']} window={model_data['window']}Hz*{model_data['sample_rate_hz']} pca={model_data['pca_dim']}"
    
    return HealthResponse(
        ok=True,
        model=model_info
    )


@router.get("/telemetry", response_model=TelemetryResponse)
async def telemetry() -> TelemetryResponse:
    """
    Telemetry endpoint with request statistics.
    
    Returns:
        TelemetryResponse with request count, average latency, and uptime
    """
    uptime_seconds = time.time() - _start_time
    avg_latency_ms = _latency_sum / _request_count if _request_count > 0 else 0.0
    
    return TelemetryResponse(
        request_count=_request_count,
        avg_latency_ms=avg_latency_ms,
        uptime_seconds=uptime_seconds
    )




