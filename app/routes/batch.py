"""Batch CAV computation routes."""

import os
import time
import threading
from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException, Body
from app.models import BatchResponse, BatchResponseItem
from app.engine import CAVEngine, STRESS_LABEL
from app.utils.feature_ingest import looks_raw, featurize_raw, normalize_feature_map
from app import __version__
import logging
from time import gmtime, strftime

# Import state bus for updating latest state
try:
    from app.state_bus import set_state
except ImportError:
    set_state = None

router = APIRouter(prefix="/oem/cav/batch", tags=["Batch"])

# Keep existing router declaration (don't change the path clients depend on)
# router = APIRouter(prefix="/oem/cav/batch", tags=["Batch"])

ENGINE = CAVEngine(stress_label=STRESS_LABEL)  # ensure we're not re-creating this per request

EXPECTED = ["eda_mean", "eda_std", "bvp_mean", "bvp_std", "acc_mean", "acc_std"]

# Note: For batch processing, we use a shared engine instance
# The engine maintains EMA state, so we need thread safety for concurrent requests
# Using a lock to ensure thread-safe access to the engine
_engine_lock = threading.Lock()

LOGGER = logging.getLogger(__name__)
RELAXED_GUARD = os.getenv("EDON_RELAXED_GUARD", "0") == "1"


def _guard_features_when_needed(fmaps: List[Dict[str, Any]], any_raw: bool) -> None:
    """
    Only enforce the strict feature overlap guard when:
      - No raw windows were present, AND
      - EDON_STRICT_FEATURES is true (default)
    """
    if any_raw:
        return
    if os.getenv("EDON_STRICT_FEATURES", "true").lower() != "true":
        return
    
    keys = {k.lower() for k in fmaps[0].keys()} if fmaps else set()
    missing = [k for k in EXPECTED if k not in keys]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Feature schema mismatch: missing={missing}"
        )


@router.post("", response_model=BatchResponse)  # keep the same final URL (prefix + "")
async def cav_batch(req: Dict[str, List[Dict[str, Any]]]):
    """
    Accepts either:
      - RAW windows: {EDA,TEMP,BVP,ACC_x,ACC_y,ACC_z} (each 240 floats) + env fields
      - FEATURE maps: {eda_mean, eda_std, bvp_mean, bvp_std, acc_mean, acc_std} (+ optional env)
    
    RAW → featurize here → run feature pipeline
    FEATURE → normalize → run feature pipeline
    """
    start_time = time.time()
    
    windows = req.get("windows", [])
    if not isinstance(windows, list) or not windows:
        raise HTTPException(status_code=422, detail="windows must be a non-empty list")
    
    fmaps: List[Dict[str, float]] = []
    any_raw = False
    is_raw_list = []  # Track which windows are raw
    
    for w in windows:
        is_raw = looks_raw(w)
        is_raw_list.append(is_raw)
        if is_raw:
            any_raw = True
            fmaps.append(featurize_raw(w))          # compute 6 features from arrays
        else:
            fmaps.append(normalize_feature_map(w))  # normalize keys/casing for feature maps
    
    # Only enforce strict feature-guard if ALL windows were feature-maps
    _guard_features_when_needed(fmaps, any_raw)
    
    # Convert to vectors in engine's expected order
    X = [[float(f.get(k, 0.0)) for k in EXPECTED] for f in fmaps]
    
    # Run feature-based inference
    # Since ENGINE.cav_from_features_batch doesn't exist yet, we'll call cav_from_window
    # for each window. For feature maps, we need to reconstruct raw windows or use a different path.
    # For now, we'll process sequentially with the engine (which expects raw windows)
    results = []
    with _engine_lock:  # Thread-safe access to shared engine
        for idx, w in enumerate(windows):
            try:
                # If it was raw, use the original window; otherwise we need to handle feature maps
                if is_raw_list[idx]:
                    # Use original raw window
                    from app.utils.feature_ingest import normalize_to_engine_format
                    normalized_win = normalize_to_engine_format(w)
                    temp_c = w.get('temp_c') or w.get('TEMP_C')
                    humidity = w.get('humidity') or w.get('HUMIDITY')
                    aqi = w.get('aqi') or w.get('AQI') or w.get('air_quality')
                    local_hour = w.get('local_hour') or w.get('LOCAL_HOUR') or 12
                    
                    cav_raw, cav_smooth, state, parts = ENGINE.cav_from_window(
                        normalized_win,
                        temp_c=temp_c,
                        humidity=humidity,
                        aqi=aqi,
                        local_hour=local_hour
                    )
                else:
                    # Feature map - compute overlap against expected engine schema if available
                    try:
                        # Build a faux raw window dict to compute features using engine for overlap
                        if hasattr(ENGINE, "feature_names"):
                            expected = list(ENGINE.feature_names)
                            # Normalize feature-map keys
                            keys = {k.lower() for k in w.keys()}
                            overlap = [k for k in expected if k.lower() in keys]
                            ratio = (len(overlap) / max(1, len(expected)))
                            if ratio < 0.8:
                                if not RELAXED_GUARD:
                                    raise HTTPException(
                                        status_code=400,
                                        detail=f"Feature mismatch: overlap {ratio:.2%} < 80%"
                                    )
                                else:
                                    LOGGER.warning("Relaxed guard: feature overlap=%s", f"{ratio:.2%}")
                                    results.append(BatchResponseItem(ok=False, error=f"Schema mismatch (relaxed): overlap {ratio:.1%}"))
                                    continue
                    except HTTPException:
                        raise
                    # Engine currently requires raw windows for full inference
                    raise ValueError("Feature map inference not yet supported - engine requires raw windows")
                
                results.append(BatchResponseItem(
                    ok=True,
                    cav_raw=cav_raw,
                    cav_smooth=cav_smooth,
                    state=state,
                    parts=parts
                ))
            except Exception as e:
                results.append(BatchResponseItem(
                    ok=False,
                    error=str(e)
                ))
    
    # Update state bus with the last successful window's result
    # This ensures _debug/state reflects the latest processed state
    if set_state and results:
        # Find the last successful result (ok=True)
        last_success = None
        for result in reversed(results):
            if result.ok and result.state and result.cav_smooth is not None:
                last_success = result
                break
        
        if last_success:
            try:
                # Build state payload similar to ingest endpoint format
                state_payload = {
                    "schema": "1.0.0",
                    "ts": strftime("%Y-%m-%dT%H:%M:%SZ", gmtime()),
                    "state": last_success.state,
                    "cav_smooth": last_success.cav_smooth,
                    "cav_raw": last_success.cav_raw,
                    "confidence": 0.9,  # Default confidence for batch processing
                    "parts": last_success.parts or {},
                }
                set_state(state_payload)
            except Exception as e:
                # Don't fail the batch request if state update fails
                LOGGER.warning(f"Failed to update state bus: {e}")
    
    latency_ms = (time.time() - start_time) * 1000.0
    
    return BatchResponse(
        results=results,
        latency_ms=latency_ms,
        server_version=f"EDON CAV Engine v{__version__}"
    )

