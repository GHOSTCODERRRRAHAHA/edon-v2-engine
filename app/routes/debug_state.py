# app/routes/debug_state.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/_debug/state")
def debug_state():
    """
    Returns the most recent engine state (including 'mode') for watchers or hardware bridges.
    Safe to call even if no state exists yet.
    """
    try:
        # Try unified state bus first
        from app.state_bus import get_state
        st = get_state() or {}
    except Exception:
        st = {}

    mode = None
    if "mode" in st:
        mode = st["mode"]
    elif "last_state" in st and isinstance(st["last_state"], dict):
        mode = st["last_state"].get("mode")

    return {
        "ok": True,
        "mode": mode,
        "last_state": st.get("last_state", {}),
        "state": st,
    }


# --- setters for testing (ADD THIS BELOW THE FIRST ROUTE) ---
try:
    from app.state_bus import get_state, set_state  # if you have a state bus
except Exception:
    get_state = None
    set_state = None

@router.post("/_debug/set_mode")
def debug_set_mode(mode: str):
    """
    Force the current mode (for hardware tests).
    Example: POST /_debug/set_mode?mode=focus
    """
    st = {}
    if get_state:
        st = get_state() or {}
    st["mode"] = mode
    if set_state:
        set_state(st)
    return {"ok": True, "mode": mode}
