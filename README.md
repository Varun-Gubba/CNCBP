# Network Monitoring and Intelligent Routing System

A full-stack, college-level network simulation and monitoring system demonstrating **Dijkstra's Shortest-Path Algorithm**, virtual IoT telemetry generation, fault injection, and live dashboard analytics.

---

## Architecture Overview

- **Backend (`/backend`)**:
  - Python, FastAPI, NetworkX (graph routing), Pydantic, Uvicorn, and WebSockets.
  - Generates realistic simulated environmental telemetry (`temperature`, `humidity`, `air_quality_aqi`).
  - Runs Dijkstra's algorithm to determine lowest-cost routes while tracking physical transmission delay (in ms) separately from route weight.
  - Exposes RESTful endpoints and a WebSocket channel at `ws://127.0.0.1:8000/ws`.
- **Frontend (`/frontend`)**:
  - React 19 + Vite, Vanilla CSS design system (cyber-network glassmorphism dark theme).
  - Graph visualization using `@xyflow/react` (React Flow) with interactive node failure toggles and glowing path highlights.
  - Live metric cards (Total, Delivered, Failed, Delivery Ratio %, Avg Latency, Avg Hops).
  - Packet simulation controls, sensor telemetry monitoring, and packet history table with detailed modal inspector.

---

## Quick Start (Windows PowerShell)

### Terminal 1: Launch Backend Server

```powershell
# 1. Navigate to project root
cd c:\Users\gubba\OneDrive\Desktop\CNCBP

# 2. Activate virtual environment
.\backend\venv\Scripts\Activate.ps1

# 3. Start FastAPI Uvicorn server
.\backend\venv\Scripts\uvicorn.exe main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```

- API Base URL: `http://127.0.0.1:8000`
- Swagger Interactive Docs: `http://127.0.0.1:8000/docs`

---

### Terminal 2: Launch React Frontend Dashboard

```powershell
# 1. Navigate to frontend directory
cd c:\Users\gubba\OneDrive\Desktop\CNCBP\frontend

# 2. Install dependencies (if not already installed)
npm install

# 3. Start Vite development server
npm run dev
```

- Frontend URL: `http://localhost:5173`

---

## How to Test and Demonstrate

1. **View Topology**: Observe the 7 nodes (`S1`, `S2`, `R1`, `R2`, `R3`, `G1`, `SRV`) and 10 links with costs and delays on the interactive canvas.
2. **Normal Routing**: Select Source `S1` and Destination `SRV`, then click **"Send Packet & Route"**.
   - Notice Dijkstra selects the lowest-cost 4-hop path: `S1 ➔ R1 ➔ R2 ➔ G1 ➔ SRV` (Cost: 9.0, Latency: 20.0 ms).
   - The path pulses with an animated cyan glow on the graph.
   - Metric cards increment and the packet appears in the history table as `DELIVERED`.
3. **Simulate Node Outage**: Click the **"Fail"** button on node `R2`.
   - Send another packet from `S1` to `SRV`.
   - Observe Dijkstra reroute automatically through `S1 ➔ R1 ➔ G1 ➔ SRV` (Cost: 12.0, Latency: 26.0 ms).
4. **Simulate Network Partition**: Click **"Fail"** on Gateway `G1`.
   - Send a packet from `S1` to `SRV`.
   - The packet status is marked `FAILED` with an explanation: destination unreachable.
   - The Delivery Ratio % decreases accordingly in the KPI cards.
5. **Reset**: Use **"Reset Network"** to restore all nodes, or **"Clear History"** to reset packet statistics.

---

## Testing Automated Suites

```powershell
# Run backend pytest suite (33 test cases: Phase 1 Routing + Phase 2 Edge AI)
.\backend\venv\Scripts\pytest.exe backend/test_backend.py backend/test_edge.py -v

# Run live integration script
.\backend\venv\Scripts\python.exe backend/live_test.py
```

---

## Phase 2: Edge AI & Environmental Anomaly Detection

### Architecture & Capabilities
- **Modular Edge Processing Engine (`/backend/edge`)**:
  - `detector.py`: Explainable moving-window statistical Z-scores, configurable regulatory threshold rules, rate-of-change ($\Delta v / \Delta t$) detection, and data sanity/staleness checks.
  - `risk_engine.py`: Multi-hazard risk scoring (0-100) and severity grading (LOW, MODERATE, HIGH, CRITICAL) with defensible confidence estimates across 7 hazards:
    1. **Flood & Flash Surge**: River stage, precipitation accumulation, and rate of rise.
    2. **Forest Fire**: Ambient dry heat, desiccated vegetation humidity, and smoke particulate byproducts.
    3. **Air Pollution**: CPCB NAAQS PM2.5, PM10, and sustained smog episode detection.
    4. **Extreme Heat**: IMD 40°C/45°C criteria and NOAA apparent Heat Index model.
    5. **Landslide Precursors**: Volumetric pore saturation and geotechnical micro-vibrations.
    6. **Industrial Gas Leak**: Chemical toxic/combustible gas concentration spikes.
    7. **Water Quality**: BIS IS 10500 potable limits for pH, turbidity, and dissolved oxygen.
  - `ml_model.py`: Self-contained, lightweight pure-Python Isolation Forest for multivariate outlier detection.
  - `persistence.py`: SQLite-backed FIFO buffer preserving pending alerts across outages and process restarts.
  - `edge_node.py`: Autonomous local edge processing with lifecycle de-duplication (`NEW`, `CONTINUING`, `WORSENING`, `RESOLVED`).

### Offline Mode & Computer Networks Integration
- Edge nodes continue analyzing sensor telemetry locally when central connectivity is broken.
- Pending alerts are stored in a persistent local queue with unique event IDs (`EVT-*`).
- When connectivity is restored, the `POST /edge/nodes/{id}/sync` endpoint automatically dispatches queued alerts across the NetworkX Dijkstra router to Central Server `SRV`, recording delivery status, hop count, and simulated latency.

