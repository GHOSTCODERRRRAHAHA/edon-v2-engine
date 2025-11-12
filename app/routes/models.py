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
    models_dir = None
    for base in [Path("."), Path(__file__).parent.parent.parent]:
        candidate = base / "models"
        if candidate.exists():
            models_dir = candidate
            break
    
    if models_dir is None:
        models_dir = Path("models")  # Fallback
    
    hashes = models_dir / "HASHES.txt"
    if hashes.exists():
        try:
            # Expect lines like: "cav_engine_v3_2.pkl  d2a40645..."
            line = hashes.read_text().splitlines()[0].strip()
            parts = line.split()
            if len(parts) >= 2:
                info["name"] = Path(parts[0]).stem
                info["sha256"] = parts[-1]
        except Exception:
            pass
    else:
        for ext in (".pkl", ".bin", ".onnx", ".pt", ".joblib"):
            for f in models_dir.glob(f"*{ext}"):
                info["name"] = f.stem
                info["sha256"] = _sha256_file(f)
                break

    return info


@router.get("/info")
def models_info():
    return _discover_model()

