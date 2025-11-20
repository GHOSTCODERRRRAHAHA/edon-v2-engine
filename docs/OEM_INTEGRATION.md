# EDON OEM Integration Guide

**Version**: v1.0  
**Last Updated**: 2025-11-20

Complete guide for integrating EDON CAV Engine into robotics systems.

---

## What EDON Does

EDON is an **adaptive state engine** for physical AI (humanoids, wearables, smart environments). 

**Input**: A 4-second sensor window (240 samples) of physiological and environmental data  
**Output**: 
- **State**: `restorative`, `balanced`, `focus`, or `overload`
- **p_stress**: Probability of stress [0.0-1.0]
- **Control scales**: Recommended speed, torque, and safety margins for robot behavior

**Use Case**: Adapt robot behavior in real-time based on operator/occupant physiological state.

---

## Integration Modes

### 1. REST API

**Best for**: HTTP-based architectures, web applications, simple integrations

```python
from edon import EdonClient, TransportType

client = EdonClient(
    base_url="http://localhost:8001",
    transport=TransportType.REST
)

window = build_window_from_robot_sensors()
result = client.cav(window)

print(f"State: {result['state']}")
print(f"P-Stress: {result['parts']['p_stress']:.3f}")
```

### 2. gRPC

**Best for**: High-performance applications, real-time streaming, robotics systems

```python
from edon import EdonClient, TransportType

client = EdonClient(
    transport=TransportType.GRPC,
    grpc_host="localhost",
    grpc_port=50051
)

window = build_window_from_robot_sensors()
result = client.cav(window)

# Includes control scales
print(f"Speed: {result['controls']['speed']:.2f}")
print(f"Torque: {result['controls']['torque']:.2f}")
print(f"Safety: {result['controls']['safety']:.2f}")

client.close()
```

### 3. Python SDK

**Installation**:
```bash
pip install -e sdk/python
# Or with gRPC support:
pip install -e "sdk/python[grpc]"
```

**Usage**: See examples above.

### 4. C++ SDK (Coming Soon)

For C++/ROS2 integrations. See `sdk/cpp/README.md`.

---

## Minimal Integration Loop

Here's the core integration pattern for a robotics control loop:

```python
from edon import EdonClient

# Initialize client
client = EdonClient()  # Uses EDON_BASE_URL env var or default

while True:
    # 1. Collect sensor data (4 seconds = 240 samples @ 60Hz)
    window = build_window_from_robot_sensors()
    
    # 2. Get EDON state
    result = client.cav(window)
    state = result['state']
    p_stress = result['parts']['p_stress']
    
    # 3. Map state to control scales
    if state == "restorative":
        speed_scale, torque_scale, safety_scale = 0.7, 0.7, 0.95
    elif state == "balanced":
        speed_scale, torque_scale, safety_scale = 1.0, 1.0, 0.85
    elif state == "focus":
        speed_scale, torque_scale, safety_scale = 1.2, 1.1, 0.8
    elif state == "overload":
        speed_scale, torque_scale, safety_scale = 0.4, 0.4, 1.0
    
    # 4. Apply scales to robot controllers
    apply_scales_to_controllers(speed_scale, torque_scale, safety_scale)
    
    # 5. Wait for next window (4 seconds)
    time.sleep(4.0)
```

---

## Robot Example Output

Here's what a typical integration looks like in practice:

```
[STEP 00] stress_mode=False
  EDON → state=restorative | cav=9996 | p_stress=0.001
  Controls → speed=0.70 | torque=0.70 | safety=0.95
------------------------------------------------------------
[STEP 01] stress_mode=False
  EDON → state=restorative | cav=9995 | p_stress=0.001
  Controls → speed=0.70 | torque=0.70 | safety=0.95
------------------------------------------------------------
...
[STEP 20] stress_mode=True
  EDON → state=overload | cav=1200 | p_stress=0.932
  Controls → speed=0.40 | torque=0.40 | safety=1.00
------------------------------------------------------------
[STEP 21] stress_mode=True
  EDON → state=overload | cav=1150 | p_stress=0.945
  Controls → speed=0.40 | torque=0.40 | safety=1.00
------------------------------------------------------------
```

**Key Observations**:
- **Steps 0-19**: Low stress (`p_stress < 0.2`) → `restorative` state → Lower speed/torque, higher safety
- **Steps 20-39**: High stress (`p_stress > 0.8`) → `overload` state → Minimal speed/torque, maximum safety

This demonstrates how EDON adapts robot behavior based on physiological state.

---

## Sensor Window Format

Each window must contain exactly **240 samples** per signal (4 seconds @ 60Hz):

```python
window = {
    "EDA": [0.1, 0.12, ...],      # 240 floats - Electrodermal activity
    "TEMP": [36.5, 36.5, ...],    # 240 floats - Temperature
    "BVP": [0.5, 0.52, ...],      # 240 floats - Blood volume pulse
    "ACC_x": [0.0, 0.01, ...],    # 240 floats - Accelerometer X
    "ACC_y": [0.0, -0.01, ...],   # 240 floats - Accelerometer Y
    "ACC_z": [1.0, 1.0, ...],     # 240 floats - Accelerometer Z
    "temp_c": 22.0,               # float - Ambient temperature (°C)
    "humidity": 50.0,             # float - Relative humidity (%)
    "aqi": 35,                    # int - Air Quality Index
    "local_hour": 14              # int - Local hour [0-23]
}
```

---

## State Classification

EDON returns one of four states based on `p_stress`, `env`, and `circadian` scores:

| State | Conditions | Description | Typical Control Response |
|-------|------------|-------------|--------------------------|
| `restorative` | `p_stress < 0.2` | Very low stress, optimal recovery | Lower speed/torque, higher safety |
| `focus` | `0.2 ≤ p_stress ≤ 0.5` AND `env ≥ 0.8` AND `circadian ≥ 0.9` | Moderate stress with strong alignment | Higher speed/torque, optimized performance |
| `balanced` | `0.2 ≤ p_stress < 0.8` (when focus conditions not met) | Normal operation, moderate stress | Normal speed/torque, moderate safety |
| `overload` | `p_stress ≥ 0.8` | High stress, needs intervention | Minimal speed/torque, maximum safety |

**State Mapping Logic** (v1.1.0):
- **Overload** is checked first - high stress (`p_stress ≥ 0.8`) always triggers overload
- **Restorative** is for very low stress (`p_stress < 0.2`)
- **Focus** requires moderate stress (0.2-0.5) combined with excellent environment (`env ≥ 0.8`) and circadian alignment (`circadian ≥ 0.9`)
- **Balanced** is the default for moderate stress when focus conditions aren't met

See [`MODEL_CARD.md`](../MODEL_CARD.md) for detailed state mapping explanation.

---

## Deployment

### Docker (Recommended)

**One-command deployment**:

```bash
git clone <repo>
cd edon-cav-engine
docker compose up --build
```

**Access**:
- REST API: `http://localhost:8001/oem/cav/batch`
- gRPC: `localhost:50051`

### Manual Installation

```bash
pip install -r requirements.txt
pip install -e sdk/python

# Start REST API
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001

# Start gRPC (separate terminal)
python integrations/grpc/edon_grpc_service/server.py --port 50051
```

---

## Complete Example

See `clients/robot_example.py` for a complete working example:

```bash
# REST transport
python clients/robot_example.py --transport rest --steps 40

# gRPC transport
python clients/robot_example.py --transport grpc --steps 40
```

---

## Performance

On a single CPU core (Ryzen 7 3700X):
- **Throughput**: ~50-100 windows/sec (REST)
- **Latency**: ~10-20ms median (p50), ~30-50ms p99
- **gRPC**: Similar performance, slightly lower overhead

Run benchmarks:
```bash
python tests/latency_benchmark.py --n 1000
python tests/load_test_grpc.py --n 1000
```

---

## Security

### Authentication

Set environment variables:
```bash
export EDON_AUTH_ENABLED=true
export EDON_API_TOKEN=your-secret-token
```

Include in requests:
```python
client = EdonClient(
    base_url="http://localhost:8001",
    api_key="your-secret-token"
)
```

### Health Monitoring

Check service health:
```python
health = client.health()
print(health)  # {"ok": true, "model": "...", "uptime_s": ...}
```

Or via HTTP:
```bash
curl http://localhost:8001/health
```

---

## API Contract

See `docs/OEM_API_CONTRACT.md` for:
- Exact request/response schemas
- Error codes
- Versioning policy
- Breaking change policy

**v1 is FROZEN** - breaking changes will result in v2.

---

## Support

For integration questions or issues:
- API Contract: `docs/OEM_API_CONTRACT.md`
- Examples: `clients/robot_example.py`
- SDK Docs: `sdk/python/README.md`

---

**Version**: v1.0  
**Last Updated**: 2025-11-20
