"""
FastAPI Application Entry Point for Network Monitoring and Intelligent Routing System.
Exposes RESTful endpoints for network topology, Dijkstra shortest-path routing,
environmental telemetry simulation, packet tracking, network metrics, and WebSocket support.
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
import logging
from typing import List, Optional, Set, Dict, Any

from fastapi import (
    FastAPI,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
    Request,
)
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from models import (
    Node,
    Link,
    NetworkTopologyResponse,
    RouteResponse,
    SimulateRequest,
    Packet,
    MetricsResponse,
    RootResponse,
    HealthResponse,
    MessageResponse,
    UpdateNodeStatusRequest,
    UpdateLinkStatusRequest,
    NodeStatus,
    LinkStatus,
    EnvironmentalData,
    HazardType,
    SeverityLevel,
    AlertLifecycle,
    AnomalyResult,
    RiskAssessment,
    EdgeAlert,
    EdgeNodeState,
    EdgeConnectivityRequest,
    EdgeSyncResponse,
    EdgeScenarioRequest,
)
from network import (
    VirtualNetwork,
    NodeNotFoundError,
    NodeInactiveError,
    DestinationUnreachableError,
    NetworkRoutingError,
)
from simulator import PacketSimulator, EnvironmentalSimulator
from edge import (
    EdgeNode,
    EdgeThresholdConfig,
    DEFAULT_THRESHOLDS,
)

# Configure application logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("network_backend")

# Initialize global core instances
virtual_network = VirtualNetwork()
packet_simulator = PacketSimulator(max_history=100)

# Initialize Edge AI Nodes for simulated sensors S1 and S2
edge_nodes: dict[str, EdgeNode] = {
    "S1": EdgeNode(
        node_id="S1",
        location="Uttarakhand - Alaknanda Basin (Multi-Hazard Station)",
    ),
    "S2": EdgeNode(
        node_id="S2",
        location="Delhi-NCR - Anand Vihar Industrial Corridor (AQI & Heat Station)",
    ),
}


def route_edge_alert_transmission(edge_node: EdgeNode, alert_dict: dict) -> Optional[dict]:
    """Transmits high-priority edge alert to Central Server SRV via NetworkX Dijkstra route."""
    meas = alert_dict.get("contributing_measurements", {})
    temp = float(meas.get("temperature_celsius", 25.0))
    hum = float(meas.get("humidity_percentage", 60.0))
    aqi = float(meas.get("air_quality_aqi", 50.0)) if meas.get("air_quality_aqi") is not None else None

    payload = EnvironmentalData(
        sensor_id=edge_node.node_id,
        location=edge_node.location,
        timestamp=alert_dict.get("created_at", datetime.now(timezone.utc).isoformat()),
        temperature_celsius=temp,
        humidity_percentage=hum,
        air_quality_aqi=aqi,
        rainfall_mm=meas.get("rainfall_mm"),
        water_level_m=meas.get("water_level_m"),
        water_level_rise_rate_m_h=meas.get("water_level_rise_rate_m_h"),
        smoke_ppm=meas.get("smoke_ppm"),
        pm25=meas.get("pm25"),
        pm10=meas.get("pm10"),
        soil_moisture_percentage=meas.get("soil_moisture_percentage"),
        vibration_g=meas.get("vibration_g"),
        gas_concentration_ppm=meas.get("gas_concentration_ppm"),
        ph=meas.get("ph"),
        turbidity_ntu=meas.get("turbidity_ntu"),
        dissolved_oxygen_mg_l=meas.get("dissolved_oxygen_mg_l"),
        is_simulated=True,
        notes=f"PRIORITIZED ALERT [{alert_dict.get('hazard_type')} - {alert_dict.get('severity')}] {alert_dict.get('event_id')}: {alert_dict.get('explanation')}",
    )

    try:
        packet = packet_simulator.simulate_transmission(
            network=virtual_network,
            source=edge_node.node_id,
            destination="SRV",
            payload=payload,
        )
        return {
            "status": packet.status.value,
            "packet_id": packet.packet_id,
            "route": packet.route,
            "total_cost": packet.total_cost,
            "estimated_latency_ms": packet.estimated_latency_ms,
            "failure_reason": packet.failure_reason,
        }
    except Exception as e:
        logger.warning(f"Alert routing failed for {edge_node.node_id}: {e}")
        return {"status": "FAILED", "failure_reason": str(e)}


for node in edge_nodes.values():
    node.set_transmission_callback(route_edge_alert_transmission)



# --- WebSocket Connection Manager for Future Real-Time Streaming ---

class ConnectionManager:
    """Manages active WebSocket connections safely without blocking."""

    def __init__(self) -> None:
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket client connected. Total active: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket) -> None:
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket client disconnected. Total active: {len(self.active_connections)}")

    async def broadcast_json(self, data: dict) -> None:
        """Safely broadcast JSON payload to all connected clients."""
        disconnected = []
        for connection in list(self.active_connections):
            try:
                await connection.send_json(data)
            except Exception as e:
                logger.warning(f"Failed to send to client: {e}. Marking for removal.")
                disconnected.append(connection)

        for dead_conn in disconnected:
            self.disconnect(dead_conn)


ws_manager = ConnectionManager()


# --- Application Setup ---

app = FastAPI(
    title="Network Monitoring and Intelligent Routing System",
    description=(
        "Backend API for virtual sensor network monitoring and Dijkstra's algorithm "
        "shortest-path packet routing simulation."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration allowing React + Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "*",  # Permissive for development convenience
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Custom Exception Handlers to Prevent Stack Trace Leaks ---

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Formats validation errors cleanly."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "ValidationError",
            "message": "Invalid request parameter or payload structure.",
            "details": exc.errors(),
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Ensures consistent JSON error format for HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "ClientError",
            "message": exc.detail,
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Catches all unexpected internal errors and hides server stack traces."""
    logger.error(f"Unexpected internal server error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred while processing the request.",
        },
    )


# --- API Endpoints ---

@app.get("/", response_model=RootResponse, tags=["General"])
def get_root():
    """Return the project name and confirmation that the backend is running."""
    return RootResponse(
        project="Network Monitoring and Intelligent Routing System",
        status="running",
        version="1.0.0",
        message="Backend is operational and ready to simulate routing.",
        docs_url="/docs",
    )


@app.get("/health", response_model=HealthResponse, tags=["General"])
def get_health():
    """Return backend health status with topology counts."""
    topo = virtual_network.get_topology()
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc).isoformat(),
        active_nodes=topo.active_nodes_count,
        total_nodes=len(topo.nodes),
        active_links=topo.active_links_count,
        total_links=len(topo.links),
    )


@app.get("/network", response_model=NetworkTopologyResponse, tags=["Network Topology"])
def get_network():
    """Return all network nodes and links, including types, weights, delays, and statuses."""
    return virtual_network.get_topology()


@app.get("/sensors", response_model=List[Node], tags=["Network Topology"])
def get_sensors():
    """Return the available monitoring sensors in the network."""
    return virtual_network.get_sensors()


@app.get("/route", response_model=RouteResponse, tags=["Routing"])
def get_shortest_route(
    source: str = Query(..., description="Source node ID (e.g. S1)"),
    destination: str = Query(..., description="Destination node ID (e.g. SRV)"),
):
    """
    Calculate and return the shortest route using Dijkstra's algorithm,
    along with total route cost, hop count, and estimated physical latency.
    """
    try:
        return virtual_network.find_shortest_path(source=source.strip(), destination=destination.strip())
    except NodeNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (NodeInactiveError, DestinationUnreachableError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except NetworkRoutingError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.post("/simulate", response_model=Packet, tags=["Packet Simulation"])
async def simulate_packet_transmission(request: SimulateRequest):
    """
    Generate environmental data (if not supplied), create a packet,
    calculate Dijkstra shortest route, simulate logical transmission,
    and return packet details and performance metrics.
    """
    src = request.source.strip()
    dst = request.destination.strip()

    # Validate node existence
    if src not in virtual_network.nodes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source node '{src}' does not exist in network topology.",
        )
    if dst not in virtual_network.nodes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Destination node '{dst}' does not exist in network topology.",
        )

    # Simulate packet transmission
    packet = packet_simulator.simulate_transmission(
        network=virtual_network,
        source=src,
        destination=dst,
        payload=request.payload,
    )

    # Optional real-time WebSocket broadcast for connected frontend listeners
    await ws_manager.broadcast_json({
        "event": "packet_simulated",
        "packet": packet.model_dump(),
    })

    return packet


@app.get("/packets", response_model=List[Packet], tags=["Packet Simulation"])
def get_packets(limit: int = Query(default=100, ge=1, le=100, description="Max packets to retrieve")):
    """Return recent packet records (up to 100, newest first)."""
    return packet_simulator.get_packets(limit=limit)


@app.get("/metrics", response_model=MetricsResponse, tags=["Network Metrics"])
def get_metrics():
    """
    Return network performance metrics:
    - Total packets created
    - Delivered packets
    - Failed packets
    - Packet delivery ratio as a percentage
    - Average estimated latency
    - Average hop count
    Safely handles zero packets without division-by-zero.
    """
    return packet_simulator.get_metrics()


@app.post("/reset", response_model=MessageResponse, tags=["System"])
def reset_simulation():
    """
    Reset packet history and simulation statistics to their initial state.
    Does not remove the default network topology.
    """
    packet_simulator.reset()
    return MessageResponse(
        message="Packet history and simulation metrics have been reset successfully.",
        success=True,
    )


# --- Node & Link Status Controls (For Simulating Link/Node Outages) ---

@app.patch("/network/nodes/{node_id}/status", response_model=Node, tags=["Network Management"])
def update_node_status(node_id: str, request: UpdateNodeStatusRequest):
    """Enable or disable a network node to simulate hardware or power failures."""
    try:
        updated_node = virtual_network.set_node_status(node_id=node_id.strip(), status=request.status)
        return updated_node
    except NodeNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@app.patch("/network/links/status", response_model=Link, tags=["Network Management"])
def update_link_status(request: UpdateLinkStatusRequest):
    """Enable or disable a link to simulate physical link cuts or degradation."""
    try:
        updated_link = virtual_network.set_link_status(
            source=request.source.strip(),
            destination=request.destination.strip(),
            status=request.status,
        )
        return updated_link
    except NetworkRoutingError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@app.post("/network/reset", response_model=MessageResponse, tags=["Network Management"])
def reset_network_topology():
    """Restores all network nodes and links to their default active state."""
    virtual_network.reset()
    return MessageResponse(
        message="Virtual network topology restored to default operational state.",
        success=True,
    )


# --- Phase 2: Edge AI Intelligence Endpoints ---

@app.get("/edge/nodes", response_model=List[EdgeNodeState], tags=["Edge AI Intelligence"])
def get_edge_nodes():
    """Return all simulated edge node states, including connectivity, processing counts, and pending queues."""
    return [node.get_state() for node in edge_nodes.values()]


@app.get("/edge/nodes/{node_id}", response_model=EdgeNodeState, tags=["Edge AI Intelligence"])
def get_edge_node(node_id: str):
    """Return runtime state for a specific edge node."""
    node = edge_nodes.get(node_id.strip())
    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Edge node '{node_id}' not found. Registered nodes: {list(edge_nodes.keys())}",
        )
    return node.get_state()


@app.post("/edge/nodes/{node_id}/readings", tags=["Edge AI Intelligence"])
async def process_edge_reading(node_id: str, reading: EnvironmentalData):
    """
    Submit and process an environmental reading directly on simulated edge node.
    Executes local anomaly detection, multi-hazard risk assessment, and offline queuing.
    """
    node = edge_nodes.get(node_id.strip())
    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Edge node '{node_id}' not found.",
        )
    reading_dict = reading.model_dump()
    result = node.process_reading(reading_dict)

    # Broadcast event via WebSocket
    await ws_manager.broadcast_json({
        "event": "edge_reading_processed",
        "node_id": node.node_id,
        "is_online": node.is_online,
        "anomalies_count": result["anomalies_detected_count"],
        "alerts_emitted_count": len(result["emitted_alerts"]),
    })

    return result


@app.post("/edge/nodes/{node_id}/connectivity", response_model=EdgeNodeState, tags=["Edge AI Intelligence"])
async def toggle_edge_connectivity(node_id: str, request: EdgeConnectivityRequest):
    """
    Toggle simulated network connectivity for edge node.
    When set to offline (is_online=false), node continues local processing and queues alerts.
    """
    node = edge_nodes.get(node_id.strip())
    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Edge node '{node_id}' not found.",
        )
    node.set_connectivity(request.is_online)

    await ws_manager.broadcast_json({
        "event": "edge_connectivity_changed",
        "node_id": node.node_id,
        "is_online": node.is_online,
    })

    return node.get_state()


@app.post("/edge/nodes/{node_id}/sync", response_model=EdgeSyncResponse, tags=["Edge AI Intelligence"])
async def sync_edge_node_alerts(node_id: str):
    """
    Trigger transmission of pending locally buffered alerts to Central Server (SRV).
    Executes shortest-path Dijkstra routing for each alert, recording delivery stats.
    """
    node = edge_nodes.get(node_id.strip())
    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Edge node '{node_id}' not found.",
        )
    if not node.is_online:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot sync: Edge node '{node_id}' is currently offline. Enable connectivity first.",
        )

    synced_events = node.sync_pending_alerts()
    pending = node.persistence.get_pending_alerts(sensor_id=node.node_id)

    await ws_manager.broadcast_json({
        "event": "edge_alerts_synced",
        "node_id": node.node_id,
        "synced_count": len(synced_events),
        "remaining_pending": len(pending),
    })

    return EdgeSyncResponse(
        node_id=node.node_id,
        synced_count=len(synced_events),
        remaining_pending=len(pending),
        synced_events=synced_events,
        message=f"Synchronized {len(synced_events)} pending alerts to Central Server SRV.",
    )


@app.post("/edge/sync", tags=["Edge AI Intelligence"])
async def sync_all_edge_alerts():
    """Trigger synchronization for all online edge nodes."""
    results = {}
    for nid, node in edge_nodes.items():
        if node.is_online:
            synced = node.sync_pending_alerts()
            results[nid] = len(synced)
        else:
            results[nid] = 0
    return {
        "status": "success",
        "synced_by_node": results,
        "total_synced": sum(results.values()),
    }


@app.get("/edge/anomalies", response_model=List[AnomalyResult], tags=["Edge AI Intelligence"])
def get_edge_anomalies(node_id: Optional[str] = None):
    """Retrieve the latest detected anomalies across edge nodes."""
    anomalies = []
    if node_id:
        node = edge_nodes.get(node_id.strip())
        if node:
            anomalies.extend(node.latest_anomalies)
    else:
        for node in edge_nodes.values():
            anomalies.extend(node.latest_anomalies)
    return anomalies


@app.get("/edge/risk-assessments", response_model=Dict[str, Dict[str, RiskAssessment]], tags=["Edge AI Intelligence"])
def get_edge_risk_assessments():
    """Retrieve the latest risk assessments grouped by node ID and hazard type."""
    return {nid: node.active_risk_assessments for nid, node in edge_nodes.items()}


@app.get("/edge/alerts", response_model=List[EdgeAlert], tags=["Edge AI Intelligence"])
def get_edge_alerts(
    node_id: Optional[str] = None,
    synced: Optional[bool] = None,
    limit: int = Query(default=50, ge=1, le=100),
):
    """Retrieve environmental alerts from persistent edge queue."""
    all_alerts = []
    if node_id:
        node = edge_nodes.get(node_id.strip())
        if node:
            all_alerts = node.persistence.get_all_alerts(sensor_id=node.node_id, limit=limit)
    else:
        from edge import EdgeQueuePersistence
        p = EdgeQueuePersistence()
        all_alerts = p.get_all_alerts(limit=limit)

    if synced is not None:
        all_alerts = [a for a in all_alerts if a["synced"] == synced]

    return all_alerts[:limit]


@app.get("/edge/config", response_model=EdgeThresholdConfig, tags=["Edge AI Intelligence"])
def get_edge_config():
    """Retrieve active configurable multi-hazard threshold configuration."""
    return DEFAULT_THRESHOLDS


@app.post("/edge/simulate-scenario", tags=["Edge AI Intelligence"])
async def simulate_edge_scenario(request: EdgeScenarioRequest):
    """
    Test helper endpoint: Injects a named multi-hazard test scenario into the edge node.
    """
    nid = request.sensor_id.strip()
    node = edge_nodes.get(nid)
    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Edge node '{nid}' not found.",
        )

    now_iso = datetime.now(timezone.utc).isoformat()
    sc = request.scenario.lower().strip()

    if sc == "flood":
        reading = EnvironmentalData(
            sensor_id=nid,
            location=node.location,
            timestamp=now_iso,
            temperature_celsius=22.5,
            humidity_percentage=94.0,
            rainfall_mm=55.0,
            water_level_m=11.2,
            water_level_rise_rate_m_h=1.35,
            notes="Simulated Flash Flood Surge Scenario",
        )
    elif sc in ("fire", "forest_fire"):
        reading = EnvironmentalData(
            sensor_id=nid,
            location=node.location,
            timestamp=now_iso,
            temperature_celsius=43.5,
            humidity_percentage=16.0,
            smoke_ppm=88.0,
            notes="Simulated Forest Fire Weather Scenario",
        )
    elif sc in ("pollution", "smog", "aqi"):
        reading = EnvironmentalData(
            sensor_id=nid,
            location=node.location,
            timestamp=now_iso,
            temperature_celsius=18.0,
            humidity_percentage=72.0,
            air_quality_aqi=380.0,
            pm25=290.0,
            pm10=435.0,
            notes="Simulated Severe Smog Episode (CPCB Severe)",
        )
    elif sc in ("heat", "extreme_heat"):
        reading = EnvironmentalData(
            sensor_id=nid,
            location=node.location,
            timestamp=now_iso,
            temperature_celsius=46.5,
            humidity_percentage=42.0,
            notes="Simulated Severe IMD Heatwave Scenario",
        )
    elif sc == "landslide":
        reading = EnvironmentalData(
            sensor_id=nid,
            location=node.location,
            timestamp=now_iso,
            temperature_celsius=20.5,
            humidity_percentage=95.0,
            rainfall_mm=62.0,
            soil_moisture_percentage=89.0,
            vibration_g=0.088,
            notes="Simulated Slope Failure Precursor Scenario",
        )
    elif sc in ("gas", "gas_leak"):
        reading = EnvironmentalData(
            sensor_id=nid,
            location=node.location,
            timestamp=now_iso,
            temperature_celsius=32.0,
            humidity_percentage=55.0,
            gas_concentration_ppm=165.0,
            notes="Simulated Industrial Gas Leakage Scenario",
        )
    elif sc in ("water", "water_quality"):
        reading = EnvironmentalData(
            sensor_id=nid,
            location=node.location,
            timestamp=now_iso,
            temperature_celsius=24.0,
            humidity_percentage=60.0,
            ph=4.6,
            turbidity_ntu=52.0,
            dissolved_oxygen_mg_l=2.1,
            notes="Simulated Surface Water Contamination Scenario",
        )
    else:  # normal
        reading = EnvironmentalData(
            sensor_id=nid,
            location=node.location,
            timestamp=now_iso,
            temperature_celsius=26.4,
            humidity_percentage=58.0,
            air_quality_aqi=45.0,
            rainfall_mm=0.0,
            water_level_m=2.2,
            water_level_rise_rate_m_h=0.01,
            smoke_ppm=3.5,
            pm25=28.0,
            pm10=55.0,
            soil_moisture_percentage=32.0,
            vibration_g=0.004,
            gas_concentration_ppm=12.0,
            ph=7.3,
            turbidity_ntu=3.2,
            dissolved_oxygen_mg_l=7.2,
            notes="Simulated Nominal Indian Environmental Baseline",
        )

    res = node.process_reading(reading.model_dump())

    await ws_manager.broadcast_json({
        "event": "edge_scenario_injected",
        "node_id": nid,
        "scenario": sc,
        "anomalies_count": res["anomalies_detected_count"],
        "alerts_count": len(res["emitted_alerts"]),
    })

    return {
        "scenario": sc,
        "node_id": nid,
        "reading": reading.model_dump(),
        "processing_result": res,
    }


@app.post("/edge/reset", response_model=MessageResponse, tags=["Edge AI Intelligence"])
def reset_edge_nodes():
    """Reset edge nodes history, persistent queue, and lifecycle state."""
    for node in edge_nodes.values():
        node.detector.reset_history()
        node.persistence.clear()
        node._hazard_lifecycle.clear()
        node.readings_processed = 0
        node.last_processed_at = None
        node.latest_measurements = None
        node.latest_anomalies.clear()
        node.active_risk_assessments.clear()
        node.is_online = True
    return MessageResponse(
        message="Edge AI nodes and alert queues reset successfully.",
        success=True,
    )


# --- WebSocket Endpoint ---

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Basic WebSocket endpoint for real-time packet progress and monitoring updates.
    Accepts client connection and handles disconnection safely.
    """
    await ws_manager.connect(websocket)
    try:
        # Send initial welcome confirmation
        await websocket.send_json({
            "event": "connected",
            "message": "Connected to Network Monitoring WebSocket channel.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        # Keep connection open and safely handle incoming client pings
        while True:
            data = await websocket.receive_text()
            # Echo or acknowledge client heartbeat
            await websocket.send_json({
                "event": "echo",
                "received": data,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
        logger.info("Client cleanly disconnected from WebSocket.")
    except Exception as e:
        logger.warning(f"WebSocket session terminated: {e}")
        ws_manager.disconnect(websocket)
