# EDON OEM API Contract v1

**Status**: FROZEN  
**Version**: v1.0  
**Last Updated**: 2025-11-20

This document defines the exact API contract for EDON CAV Engine. **v1 is stable** - breaking changes will result in v2.

---

## REST API Contract

### Endpoint: `POST /oem/cav/batch`

**Base URL**: `http://localhost:8001` (configurable via `EDON_BASE_URL`)

**Authentication**: Optional, via `Authorization: Bearer <EDON_API_TOKEN>` header

**Content-Type**: `application/json`

### Request Schema

```json
{
  "windows": [
    {
      "EDA": [0.1, 0.12, ...],      // 240 floats - Electrodermal activity
      "TEMP": [36.5, 36.5, ...],    // 240 floats - Temperature
      "BVP": [0.5, 0.52, ...],      // 240 floats - Blood volume pulse
      "ACC_x": [0.0, 0.01, ...],    // 240 floats - Accelerometer X
      "ACC_y": [0.0, -0.01, ...],   // 240 floats - Accelerometer Y
      "ACC_z": [1.0, 1.0, ...],     // 240 floats - Accelerometer Z
      "temp_c": 22.0,               // float - Ambient temperature (°C)
      "humidity": 50.0,             // float - Relative humidity (%)
      "aqi": 35,                    // int - Air Quality Index
      "local_hour": 14              // int - Local hour [0-23]
    }
  ]
}
```

**Constraints**:
- `windows`: Array of 1-5 window objects
- Each signal array (`EDA`, `TEMP`, `BVP`, `ACC_x`, `ACC_y`, `ACC_z`): Exactly 240 floats
- `temp_c`: Float, typically 18.0-35.0
- `humidity`: Float, typically 20.0-80.0
- `aqi`: Integer, typically 0-300
- `local_hour`: Integer, 0-23

### Response Schema

```json
{
  "results": [
    {
      "ok": true,
      "cav_raw": 8500,              // int [0-10000] - Raw CAV score
      "cav_smooth": 8200,           // int [0-10000] - EMA-smoothed CAV score
      "state": "balanced",          // string - One of: overload, balanced, focus, restorative
      "parts": {
        "bio": 0.95,                // float [0.0-1.0] - Biological score
        "env": 0.85,                // float [0.0-1.0] - Environmental score
        "circadian": 1.0,           // float [0.0-1.0] - Circadian score
        "p_stress": 0.05            // float [0.0-1.0] - Probability of stress
      }
    }
  ],
  "latency_ms": 12.5,
  "server_version": "EDON CAV Engine v0.1.0"
}
```

**Error Response**:
```json
{
  "results": [
    {
      "ok": false,
      "error": "Invalid window length for EDA: expected 240, got 100"
    }
  ],
  "latency_ms": 5.2,
  "server_version": "EDON CAV Engine v0.1.0"
}
```

### Example Request (curl)

```bash
curl -X POST http://localhost:8001/oem/cav/batch \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "windows": [{
      "EDA": [0.1] * 240,
      "TEMP": [36.5] * 240,
      "BVP": [0.5] * 240,
      "ACC_x": [0.0] * 240,
      "ACC_y": [0.0] * 240,
      "ACC_z": [1.0] * 240,
      "temp_c": 22.0,
      "humidity": 50.0,
      "aqi": 35,
      "local_hour": 14
    }]
  }'
```

---

## gRPC API Contract

### Service: `edon.v1.EdonService`

**Package**: `edon.v1` (versioned for stability)

**Port**: `50051` (default)

### RPC Methods

#### `GetState(CavRequest) -> CavResponse`

Single request/response for CAV computation.

**Request** (`CavRequest`):
```protobuf
message CavRequest {
    repeated float eda = 1;          // 240 samples
    repeated float temp = 2;         // 240 samples
    repeated float bvp = 3;          // 240 samples
    repeated float acc_x = 4;        // 240 samples
    repeated float acc_y = 5;        // 240 samples
    repeated float acc_z = 6;        // 240 samples
    float temp_c = 7;                // Ambient temperature (°C)
    float humidity = 8;              // Relative humidity (%)
    int32 aqi = 9;                   // Air Quality Index
    int32 local_hour = 10;           // Local hour [0-23]
}
```

**Response** (`CavResponse`):
```protobuf
message CavResponse {
    int32 cav_raw = 1;               // [0-10000]
    int32 cav_smooth = 2;            // [0-10000]
    string state = 3;                // overload, balanced, focus, restorative
    ComponentScores parts = 4;
    ControlScales controls = 5;
    int64 timestamp_ms = 6;
}

message ComponentScores {
    float bio = 1;                   // [0.0-1.0]
    float env = 2;                   // [0.0-1.0]
    float circadian = 3;             // [0.0-1.0]
    float p_stress = 4;              // [0.0-1.0]
}

message ControlScales {
    float speed = 1;                 // [0.0-1.0]
    float torque = 2;                // [0.0-1.0]
    float safety = 3;                // [0.0-1.0]
}
```

#### `StreamState(StateStreamRequest) -> stream StateStreamResponse`

Server-side streaming for continuous state updates.

**Request** (`StateStreamRequest`): Same as `CavRequest` plus `stream_mode = true`

**Response**: Stream of `StateStreamResponse` (same structure as `CavResponse`)

---

## Versioning Policy

### v1 (Current)
- **Status**: FROZEN
- **Breaking Changes**: None allowed
- **Additive Changes**: New optional fields only

### Future Versions
- Breaking changes will result in new package version (e.g., `edon.v2`)
- v1 will remain supported for backward compatibility
- Migration guides will be provided

---

## Authentication & Security

### REST API

**Production Setup**:
```bash
export EDON_AUTH_ENABLED=true
export EDON_API_TOKEN=your-secret-token
```

**Request Header**:
```
Authorization: Bearer your-secret-token
```

**Example curl**:
```bash
curl -X POST http://localhost:8001/oem/cav/batch \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-secret-token" \
  -d '{"windows": [...]}'
```

**Python SDK**:
```python
from edon import EdonClient

client = EdonClient(
    base_url="http://localhost:8001",
    api_key="your-secret-token"
)
```

### gRPC

Authentication via metadata (future enhancement):
```python
import grpc

metadata = [('authorization', 'Bearer your-secret-token')]
context = grpc.ClientContext()
for key, value in metadata:
    context.add_metadata(key, value)

response = stub.GetState(context, request)
```

### Security Best Practices

1. **Use HTTPS in production** (via reverse proxy)
2. **Set strong API tokens** (minimum 32 characters)
3. **Rotate tokens regularly**
4. **Monitor `/metrics` endpoint** for unusual activity
5. **Use firewall rules** to restrict access to known IPs

---

## State Values

EDON returns one of four states:

| State | Description | Conditions |
|-------|-------------|------------|
| `restorative` | Very low stress, optimal recovery | `p_stress < 0.2` |
| `focus` | Moderate stress with strong alignment | `0.2 ≤ p_stress ≤ 0.5` AND `env ≥ 0.8` AND `circadian ≥ 0.9` |
| `balanced` | Normal operation, moderate stress | `0.2 ≤ p_stress < 0.8` (when focus conditions not met) |
| `overload` | High stress, needs intervention | `p_stress ≥ 0.8` |

**State Mapping Logic**:
- **Restorative**: Very low stress indicates optimal recovery state
- **Focus**: Moderate stress combined with excellent environment and circadian alignment indicates focused, productive state
- **Balanced**: Normal operation with moderate stress levels
- **Overload**: High stress requires intervention regardless of other factors

---

## Error Codes

### REST API

- `400`: Bad Request (invalid window format, wrong length)
- `401`: Unauthorized (missing/invalid token)
- `422`: Validation Error (missing required fields)
- `500`: Internal Server Error

### gRPC

- `INVALID_ARGUMENT`: Invalid request (wrong window length, etc.)
- `UNAUTHENTICATED`: Missing/invalid authentication
- `INTERNAL`: Server error

---

## Rate Limits

Currently: No rate limits  
Future: May implement rate limiting per API key

## Health & Monitoring

### Health Check

**Endpoint**: `GET /health`

**Response**:
```json
{
  "ok": true,
  "model": "cav_state_v3_2 sha256=abc123... features=6 window=240*4Hz pca=128",
  "uptime_s": 1234.5
}
```

### Telemetry

**Endpoint**: `GET /telemetry`

**Response**:
```json
{
  "request_count": 1250,
  "avg_latency_ms": 15.3,
  "uptime_seconds": 3600.0
}
```

### Prometheus Metrics

**Endpoint**: `GET /metrics`

**Response** (Prometheus format):
```
# HELP edon_requests_total Total number of requests
# TYPE edon_requests_total counter
edon_requests_total 1250

# HELP edon_latency_ms Average request latency in milliseconds
# TYPE edon_latency_ms gauge
edon_latency_ms 15.30

# HELP edon_uptime_seconds Server uptime in seconds
# TYPE edon_uptime_seconds gauge
edon_uptime_seconds 3600.00
```

**Scraping**: Configure Prometheus to scrape `http://localhost:8001/metrics`

---

## Support

For API questions or issues, contact the EDON team.

**Contract Version**: v1.0  
**Last Updated**: 2025-11-20

