# EDON OEM Onboarding Guide (v1)

Welcome to EDON. This guide shows OEMs and robotics partners how to integrate the EDON CAV Engine into their systems using Docker, REST, gRPC, and the Python / C++ SDKs.

---

## 1. What EDON does

EDON is a **Context-Aware Vector (CAV) engine** for physical AI:

- **Ingests**:
  - Physiological signals (e.g., EDA, BVP, accelerometer-derived features)
  - Environmental signals (e.g., temperature, humidity, AQI, local time)

- **Outputs**:
  - A normalized **CAV score** (`cav_raw`, `cav_smooth`)
  - A **state**: `restorative`, `balanced`, `focus`, or `overload` (depending on model)
  - Components: `bio`, `env`, `circadian`, `p_stress` (probability of stress)

OEMs use this to **modulate robot behavior** or **safety limits** in real time.

---

## 2. Deployment overview

EDON v1.0.1 ships as:

- A **Docker image**: `edon-server:v1.0.1`
  - REST API on port `8000` inside the container
  - gRPC service on port `50051` inside the container
- A **Python SDK**: `edon` wheel
- A **C++ SDK**: library + headers (see `sdk/cpp`)

You can run EDON:

- On a local dev machine (Docker Desktop)
- On an on-prem server
- Inside your robotics compute node (e.g., x86 or ARM, depending on build)

---

## 3. Running EDON via Docker

### 3.1 Basic run

Example local run mapping REST to `localhost:8002` and gRPC to `localhost:50052`:

```bash
docker run --rm \
  -p 8002:8000 \
  -p 50052:50051 \
  edon-server:v1.0.1
```

**Inside container**:
- REST: `http://0.0.0.0:8000`
- gRPC: `0.0.0.0:50051`

**From host**:
- REST: `http://localhost:8002`
- gRPC: `localhost:50052`

### 3.2 Health check

```bash
curl http://localhost:8002/health
```

**Expected response**:

```json
{
  "ok": true,
  "model": "cav_state_v3_2 sha256=...",
  "uptime_s": 123.45
}
```

---

## 4. REST API – `/oem/cav/batch`

### 4.1 Endpoint

- **Method**: `POST`
- **Path**: `/oem/cav/batch`
- **Content-Type**: `application/json`

### 4.2 Request schema (conceptual)

The request carries one or more 240-sample windows of sensor data.

A single window looks like:

```json
{
  "EDA":    [0.01, 0.02, ..., 2.40],
  "TEMP":   [36.5, 36.5, ..., 36.5],
  "BVP":    [...],
  "ACC_x":  [...],
  "ACC_y":  [...],
  "ACC_z":  [...],
  "temp_c":    22.0,
  "humidity":  50.0,
  "aqi":       30,
  "local_hour": 14
}
```

For batches, you send an array of such windows.

Refer to the OpenAPI spec served by the engine for the exact schema.

### 4.3 Example REST call

```bash
curl -X POST http://localhost:8002/oem/cav/batch \
  -H "Content-Type: application/json" \
  -d '{
    "windows": [{
      "EDA":    [0.0, 0.01, 0.02, 0.03],
      "TEMP":   [36.5, 36.5, 36.5, 36.5],
      "BVP":    [0.0, 0.1, 0.2, 0.3],
      "ACC_x":  [0.0, 0.0, 0.0, 0.0],
      "ACC_y":  [0.0, 0.0, 0.0, 0.0],
      "ACC_z":  [1.0, 1.0, 1.0, 1.0],
      "temp_c": 22.0,
      "humidity": 50.0,
      "aqi": 30,
      "local_hour": 14
    }]
  }'
```

**Note**: The arrays above show only 4 samples for brevity. In production, each array must contain exactly **240 samples**.

**Example response** (simplified):

```json
{
  "results": [{
    "ok": true,
    "cav_raw": 9793,
    "cav_smooth": 7255,
    "state": "restorative",
    "parts": {
      "bio": 0.96,
      "env": 1.0,
      "circadian": 1.0,
      "p_stress": 0.034
    }
  }],
  "latency_ms": 12.5,
  "server_version": "EDON CAV Engine v0.1.0"
}
```

---

## 5. Python SDK integration

### 5.1 Installation

From your own Python project (recommended in a virtualenv):

```bash
pip install edon-0.1.0-py3-none-any.whl
```

(or from PyPI once published: `pip install edon`)

### 5.2 Basic usage

```python
from edon import EdonClient
import math

client = EdonClient(base_url="http://localhost:8002")

window = {
    "EDA":   [0.01 * i for i in range(240)],
    "TEMP":  [36.5] * 240,
    "BVP":   [math.sin(i / 10.0) for i in range(240)],
    "ACC_x": [0.0] * 240,
    "ACC_y": [0.0] * 240,
    "ACC_z": [1.0] * 240,
    "temp_c":    22.0,
    "humidity":  50.0,
    "aqi":       30,
    "local_hour": 14,
}

res = client.cav(window)
print(res)
```

OEMs can embed this into their control loop and map state / p_stress to actuation limits.

---

## 6. C++ / robotics integration

For C++ and robotics use cases:

1. Build the C++ SDK under `sdk/cpp` (see [`sdk/cpp/README.md`](../sdk/cpp/README.md)).

2. Link your robot control stack against the EDON C++ client library.

3. Stream 240-sample windows into EDON at your chosen cadence.

4. Use the CAV outputs to:
   - Reduce speed / torque under high stress / overload.
   - Increase safety margins when `p_stress` is high.
   - Maintain efficient operation in balanced / focus states.

---

## 7. Versioning and compatibility

**Current engine release**: v1.0.1

REST and gRPC schemas are frozen for v1.

Breaking changes will ship in new versions:
- REST paths may include version prefixes (e.g. `/v2/oem/...`).
- gRPC package(s) may bump to `edon.v2`.

We recommend pinning the Docker image tag (`edon-server:v1.0.1`) and testing upgrades in a staging environment before deployment.

---

## 8. Support

For OEM integrations:

Share your:
- Sensor sample rates and feature map
- Desired update frequency for CAV
- Target platform (CPU / GPU, OS)

EDON can be tuned or re-trained on your distribution as needed.

---

## Additional Resources

- **API Contract**: See [`docs/OEM_API_CONTRACT.md`](OEM_API_CONTRACT.md) for complete API documentation
- **Integration Guide**: See [`docs/OEM_INTEGRATION.md`](OEM_INTEGRATION.md) for detailed integration examples
- **C++ SDK**: See [`sdk/cpp/README.md`](../sdk/cpp/README.md) for C++ build and usage

