# Network Monitoring and Intelligent Routing System

A modular, high-performance Python FastAPI backend simulation engine demonstrating **Dijkstra's Shortest-Path Algorithm**, virtual network topology monitoring, dynamic telemetry generation, packet routing, and real-time performance analytics.

---

## 1. Project Overview

In computer networking and IoT telemetry, edge sensors monitor conditions (such as temperature, humidity, and air quality) and transmit telemetry packets across intermediate routers and gateways to reach a central monitoring server. 

This project simulates that process in software:
- **Virtual Network Topology**: Models sensors (`S1`, `S2`), routers (`R1`, `R2`, `R3`), a gateway (`G1`), and a central server (`SRV`) as a weighted, delay-annotated graph using **NetworkX**.
- **Dijkstra's Algorithm**: Dynamically computes the lowest-cost path between any active source and destination.
- **Independent Delay vs. Cost Calculation**: Separates routing decisions (based on link cost/weights) from physical transmission latency (accumulated link delay in milliseconds).
- **Packet Lifecycle Simulation**: Simulates packet creation, environmental telemetry attachment, transmission attempts, and delivery states (`DELIVERED` vs. `FAILED`).
- **Network Performance Metrics**: Computes packet delivery ratio (PDR %), average latency, and average hop count without division-by-zero risks.
- **Fault Simulation**: Supports disabling individual nodes or links to demonstrate real-time path rerouting or destination unreachability.
- **WebSocket Readiness**: Features a non-blocking WebSocket endpoint (`/ws`) for live packet notifications.

---

## 2. Folder Structure

```text
CNCBP/
└── backend/
    ├── venv/                   # Python virtual environment
    ├── main.py                 # FastAPI application, routes, CORS & WebSocket
    ├── network.py              # Virtual network graph & Dijkstra routing logic (NetworkX)
    ├── simulator.py            # Telemetry generator, packet lifecycle & metrics
    ├── models.py               # Pydantic schemas and request/response models
    ├── requirements.txt        # Backend dependencies
    ├── test_backend.py         # Automated test suite (Pytest + TestClient)
    ├── live_test.py            # Live integration test runner
    └── README.md               # Complete project documentation
```

---

## 3. Virtual Network Topology

### Nodes

| Node ID | Type | Name | Initial Status | Role |
| :--- | :--- | :--- | :--- | :--- |
| `S1` | Sensor | Sensor Node 1 - Temp & Humidity | `active` | Edge sensor node |
| `S2` | Sensor | Sensor Node 2 - Environmental Monitor | `active` | Edge sensor node |
| `R1` | Router | Router 1 - Edge Router Alpha | `active` | Intermediate router |
| `R2` | Router | Router 2 - Backbone Router Beta | `active` | Central backbone router |
| `R3` | Router | Router 3 - Backbone Router Gamma | `active` | Intermediate router |
| `G1` | Gateway | Gateway 1 - Primary Gateway | `active` | Network egress gateway |
| `SRV` | Server | Central Server - Datacenter | `active` | Central monitoring datacenter |

### Links (Bidirectional)

| Link (Endpoints) | Link Cost (Dijkstra Weight) | Estimated Delay (ms) | Initial Status |
| :--- | :--- | :--- | :--- |
| `S1` ↔ `R1` | 3.0 | 6.0 ms | `active` |
| `S1` ↔ `R2` | 7.0 | 14.0 ms | `active` |
| `S2` ↔ `R2` | 4.0 | 9.0 ms | `active` |
| `S2` ↔ `R3` | 2.0 | 5.0 ms | `active` |
| `R1` ↔ `R2` | 2.0 | 4.0 ms | `active` |
| `R1` ↔ `G1` | 8.0 | 18.0 ms | `active` |
| `R2` ↔ `R3` | 3.0 | 7.0 ms | `active` |
| `R2` ↔ `G1` | 3.0 | 8.0 ms | `active` |
| `R3` ↔ `G1` | 4.0 | 9.0 ms | `active` |
| `G1` ↔ `SRV` | 1.0 | 2.0 ms | `active` |

---

## 4. How Dijkstra's Algorithm & Metrics Work

### 1. Dijkstra Routing Logic
When a route is requested from `S1` to `SRV`:
- **Path 1**: `S1 -> R1 -> G1 -> SRV`
  - Total Cost: $3 + 8 + 1 = 12.0$
  - Total Delay: $6 + 18 + 2 = 26.0\text{ ms}$
  - Hops: 3
- **Path 2**: `S1 -> R1 -> R2 -> G1 -> SRV`
  - Total Cost: $3 + 2 + 3 + 1 = 9.0$ (**Lowest Cost!**)
  - Total Delay: $6 + 4 + 8 + 2 = 20.0\text{ ms}$
  - Hops: 4
- **Path 3**: `S1 -> R2 -> G1 -> SRV`
  - Total Cost: $7 + 3 + 1 = 11.0$
  - Total Delay: $14 + 8 + 2 = 24.0\text{ ms}$
  - Hops: 3

**Why Path 2 is chosen:** Dijkstra evaluates cumulative edge weights (`cost`). Even though Path 2 has more hops (4 hops vs 3 hops), its total cost ($9.0$) is strictly lower than Path 1 ($12.0$) and Path 3 ($11.0$).

### 2. Failure Adaptation
If router `R2` fails (status set to `inactive`):
- Path 2 and Path 3 become invalid because the active subgraph excludes `R2`.
- Dijkstra automatically routes through **Path 1**: `S1 -> R1 -> G1 -> SRV` (Cost: $12.0$, Latency: $26.0\text{ ms}$).

### 3. Metric Calculations
- **Packet Delivery Ratio (PDR %)**:
  $$\text{PDR} = \left(\frac{\text{Delivered Packets}}{\text{Total Packets}}\right) \times 100$$
- **Average Latency**:
  $$\text{Avg Latency} = \frac{\sum \text{Delivered Packet Latency}}{\text{Delivered Packets}}$$
- **Average Hop Count**:
  $$\text{Avg Hops} = \frac{\sum \text{Delivered Packet Hops}}{\text{Delivered Packets}}$$
- Both averages evaluate to `0.0` when total delivered packets is zero, preventing `ZeroDivisionError`.

---

## 5. Setup and Installation

### Prerequisites
- Python 3.10+ (tested on Python 3.13)
- Windows PowerShell

### Step 1: Clone or Navigate to the Project Directory
```powershell
cd c:\Users\gubba\OneDrive\Desktop\CNCBP
```

### Step 2: Create and Activate Virtual Environment
```powershell
# Create venv if not already created
python -m venv backend/venv

# Activate venv in PowerShell
.\backend\venv\Scripts\Activate.ps1
```

*(If PowerShell execution policies restrict script activation, run: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`)*

### Step 3: Install Required Dependencies
```powershell
.\backend\venv\Scripts\pip.exe install -r backend/requirements.txt
```

---

## 6. Running the Development Server

Start the backend with Uvicorn:
```powershell
.\backend\venv\Scripts\uvicorn.exe main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```

- **Base URL**: `http://127.0.0.1:8000`
- **Interactive Swagger Docs**: `http://127.0.0.1:8000/docs`
- **ReDoc Documentation**: `http://127.0.0.1:8000/redoc`

---

## 7. API Endpoints & Sample Requests

### 1. `GET /` — Root Status
Confirms backend availability.
- **Request**:
  ```powershell
  curl http://127.0.0.1:8000/
  ```
- **Response**:
  ```json
  {
    "project": "Network Monitoring and Intelligent Routing System",
    "status": "running",
    "version": "1.0.0",
    "message": "Backend is operational and ready to simulate routing.",
    "docs_url": "/docs"
  }
  ```

---

### 2. `GET /health` — Health Check
Returns operational health and count of active nodes and links.
- **Request**:
  ```powershell
  curl http://127.0.0.1:8000/health
  ```
- **Response**:
  ```json
  {
    "status": "healthy",
    "timestamp": "2026-10-12T16:12:26.320729+00:00",
    "active_nodes": 7,
    "total_nodes": 7,
    "active_links": 10,
    "total_links": 10
  }
  ```

---

### 3. `GET /network` — Topology Graph
Returns all nodes and links including types, statuses, costs, and delays.
- **Request**:
  ```powershell
  curl http://127.0.0.1:8000/network
  ```
- **Response (truncated)**:
  ```json
  {
    "nodes": [
      {
        "id": "S1",
        "name": "Sensor Node 1 - Temp & Humidity",
        "type": "sensor",
        "status": "active"
      },
      {
        "id": "SRV",
        "name": "Central Server - Monitoring Datacenter",
        "type": "server",
        "status": "active"
      }
    ],
    "links": [
      {
        "source": "S1",
        "destination": "R1",
        "cost": 3.0,
        "delay": 6.0,
        "status": "active"
      }
    ],
    "active_nodes_count": 7,
    "active_links_count": 10
  }
  ```

---

### 4. `GET /sensors` — Available Sensors
Returns all edge monitoring sensor nodes.
- **Request**:
  ```powershell
  curl http://127.0.0.1:8000/sensors
  ```
- **Response**:
  ```json
  [
    {
      "id": "S1",
      "name": "Sensor Node 1 - Temp & Humidity",
      "type": "sensor",
      "status": "active"
    },
    {
      "id": "S2",
      "name": "Sensor Node 2 - Environmental Monitor",
      "type": "sensor",
      "status": "active"
    }
  ]
  ```

---

### 5. `GET /route?source=S1&destination=SRV` — Dijkstra Routing
Computes the optimal path and breaks down cost and delay for every hop.
- **Request**:
  ```powershell
  curl "http://127.0.0.1:8000/route?source=S1&destination=SRV"
  ```
- **Response**:
  ```json
  {
    "source": "S1",
    "destination": "SRV",
    "route": ["S1", "R1", "R2", "G1", "SRV"],
    "total_cost": 9.0,
    "hop_count": 4,
    "estimated_latency_ms": 20.0,
    "path_details": [
      {
        "hop_number": 1,
        "from_node": "S1",
        "to_node": "R1",
        "link_cost": 3.0,
        "link_delay_ms": 6.0
      },
      {
        "hop_number": 2,
        "from_node": "R1",
        "to_node": "R2",
        "link_cost": 2.0,
        "link_delay_ms": 4.0
      },
      {
        "hop_number": 3,
        "from_node": "R2",
        "to_node": "G1",
        "link_cost": 3.0,
        "link_delay_ms": 8.0
      },
      {
        "hop_number": 4,
        "from_node": "G1",
        "to_node": "SRV",
        "link_cost": 1.0,
        "link_delay_ms": 2.0
      }
    ]
  }
  ```

---

### 6. `POST /simulate` — Packet Simulation
Generates telemetry data, calculates optimal route, and delivers the packet.
- **Request (Default Payload)**:
  ```powershell
  curl -X POST http://127.0.0.1:8000/simulate `
    -H "Content-Type: application/json" `
    -d '{"source": "S1", "destination": "SRV"}'
  ```
- **Response**:
  ```json
  {
    "packet_id": "PKT-1001-FEB2",
    "source": "S1",
    "destination": "SRV",
    "payload": {
      "sensor_id": "S1",
      "timestamp": "2026-10-12T16:12:26.336144+00:00",
      "temperature_celsius": 24.59,
      "humidity_percentage": 60.22,
      "air_quality_aqi": 97.6,
      "is_simulated": true,
      "notes": "Simulated environmental reading - not physical sensor measurement"
    },
    "created_at": "2026-10-12T16:12:26.336144+00:00",
    "route": ["S1", "R1", "R2", "G1", "SRV"],
    "status": "DELIVERED",
    "hop_count": 4,
    "total_cost": 9.0,
    "estimated_latency_ms": 20.0,
    "failure_reason": null
  }
  ```

---

### 7. `GET /packets` — Packet Records
Retrieves latest 100 packets (newest first).
- **Request**:
  ```powershell
  curl http://127.0.0.1:8000/packets?limit=10
  ```

---

### 8. `GET /metrics` — Aggregate Performance Metrics
Calculates total packets, delivery ratio %, and averages.
- **Request**:
  ```powershell
  curl http://127.0.0.1:8000/metrics
  ```
- **Response**:
  ```json
  {
    "total_packets": 3,
    "delivered_packets": 2,
    "failed_packets": 1,
    "delivery_ratio_percentage": 66.67,
    "average_latency_ms": 18.0,
    "average_hop_count": 3.5
  }
  ```

---

### 9. `POST /reset` — Reset Simulation History
Clears packet history and metrics back to 0 without modifying the network topology.
- **Request**:
  ```powershell
  curl -X POST http://127.0.0.1:8000/reset
  ```

---

### 10. Fault Injection / Topology Management
- **Disable Node (e.g., simulate router failure)**:
  ```powershell
  curl -X PATCH http://127.0.0.1:8000/network/nodes/R2/status `
    -H "Content-Type: application/json" `
    -d '{"status": "inactive"}'
  ```
- **Disable Link**:
  ```powershell
  curl -X PATCH http://127.0.0.1:8000/network/links/status `
    -H "Content-Type: application/json" `
    -d '{"source": "R1", "destination": "G1", "status": "inactive"}'
  ```
- **Reset Network Topology**:
  ```powershell
  curl -X POST http://127.0.0.1:8000/network/reset
  ```

---

## 8. WebSocket Integration (`/ws`)

A lightweight WebSocket connection endpoint is available at `ws://127.0.0.1:8000/ws`.

When packets are simulated via `POST /simulate`, the server broadcasts an event to all connected clients:
```json
{
  "event": "packet_simulated",
  "packet": { ...packet_details... }
}
```
Client disconnections and ping heartbeats are handled cleanly without exceptions.

---

## 9. Running Automated Tests

Run the full automated test suite using Pytest:
```powershell
.\backend\venv\Scripts\pytest.exe backend/test_backend.py -v
```

All 19 test cases cover:
- Root & health status
- Topology graph integrity & sensor listing
- Dijkstra optimal path selection across multiple paths
- Dynamic rerouting on node outages
- Unreachable destinations & error handling
- Packet generation with default and custom payloads
- Zero-packet metric calculation (division-by-zero safety)
- Bounded packet history limits
- WebSocket connectivity & echo response

---

## 10. Frontend Connection (React + Vite)

CORS is pre-configured for React / Vite running at `http://localhost:5173`.

Example fetch in frontend:
```javascript
// Fetch shortest route
const response = await fetch('http://127.0.0.1:8000/route?source=S1&destination=SRV');
const routeData = await response.json();
console.log('Optimal path:', routeData.route);

// Simulate packet
const simResponse = await fetch('http://127.0.0.1:8000/simulate', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ source: 'S1', destination: 'SRV' })
});
const packet = await simResponse.json();
console.log('Packet status:', packet.status);
```
