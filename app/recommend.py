from typing import Dict, List
def recommend_for(state: str, drift: float, env: Dict) -> List[Dict]:
    recs: List[Dict] = []
    co2 = float(env.get("co2", 600) or 600)
    dba = float(env.get("dba", 40) or 40)
    lux = float(env.get("lux", 300) or 300)
    if state == "overload":
        if co2 >= 900:
            recs.append({"priority": 1, "action": "ventilation_increase", "reason": f"CO2={int(co2)}ppm", "ttl_ms": 30000})
        if dba >= 55:
            recs.append({"priority": 1, "action": "reduce_noise", "reason": f"dBA≈{int(dba)}", "ttl_ms": 20000})
        if lux >= 500:
            recs.append({"priority": 2, "action": "dim_lights", "reason": f"Lux≈{int(lux)}", "ttl_ms": 20000})
        recs.append({"priority": 3, "action": "suggest_break", "reason": "high cognitive load", "ttl_ms": 60000})
    elif state == "focus":
        if 45 <= dba <= 55:
            recs.append({"priority": 3, "action": "keep_noise_stable", "reason": "good speech-band noise", "ttl_ms": 20000})
        if 250 <= lux <= 450:
            recs.append({"priority": 3, "action": "keep_lighting", "reason": "comfortable lighting", "ttl_ms": 20000})
        recs.append({"priority": 4, "action": "maintain_conditions", "reason": "stable focus", "ttl_ms": 15000})
    else:  # balanced/restorative
        recs.append({"priority": 4, "action": "maintain_conditions", "reason": "good state", "ttl_ms": 15000})
    recs.sort(key=lambda r: r["priority"])
    return recs
