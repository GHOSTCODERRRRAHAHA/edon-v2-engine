"""FastAPI microservice for EDON CAV."""

import os
import json
import sys
import random
from typing import List, Dict, Optional

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, conint, confloat

load_dotenv()

# Ensure repository root is on sys.path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Local imports (after path fix)
from src.embedding import CAVEmbedder, cosine_similarity  # noqa: E402

app = FastAPI(
    title="EDON CAV API",
    description="Context-Aware Vectors microservice for generating and querying 128-D embeddings",
    version="0.1.1",
)

# -----------------------
# Global state
# -----------------------
embedder: Optional[CAVEmbedder] = None
cav_data: List[Dict] = []
cav_embeddings: Optional[np.ndarray] = None  # L2-normalized Nx128 matrix


# -----------------------
# Pydantic models
# -----------------------
class BioFeatures(BaseModel):
    hr: confloat(ge=0, le=240) = Field(..., description="Heart rate in BPM")
    hrv_rmssd: confloat(ge=0) = Field(..., description="HRV RMSSD in ms")
    eda_mean: float = Field(..., description="EDA mean in μS")
    eda_var: confloat(ge=0) = Field(..., description="EDA variance")
    resp_bpm: confloat(ge=0, le=80) = Field(..., description="Respiration rate in BPM")
    accel_mag: confloat(ge=0) = Field(..., description="Accelerometer magnitude in g")


class EnvFeatures(BaseModel):
    temp_c: confloat(ge=-40, le=60) = Field(..., description="Temperature in Celsius")
    humidity: conint(ge=0, le=100) = Field(..., description="Humidity percentage [0-100]")
    cloud: conint(ge=0, le=100) = Field(..., description="Cloud coverage [0-100]")
    aqi: conint(ge=0, le=500) = Field(..., description="Air Quality Index")
    pm25: confloat(ge=0) = Field(..., description="PM2.5 concentration")
    ozone: confloat(ge=0) = Field(..., description="Ozone concentration")
    hour: conint(ge=0, le=23) = Field(..., description="Hour of day [0-23]")
    is_daylight: conint(ge=0, le=1) = Field(..., description="Daylight flag [0 or 1]")


class GenerateCAVRequest(BaseModel):
    bio: BioFeatures
    env: EnvFeatures


class GenerateCAVResponse(BaseModel):
    cav128: List[float] = Field(..., description="128-dimensional CAV embedding (L2-normalized)")


class SimilarRequest(BaseModel):
    cav128: List[float] = Field(..., description="128-dimensional query vector (will be L2-normalized)")
    k: conint(ge=1, le=100) = Field(5, description="Number of nearest neighbors")


class SimilarHit(BaseModel):
    similarity: float
    record: Dict


class SimilarResponse(BaseModel):
    results: List[SimilarHit] = Field(..., description="Top-k similar records with similarity scores")


# -----------------------
# Utilities
# -----------------------
def _l2_normalize(X: np.ndarray, axis: int = 1, eps: float = 1e-12) -> np.ndarray:
    norms = np.linalg.norm(X, axis=axis, keepdims=True)
    norms = np.maximum(norms, eps)
    return X / norms


# -----------------------
# Startup
# -----------------------
@app.on_event("startup")
async def startup_event():
    """Load models and dataset on startup."""
    global embedder, cav_data, cav_embeddings

    # Model directory discovery
    model_dir = os.getenv("EDON_MODEL_DIR") or os.getenv("MODEL_DIR") or os.path.join(ROOT, "models")
    try:
        embedder = CAVEmbedder(n_components=128, model_dir=model_dir)
        embedder.load()
        print(f"✓ Loaded embedding models from: {model_dir}")
    except FileNotFoundError:
        print(f"⚠ Warning: Models not found in {model_dir}. Run your build script to create them.")
        embedder = None

    # Data path discovery
    data_path = os.getenv("CAV_DATA_PATH") or os.path.join(ROOT, "data", "edon_cav.json")
    if os.path.exists(data_path):
        try:
            with open(data_path, "r", encoding="utf-8") as f:
                cav_data = json.load(f)

            # Expect each record to contain "cav128"
            vecs = [rec.get("cav128") for rec in cav_data if isinstance(rec.get("cav128"), list)]
            if len(vecs) == 0:
                raise ValueError("No 'cav128' vectors found in dataset.")

            cav_embeddings = np.array(vecs, dtype=np.float32)
            if cav_embeddings.ndim != 2 or cav_embeddings.shape[1] != 128:
                raise ValueError(f"Bad shape for embeddings: {cav_embeddings.shape} (expected Nx128)")

            # L2-normalize for cosine via dot product
            cav_embeddings = _l2_normalize(cav_embeddings, axis=1)
            print(f"✓ Loaded {len(cav_embeddings)} CAV records from: {data_path}")
        except Exception as e:
            print(f"⚠ Warning: Failed to load CAV data from {data_path}: {e}")
            cav_data = []
            cav_embeddings = None
    else:
        print(f"⚠ Warning: CAV data not found at {data_path}. Similarity search will be unavailable.")
        cav_data = []
        cav_embeddings = None


# -----------------------
# Debug / Health
# -----------------------
@app.get("/_debug/state")
def debug_state():
    """Lightweight debug state so the UI can poll without 404s."""
    model_dir = os.getenv("EDON_MODEL_DIR") or os.getenv("MODEL_DIR") or os.path.join(ROOT, "models")
    data_path = os.getenv("CAV_DATA_PATH") or os.path.join(ROOT, "data", "edon_cav.json")
    return {
        "ok": True,
        "models": {
            "dir": model_dir,
            "loaded": embedder is not None,
        },
        "data": {
            "path": data_path,
            "loaded": bool(cav_embeddings is not None and len(cav_data) > 0),
            "count": len(cav_data),
        },
        "version": app.version,
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "embedder_loaded": embedder is not None,
        "data_loaded": bool(cav_embeddings is not None and len(cav_data) > 0),
        "data_count": len(cav_data),
        "version": app.version,
    }


# -----------------------
# Routes
# -----------------------
@app.get("/")
async def root():
    return {
        "service": "EDON CAV API",
        "version": app.version,
        "endpoints": {
            "POST /generate_cav": "Generate 128-D embedding from features",
            "POST /similar": "Find similar CAV vectors",
            "GET /sample": "Get random sample records",
            "GET /_debug/state": "Debug status (polled by UI)",
            "GET /health": "Liveness / readiness probe",
        },
    }


@app.post("/generate_cav", response_model=GenerateCAVResponse)
async def generate_cav(request: GenerateCAVRequest):
    """
    Generate a 128-dimensional CAV embedding from physiological and environmental features.
    Returns an L2-normalized embedding vector suitable for cosine similarity.
    """
    if embedder is None:
        raise HTTPException(status_code=503, detail="Embedding model not loaded. Build or load models first.")

    row = {
        "hr": request.bio.hr,
        "hrv_rmssd": request.bio.hrv_rmssd,
        "eda_mean": request.bio.eda_mean,
        "eda_var": request.bio.eda_var,
        "resp_bpm": request.bio.resp_bpm,
        "accel_mag": request.bio.accel_mag,
        "temp_c": request.env.temp_c,
        "humidity": request.env.humidity,
        "cloud": request.env.cloud,
        "aqi": request.env.aqi,
        "pm25": request.env.pm25,
        "ozone": request.env.ozone,
        "hour": request.env.hour,
        "is_daylight": request.env.is_daylight,
    }
    feature_df = pd.DataFrame([row])

    vec = embedder.transform(feature_df)[0]
    vec = np.asarray(vec, dtype=np.float32)
    vec = _l2_normalize(vec[None, :], axis=1)[0]  # ensure normalized

    return GenerateCAVResponse(cav128=vec.tolist())


@app.post("/similar", response_model=SimilarResponse)
async def find_similar(request: SimilarRequest):
    """
    Find the top-k most similar CAV vectors using cosine similarity.
    """
    if cav_embeddings is None or len(cav_data) == 0:
        raise HTTPException(status_code=503, detail="CAV data not loaded. Build dataset first.")

    if len(request.cav128) != 128:
        raise HTTPException(status_code=400, detail=f"Expected 128-dimensional vector, got {len(request.cav128)}")

    query_vec = np.asarray(request.cav128, dtype=np.float32)
    query_vec = _l2_normalize(query_vec[None, :], axis=1)[0]

    # Cosine similarity = dot product when both sides are L2-normalized
    sims = cav_embeddings @ query_vec

    top_idx = np.argsort(sims)[::-1][: request.k]
    results: List[SimilarHit] = []
    for idx in top_idx:
        results.append(SimilarHit(similarity=float(sims[idx]), record=cav_data[idx]))

    return SimilarResponse(results=results)


@app.get("/sample")
async def get_sample(n: int = Query(5, ge=1, le=100)):
    """
    Get random sample records from the CAV dataset.
    """
    if len(cav_data) == 0:
        raise HTTPException(status_code=503, detail="CAV data not loaded. Build dataset first.")

    n = min(n, len(cav_data))
    return {"samples": random.sample(cav_data, n), "total": len(cav_data)}


# -----------------------
# Entrypoint
# -----------------------
if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run("api.main:app", host="0.0.0.0", port=port, reload=bool(os.getenv("RELOAD", "1") == "1"))
