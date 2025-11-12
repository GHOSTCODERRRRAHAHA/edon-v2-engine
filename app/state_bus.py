# app/state_bus.py
from __future__ import annotations
from typing import Optional, Dict, Any
import threading, time

_STATE_LOCK = threading.Lock()
_latest_state: Optional[Dict[str, Any]] = None
_latest_adapt: Optional[Dict[str, Any]] = None

def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def set_state(d: Dict[str, Any]) -> None:
    global _latest_state
    with _STATE_LOCK:
        _latest_state = dict(d)
        _latest_state.setdefault("ts", _now_iso())

def get_state() -> Optional[Dict[str, Any]]:
    with _STATE_LOCK:
        return dict(_latest_state) if _latest_state else None

def set_adapt(d: Dict[str, Any]) -> None:
    global _latest_adapt
    with _STATE_LOCK:
        _latest_adapt = dict(d)
        _latest_adapt.setdefault("ts", _now_iso())

def get_adapt() -> Optional[Dict[str, Any]]:
    with _STATE_LOCK:
        return dict(_latest_adapt) if _latest_adapt else None
