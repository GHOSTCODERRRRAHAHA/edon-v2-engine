# app/routes/models.py

from fastapi import APIRouter
from pathlib import Path
import hashlib

router = APIRouter()


def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _discover_model() -> dict:
    info = {
        "name": "cav_engine",
        "features": 6,
        "window": 240,
        "sample_rate_hz": 4,
        "pca_dim": 128,
        "sha256": "unknown",
        "classes": [0, 1, 2, 3],
    }

    # Try multiple possible locations for models directory
    base_paths = [Path("."), Path(__file__).parent.parent.parent]
    
    # PRIORITY 1: Check for cav_engine_v3_2_* directories (production model)
    for base in base_paths:
        for v32_dir in base.glob("cav_engine_v3_2_*"):
            if v32_dir.is_dir():
                # Look for cav_state_v3_2.joblib (production model)
                model_file = v32_dir / "cav_state_v3_2.joblib"
                if model_file.exists():
                    info["name"] = "cav_state_v3_2"
                    info["sha256"] = _sha256_file(model_file)
                    return info
    
    # PRIORITY 2: Check models directory for v3.2 models
    models_dir = None
    for base in base_paths:
        candidate = base / "models"
        if candidate.exists():
            models_dir = candidate
            break
    
    if models_dir is None:
        models_dir = Path("models")  # Fallback
    
    # Check for v3.2 model files in subdirectories
    for subdir in models_dir.iterdir():
        if subdir.is_dir() and "v3_2" in subdir.name.lower():
            for ext in (".joblib", ".pkl"):
                for f in subdir.glob(f"cav_state_v3_2{ext}"):
                    info["name"] = "cav_state_v3_2"
                    info["sha256"] = _sha256_file(f)
                    return info
    
    # PRIORITY 3: Check for HASHES.txt in subdirectories (newer models)
    hashes_found = False
    for subdir in models_dir.iterdir():
        if subdir.is_dir():
            hashes = subdir / "HASHES.txt"
            if hashes.exists():
                try:
                    line = hashes.read_text().splitlines()[0].strip()
                    if line and not line.startswith("#"):
                        parts = line.split()
                        if len(parts) >= 2:
                            info["name"] = Path(parts[0]).stem
                            info["sha256"] = parts[-1]
                            hashes_found = True
                            break
                except Exception:
                    pass
    
    # PRIORITY 4: Check root models directory HASHES.txt
    if not hashes_found:
        hashes = models_dir / "HASHES.txt"
        if hashes.exists():
            try:
                line = hashes.read_text().splitlines()[0].strip()
                if line and not line.startswith("#"):
                    parts = line.split()
                    if len(parts) >= 2:
                        info["name"] = Path(parts[0]).stem
                        info["sha256"] = parts[-1]
                        hashes_found = True
            except Exception:
                pass
    
    # PRIORITY 5: Fallback - find any model files (but skip cav_embedder if possible)
    if not hashes_found:
        # Check subdirectories first
        for subdir in models_dir.iterdir():
            if subdir.is_dir():
                for ext in (".pkl", ".bin", ".onnx", ".pt", ".joblib"):
                    for f in subdir.glob(f"*{ext}"):
                        if "embedder" not in f.stem.lower():  # Prefer non-embedder models
                            info["name"] = f.stem
                            info["sha256"] = _sha256_file(f)
                            hashes_found = True
                            break
                if hashes_found:
                    break
        
        # Check root models directory (last resort)
        if not hashes_found:
            for ext in (".pkl", ".bin", ".onnx", ".pt", ".joblib"):
                for f in models_dir.glob(f"*{ext}"):
                    info["name"] = f.stem
                    info["sha256"] = _sha256_file(f)
                    break

    return info


@router.get("/info")
def models_info():
    return _discover_model()

