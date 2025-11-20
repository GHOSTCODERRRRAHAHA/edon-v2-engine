# EDON API Overview

## REST API

### Base URL
- Default: `http://127.0.0.1:8000`
- Configurable via `EDON_BASE_URL` environment variable

### Authentication
- Optional API token via `EDON_API_TOKEN` environment variable
- Sent as `Authorization: Bearer <token>` header

### Endpoints

#### `POST /oem/cav/batch`
Batch CAV computation (1-5 windows per request).

**Request:**
```json
{
  "windows": [
    {
      "EDA": [0.1, ...],  // 240 floats
      "TEMP": [36.5, ...], // 240 floats
      "BVP": [0.5, ...],   // 240 floats
      "ACC_x": [0.0, ...], // 240 floats
      "ACC_y": [0.0, ...], // 240 floats
      "ACC_z": [1.0, ...], // 240 floats
      "temp_c": 22.0,
      "humidity": 50.0,
      "aqi": 35,
      "local_hour": 14
    }
  ]
}
```

**Response:**
```json
{
  "results": [
    {
      "ok": true,
      "cav_raw": 8500,
      "cav_smooth": 8200,
      "state": "balanced",
      "parts": {
        "bio": 0.95,
        "env": 0.85,
        "circadian": 1.0,
        "p_stress": 0.05
      }
    }
  ]
}
```

#### `GET /health`
Health check endpoint.

**Response:**
```json
{
  "ok": true,
  "model": "cav_state_v3_2",
  "uptime_s": 1234
}
```

## gRPC API

### Server
- Default: `localhost:50051`
- Configurable via `grpc_host` and `grpc_port` parameters

### Service: `EdonService`

#### `GetState(StreamDataRequest) -> StreamStateResponse`
Single request/response for CAV computation.

#### `StreamState(StreamDataRequest) -> stream StreamStateResponse`
Server-side streaming (push updates continuously).

### Message Types

See `integrations/grpc/edon_grpc_service/edon.proto` for full protocol definitions.

## Python SDK

See `sdk/python/README.md` for SDK usage.

