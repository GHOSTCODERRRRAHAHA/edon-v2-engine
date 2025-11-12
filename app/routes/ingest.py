from __future__ import annotations
from typing import List, Dict, Any, Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field
from time import gmtime, strftime
import uuid

from app.state_bus import get_state, set_state, set_adapt
from app.recommend import recommend_for

router = APIRouter()

def _ts() -> str:
    return strftime("%Y-%m-%dT%H:%M:%SZ", gmtime())

# ---------- Models ----------

class Frame(BaseModel):
    ts: Optional[float] = None
    user_id: Optional[str] = None
    place_id: Optional[str] = None
    env: Optional[Dict[str, Any]] = None
    vision: Optional[Dict[str, Any]] = None
    audio: Optional[Dict[str, Any]] = None
    imu: Optional[Dict[str, Any]] = None

class IngestBatch(BaseModel):
    frames: List[Frame] = Field(default_factory=list)

# ---------- Route ----------

@router.post("/v1/ingest")
def ingest(batch: IngestBatch) -> Dict[str, Any]:
    frames = batch.frames
    if not frames:
        return {"ok": True, "frames": 0}

    co2_vals: List[float] = []
    dba_vals: List[float] = []
    first = frames[0]

    # --- capture previous state BEFORE updating the bus ---
    prev = get_state() or {}
    prev_state = prev.get("state")

    # gather averages
    for f in frames:
        env = f.env or {}
        if "co2" in env:
            try:
                co2_vals.append(float(env["co2"]))
            except Exception:
                pass
        if "dba" in env:
            try:
                dba_vals.append(float(env["dba"]))
            except Exception:
                pass

    co2 = sum(co2_vals) / len(co2_vals) if co2_vals else 600.0
    dba = sum(dba_vals) / len(dba_vals) if dba_vals else 40.0

    # simple environment drift heuristic (0..1)
    drift_env = max(0.0, (co2 - 700.0) / 600.0) * 0.6 + max(0.0, (dba - 45.0) / 20.0) * 0.4
    drift = round(min(1.0, max(0.0, drift_env)), 2)

    if drift > 0.6:
        state = "overload"
    elif drift > 0.35:
        state = "focus"
    else:
        state = "balanced"

    payload = {
        "schema": "1.0.0",
        "ts": _ts(),
        "state": state,
        "drift": drift,
        "confidence": 0.9,
        "user_id": first.user_id,
        "place_id": first.place_id,
        "env": first.env or {},
    }

    # --- Update state bus for WS ---
    set_state(payload)

    # --- Detect state crossings (use saved prev_state) ---
    entering_overload = (state == "overload" and prev_state != "overload")
    leaving_overload  = (state in ("balanced", "focus") and prev_state == "overload")

    if entering_overload or leaving_overload:
        try:
            env = payload.get("env") or {}
            recs = recommend_for(state, drift, env)
        except Exception as e:
            print("[ADAPT ERROR]", e)
            recs = []

        adapt_event = {
            "schema": "1.0.0",
            "ts": _ts(),
            "event_id": str(uuid.uuid4()),
            "type": "overload_start" if entering_overload else "overload_clear",
            "state": state,
            "drift": drift,
            "ttl_ms": 5000,
            "recommendations": recs,
            "user_id": first.user_id,
            "place_id": first.place_id,
        }

        set_adapt(adapt_event)
        print(f"[ADAPT CROSSING] {adapt_event['type']}  recs={len(recs)}")

    return {"ok": True, "frames": len(frames), **payload}
