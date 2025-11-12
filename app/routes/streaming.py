from __future__ import annotations
import asyncio, json, time, uuid
from typing import Any, Dict, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

#  Prefer in-process bus (updated by /v1/ingest), fallback to edge bridge
try:
    from app.state_bus import get_state as sb_get_state, get_adapt as sb_get_adapt
except Exception:
    sb_get_state = sb_get_adapt = None  # type: ignore

try:
    from app.edge_bridge import get_latest_state as edge_get_state, get_latest_adapt as edge_get_adapt
except Exception:
    edge_get_state = edge_get_adapt = None  # type: ignore

router = APIRouter()
SCHEMA = "1.0.0"
DEFAULT_HZ = 5.0

def _ts_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

async def _tick(ws: WebSocket, kind: str = "state") -> None:
    await ws.accept()
    period = 1.0 / DEFAULT_HZ
    try:
        while True:
            now_iso = _ts_iso()

            if kind == "state":
                # Heartbeat baseline
                payload: Dict[str, Any] = {
                    "schema": SCHEMA,
                    "ts": now_iso,
                    "state": "balanced",
                    "drift": 0.0,
                    "confidence": 0.0,
                }
                latest = None
                if callable(sb_get_state):
                    try:
                        latest = sb_get_state()
                    except Exception:
                        latest = None
                if not latest and callable(edge_get_state):
                    try:
                        latest = edge_get_state()
                    except Exception:
                        latest = None
                if isinstance(latest, dict) and latest:
                    payload.update({k: latest[k] for k in ("state","drift","confidence","user_id","place_id") if k in latest})

                await ws.send_text(json.dumps(payload))

            else:  # kind == "adapt"
                # Heartbeat baseline (empty recs)
                heartbeat: Dict[str, Any] = {
                    "schema": SCHEMA,
                    "ts": now_iso,
                    "event_id": str(uuid.uuid4()),
                    "ttl_ms": 1500,
                    "recommendations": [],
                }

                # Prefer in-process adapt evt
                adapt_evt: Optional[Dict[str, Any]] = None
                if callable(sb_get_adapt):
                    try:
                        adapt_evt = sb_get_adapt()
                    except Exception:
                        adapt_evt = None

                # Fallback to edge only if bus has nothing/empty
                if not (isinstance(adapt_evt, dict) and isinstance(adapt_evt.get("recommendations"), list) and len(adapt_evt["recommendations"]) > 0):
                    if callable(edge_get_adapt):
                        try:
                            adapt_evt = edge_get_adapt()
                        except Exception:
                            adapt_evt = None

                # If we have non-empty recs, SEND THEM and SKIP heartbeat
                if isinstance(adapt_evt, dict) and isinstance(adapt_evt.get("recommendations"), list) and len(adapt_evt["recommendations"]) > 0:
                    out = dict(adapt_evt)
                    out.setdefault("schema", SCHEMA)
                    out.setdefault("ts", now_iso)
                    out.setdefault("event_id", str(uuid.uuid4()))
                    out.setdefault("ttl_ms", adapt_evt.get("ttl_ms", 1500))
                    await ws.send_text(json.dumps(out))
                    await asyncio.sleep(period)
                    continue  #  critical: do NOT send the empty heartbeat too

                # Otherwise, send heartbeat
                await ws.send_text(json.dumps(heartbeat))

            await asyncio.sleep(period)
    except WebSocketDisconnect:
        return

@router.websocket("/v1/state/live/ws")
async def state_live_ws(ws: WebSocket):
    await _tick(ws, "state")

@router.websocket("/v1/adapt/events/ws")
async def adapt_events_ws(ws: WebSocket):
    await _tick(ws, "adapt")
@router.get("/_debug/adapt")
def debug_adapt():
    try:
        from app.state_bus import get_adapt
        return {"last_adapt": get_adapt()}
    except Exception:
        return {"last_adapt": None}
