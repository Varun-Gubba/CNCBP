"""
Data models and Pydantic schemas for Network Monitoring and Intelligent Routing System.
Provides structured request and response validation for network nodes, links,
environmental payloads, packets, and metrics.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class NodeType(str, Enum):
    SENSOR = "sensor"
    ROUTER = "router"
    GATEWAY = "gateway"
    SERVER = "server"


class NodeStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class LinkStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class PacketStatus(str, Enum):
    CREATED = "CREATED"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"


# --- Network Topology Models ---

class Node(BaseModel):
    id: str = Field(..., description="Unique identifier of the node (e.g., S1, R1, G1, SRV)")
    name: str = Field(..., description="Descriptive name of the node")
    type: NodeType = Field(..., description="Classification of node (sensor, router, gateway, server)")
    status: NodeStatus = Field(default=NodeStatus.ACTIVE, description="Current operational status")

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, v: Any) -> Any:
        if isinstance(v, str):
            v_lower = v.lower()
            if v_lower in ("up", "active", "online"):
                return NodeStatus.ACTIVE
            if v_lower in ("down", "inactive", "offline"):
                return NodeStatus.INACTIVE
        return v


class Link(BaseModel):
    source: str = Field(..., description="Source node ID")
    destination: str = Field(..., description="Destination node ID")
    cost: float = Field(..., ge=0, description="Routing cost/weight used by Dijkstra algorithm")
    delay: float = Field(..., ge=0, description="Estimated one-way delay in milliseconds")
    status: LinkStatus = Field(default=LinkStatus.ACTIVE, description="Link operational status")

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, v: Any) -> Any:
        if isinstance(v, str):
            v_lower = v.lower()
            if v_lower in ("up", "active", "online"):
                return LinkStatus.ACTIVE
            if v_lower in ("down", "inactive", "offline"):
                return LinkStatus.INACTIVE
        return v


class NetworkTopologyResponse(BaseModel):
    nodes: List[Node] = Field(..., description="All network nodes")
    links: List[Link] = Field(..., description="All network links")
    active_nodes_count: int
    active_links_count: int


# --- Environmental Telemetry Models ---

class EnvironmentalData(BaseModel):
    sensor_id: str = Field(..., description="Node ID of the originating sensor")
    timestamp: str = Field(..., description="ISO 8601 timestamp of data generation")
    temperature_celsius: float = Field(..., description="Ambient temperature reading in Celsius")
    humidity_percentage: float = Field(..., ge=0, le=100, description="Relative humidity percentage")
    air_quality_aqi: Optional[float] = Field(default=None, description="Air Quality Index (AQI)")
    is_simulated: bool = Field(default=True, description="Indicates simulated sensor reading")
    notes: Optional[str] = Field(
        default="Simulated environmental reading - not physical sensor measurement",
        description="Disclaimer / context notes"
    )

    # Phase 2 Multi-Hazard Extensions (optional with defaults for backwards-compatibility)
    location: Optional[str] = Field(default=None, description="Physical / simulated Indian monitoring station location")
    rainfall_mm: Optional[float] = Field(default=None, ge=0, description="Rainfall accumulation in mm")
    water_level_m: Optional[float] = Field(default=None, ge=0, description="Current river/reservoir water level in meters")
    water_level_rise_rate_m_h: Optional[float] = Field(default=None, description="Rate of water-level rise in meters/hour")
    smoke_ppm: Optional[float] = Field(default=None, ge=0, description="Smoke/combustion byproducts concentration in ppm")
    pm25: Optional[float] = Field(default=None, ge=0, description="Particulate Matter PM2.5 in µg/m³ (CPCB India NAAQS)")
    pm10: Optional[float] = Field(default=None, ge=0, description="Particulate Matter PM10 in µg/m³ (CPCB India NAAQS)")
    soil_moisture_percentage: Optional[float] = Field(default=None, ge=0, le=100, description="Volumetric soil moisture percentage (0-100%)")
    vibration_g: Optional[float] = Field(default=None, ge=0, description="Ground acceleration/vibration amplitude in g")
    gas_concentration_ppm: Optional[float] = Field(default=None, ge=0, description="Toxic or combustible industrial gas level in ppm")
    ph: Optional[float] = Field(default=None, ge=0, le=14, description="Water pH level (0-14)")
    turbidity_ntu: Optional[float] = Field(default=None, ge=0, description="Water turbidity in NTU")
    dissolved_oxygen_mg_l: Optional[float] = Field(default=None, ge=0, description="Dissolved oxygen in mg/L")


# --- Routing Models ---

class RouteStepDetail(BaseModel):
    hop_number: int
    from_node: str
    to_node: str
    link_cost: float
    link_delay_ms: float


class RouteResponse(BaseModel):
    source: str
    destination: str
    route: List[str] = Field(..., description="Ordered list of node IDs forming shortest path")
    total_cost: float = Field(..., description="Total accumulated Dijkstra weight/cost")
    hop_count: int = Field(..., description="Number of network hops (nodes traversed - 1)")
    estimated_latency_ms: float = Field(..., description="Sum of physical link delays in ms")
    path_details: List[RouteStepDetail] = Field(default_factory=list, description="Breakdown of each hop")


# --- Packet Models ---

class SimulateRequest(BaseModel):
    source: str = Field(default="S1", description="Source sensor or node ID")
    destination: str = Field(default="SRV", description="Target destination node ID")
    payload: Optional[EnvironmentalData] = Field(
        default=None,
        description="Optional custom telemetry payload. If omitted, one is generated automatically."
    )


class Packet(BaseModel):
    packet_id: str = Field(..., description="Unique packet tracking ID")
    source: str = Field(..., description="Originating node ID")
    destination: str = Field(..., description="Target node ID")
    payload: EnvironmentalData = Field(..., description="Environmental telemetry payload")
    created_at: str = Field(..., description="Timestamp of packet creation")
    route: List[str] = Field(default_factory=list, description="Path traversed by packet")
    status: PacketStatus = Field(..., description="Current packet delivery state")
    hop_count: int = Field(default=0, description="Hops traversed")
    total_cost: float = Field(default=0.0, description="Accumulated route cost")
    estimated_latency_ms: float = Field(default=0.0, description="Accumulated link delay in ms")
    failure_reason: Optional[str] = Field(default=None, description="Explanation if status is FAILED")


# --- Metrics Models ---

class MetricsResponse(BaseModel):
    total_packets: int = Field(..., description="Total packets simulated")
    delivered_packets: int = Field(..., description="Packets successfully reached destination")
    failed_packets: int = Field(..., description="Packets that failed due to unreachable route or inactive node")
    delivery_ratio_percentage: float = Field(..., description="Delivered / Total * 100")
    average_latency_ms: float = Field(..., description="Average latency of delivered packets")
    average_hop_count: float = Field(..., description="Average hops of delivered packets")


# --- System Status and Management Models ---

class RootResponse(BaseModel):
    project: str
    status: str
    version: str
    message: str
    docs_url: str


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    active_nodes: int
    total_nodes: int
    active_links: int
    total_links: int


class MessageResponse(BaseModel):
    message: str
    success: bool = True


class UpdateNodeStatusRequest(BaseModel):
    status: NodeStatus


class UpdateLinkStatusRequest(BaseModel):
    source: str
    destination: str
    status: LinkStatus


# --- Phase 2: Edge AI and Environmental Hazard Models ---

class HazardType(str, Enum):
    FLOOD = "FLOOD"
    FOREST_FIRE = "FOREST_FIRE"
    AIR_POLLUTION = "AIR_POLLUTION"
    EXTREME_HEAT = "EXTREME_HEAT"
    LANDSLIDE_PRECURSOR = "LANDSLIDE_PRECURSOR"
    INDUSTRIAL_GAS = "INDUSTRIAL_GAS"
    WATER_QUALITY = "WATER_QUALITY"


class SeverityLevel(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertLifecycle(str, Enum):
    NEW = "NEW"
    CONTINUING = "CONTINUING"
    WORSENING = "WORSENING"
    RESOLVED = "RESOLVED"


class AnomalyResult(BaseModel):
    anomaly_id: str
    sensor_id: str
    metric: str
    observed_value: float
    expected_range: Optional[Dict[str, Optional[float]]] = None
    anomaly_score: float = Field(..., ge=0.0, le=100.0)
    is_anomaly: bool
    detection_method: str
    explanation: str
    timestamp: str


class RiskAssessment(BaseModel):
    hazard_type: HazardType
    sensor_id: str
    location: str
    risk_score: float = Field(..., ge=0.0, le=100.0)
    severity: SeverityLevel
    confidence_score: float = Field(..., ge=0.0, le=100.0)
    detected_anomalies: List[str]
    contributing_measurements: Dict[str, Any]
    explanation: str
    recommended_action: str
    timestamp: str
    detection_method: str
    processing_location: str = "EDGE"


class EdgeAlert(BaseModel):
    event_id: str
    sensor_id: str
    location: str
    hazard_type: HazardType
    severity: SeverityLevel
    risk_score: float
    confidence_score: float
    lifecycle_state: AlertLifecycle
    detected_anomalies: List[str]
    contributing_measurements: Dict[str, Any]
    explanation: str
    recommended_action: str
    created_at: str
    synced: bool = False
    synced_at: Optional[str] = None
    delivery_attempts: int = 0
    route_used: Optional[List[str]] = None
    packet_id: Optional[str] = None
    delivery_status: Optional[str] = None  # DELIVERED, QUEUED, FAILED


class EdgeNodeState(BaseModel):
    node_id: str
    location: str
    is_online: bool
    readings_processed: int
    last_processed_at: Optional[str] = None
    latest_measurements: Optional[Dict[str, Any]] = None
    active_risk_assessments: Dict[str, RiskAssessment] = Field(default_factory=dict)
    pending_alerts_count: int = 0
    synced_alerts_count: int = 0
    total_alerts_count: int = 0


class EdgeConnectivityRequest(BaseModel):
    is_online: bool


class EdgeSyncResponse(BaseModel):
    node_id: str
    synced_count: int
    remaining_pending: int
    synced_events: List[str]
    message: str


class EdgeScenarioRequest(BaseModel):
    scenario: str = Field(
        ...,
        description="Named test scenario (e.g. normal, flood, fire, pollution, heat, landslide, gas, water)"
    )
    sensor_id: str = Field(default="S1", description="Target edge sensor node")

