"""
Automated tests for Network Monitoring and Intelligent Routing System Backend.
Uses FastAPI TestClient to test all REST endpoints, Dijkstra routing algorithm,
failure cases, metrics calculations, and WebSocket connectivity.
"""

import pytest
from fastapi.testclient import TestClient
from main import app, virtual_network, packet_simulator
from models import NodeStatus, LinkStatus, PacketStatus


@pytest.fixture(autouse=True)
def reset_system_state():
    """Ensure a clean virtual network topology and empty packet history before each test."""
    virtual_network.reset()
    packet_simulator.reset()
    yield
    virtual_network.reset()
    packet_simulator.reset()


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    return TestClient(app)


# --- 1. General & Health Endpoints ---

def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert "Network Monitoring" in data["project"]
    assert "docs_url" in data


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["total_nodes"] == 7
    assert data["total_links"] == 10
    assert data["active_nodes"] == 7
    assert data["active_links"] == 10


# --- 2. Network Topology & Sensors Endpoints ---

def test_get_network_topology(client):
    response = client.get("/network")
    assert response.status_code == 200
    data = response.json()
    assert len(data["nodes"]) == 7
    assert len(data["links"]) == 10
    assert data["active_nodes_count"] == 7
    assert data["active_links_count"] == 10

    node_ids = [n["id"] for n in data["nodes"]]
    for expected_id in ["S1", "S2", "R1", "R2", "R3", "G1", "SRV"]:
        assert expected_id in node_ids


def test_get_sensors(client):
    response = client.get("/sensors")
    assert response.status_code == 200
    sensors = response.json()
    sensor_ids = [s["id"] for s in sensors]
    assert len(sensors) == 2
    assert "S1" in sensor_ids
    assert "S2" in sensor_ids
    for s in sensors:
        assert s["type"] == "sensor"


# --- 3. Dijkstra Shortest-Path Routing Endpoints ---

def test_dijkstra_routing_s1_to_srv(client):
    """
    Test S1 -> SRV.
    Topology:
      Path A: S1 -> R1 -> G1 -> SRV: cost = 3 + 8 + 1 = 12
      Path B: S1 -> R1 -> R2 -> G1 -> SRV: cost = 3 + 2 + 3 + 1 = 9  (Lowest cost!)
      Path C: S1 -> R2 -> G1 -> SRV: cost = 7 + 3 + 1 = 11
    Dijkstra must select Path B: ['S1', 'R1', 'R2', 'G1', 'SRV'].
    Delay = 6 + 4 + 8 + 2 = 20.0 ms.
    Hops = 4.
    """
    response = client.get("/route?source=S1&destination=SRV")
    assert response.status_code == 200
    data = response.json()

    assert data["source"] == "S1"
    assert data["destination"] == "SRV"
    assert data["route"] == ["S1", "R1", "R2", "G1", "SRV"]
    assert data["total_cost"] == 9.0
    assert data["hop_count"] == 4
    assert data["estimated_latency_ms"] == 20.0
    assert len(data["path_details"]) == 4


def test_dijkstra_routing_s2_to_srv(client):
    """
    Test S2 -> SRV.
    Topology:
      Path A: S2 -> R3 -> G1 -> SRV: cost = 2 + 4 + 1 = 7  (Lowest cost!)
      Path B: S2 -> R2 -> G1 -> SRV: cost = 4 + 3 + 1 = 8
    Dijkstra must select Path A: ['S2', 'R3', 'G1', 'SRV'].
    Delay = 5 + 9 + 2 = 16.0 ms.
    Hops = 3.
    """
    response = client.get("/route?source=S2&destination=SRV")
    assert response.status_code == 200
    data = response.json()

    assert data["source"] == "S2"
    assert data["destination"] == "SRV"
    assert data["route"] == ["S2", "R3", "G1", "SRV"]
    assert data["total_cost"] == 7.0
    assert data["hop_count"] == 3
    assert data["estimated_latency_ms"] == 16.0


def test_dijkstra_reroutes_on_node_failure(client):
    """
    When R2 is inactive:
    Path B (through R2) is unavailable.
    Dijkstra must select Path A: ['S1', 'R1', 'G1', 'SRV'].
    Cost = 3 + 8 + 1 = 12.0.
    Delay = 6 + 18 + 2 = 26.0 ms.
    """
    # Deactivate R2
    client.patch("/network/nodes/R2/status", json={"status": "inactive"})

    response = client.get("/route?source=S1&destination=SRV")
    assert response.status_code == 200
    data = response.json()

    assert data["route"] == ["S1", "R1", "G1", "SRV"]
    assert data["total_cost"] == 12.0
    assert data["hop_count"] == 3
    assert data["estimated_latency_ms"] == 26.0


def test_dijkstra_disconnected_destination(client):
    """
    When G1 is inactive, SRV is completely disconnected.
    GET /route should return HTTP 400 with a clear error message.
    """
    client.patch("/network/nodes/G1/status", json={"status": "inactive"})

    response = client.get("/route?source=S1&destination=SRV")
    assert response.status_code == 400
    data = response.json()
    assert "unreachable" in data["message"].lower() or "inactive" in data["message"].lower()


def test_dijkstra_invalid_node_ids(client):
    # Invalid source
    res1 = client.get("/route?source=INVALID_NODE&destination=SRV")
    assert res1.status_code == 404
    assert "INVALID_NODE" in res1.json()["message"]

    # Invalid destination
    res2 = client.get("/route?source=S1&destination=UNKNOWN_NODE")
    assert res2.status_code == 404
    assert "UNKNOWN_NODE" in res2.json()["message"]


def test_dijkstra_same_source_and_destination(client):
    response = client.get("/route?source=S1&destination=S1")
    assert response.status_code == 200
    data = response.json()
    assert data["route"] == ["S1"]
    assert data["total_cost"] == 0.0
    assert data["hop_count"] == 0
    assert data["estimated_latency_ms"] == 0.0


# --- 4. Packet Simulation Endpoints ---

def test_simulate_packet_default_payload(client):
    response = client.post("/simulate", json={"source": "S1", "destination": "SRV"})
    assert response.status_code == 200
    data = response.json()

    assert data["packet_id"].startswith("PKT-")
    assert data["source"] == "S1"
    assert data["destination"] == "SRV"
    assert data["status"] == "DELIVERED"
    assert data["route"] == ["S1", "R1", "R2", "G1", "SRV"]
    assert data["total_cost"] == 9.0
    assert data["hop_count"] == 4
    assert data["estimated_latency_ms"] == 20.0
    assert data["failure_reason"] is None

    # Verify generated payload
    payload = data["payload"]
    assert payload["sensor_id"] == "S1"
    assert "temperature_celsius" in payload
    assert "humidity_percentage" in payload
    assert payload["is_simulated"] is True


def test_simulate_packet_custom_payload(client):
    custom_payload = {
        "sensor_id": "S1",
        "timestamp": "2026-10-12T12:00:00Z",
        "temperature_celsius": 28.5,
        "humidity_percentage": 65.0,
        "air_quality_aqi": 42.0,
        "is_simulated": True,
        "notes": "Custom lab test payload",
    }

    response = client.post(
        "/simulate",
        json={"source": "S1", "destination": "SRV", "payload": custom_payload},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "DELIVERED"
    assert data["payload"]["temperature_celsius"] == 28.5
    assert data["payload"]["air_quality_aqi"] == 42.0


def test_simulate_packet_failure_when_unreachable(client):
    # Disable gateway G1
    client.patch("/network/nodes/G1/status", json={"status": "inactive"})

    response = client.post("/simulate", json={"source": "S1", "destination": "SRV"})
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "FAILED"
    assert data["route"] == []
    assert data["failure_reason"] is not None


def test_simulate_invalid_source_or_destination(client):
    res1 = client.post("/simulate", json={"source": "NONEXISTENT", "destination": "SRV"})
    assert res1.status_code == 404

    res2 = client.post("/simulate", json={"source": "S1", "destination": "NONEXISTENT"})
    assert res2.status_code == 404


# --- 5. Packet History & Metrics Endpoints ---

def test_metrics_with_zero_packets(client):
    response = client.get("/metrics")
    assert response.status_code == 200
    data = response.json()

    assert data["total_packets"] == 0
    assert data["delivered_packets"] == 0
    assert data["failed_packets"] == 0
    assert data["delivery_ratio_percentage"] == 0.0
    assert data["average_latency_ms"] == 0.0
    assert data["average_hop_count"] == 0.0


def test_metrics_calculation_accuracy(client):
    # Simulate 2 successful packets
    client.post("/simulate", json={"source": "S1", "destination": "SRV"})  # latency 20.0, hops 4
    client.post("/simulate", json={"source": "S2", "destination": "SRV"})  # latency 16.0, hops 3

    # Cause a failure and simulate 1 failed packet
    client.patch("/network/nodes/G1/status", json={"status": "inactive"})
    client.post("/simulate", json={"source": "S1", "destination": "SRV"})

    metrics_res = client.get("/metrics")
    assert metrics_res.status_code == 200
    metrics = metrics_res.json()

    assert metrics["total_packets"] == 3
    assert metrics["delivered_packets"] == 2
    assert metrics["failed_packets"] == 1
    # 2/3 = 66.67%
    assert metrics["delivery_ratio_percentage"] == 66.67
    # (20.0 + 16.0) / 2 = 18.0 ms
    assert metrics["average_latency_ms"] == 18.0
    # (4 + 3) / 2 = 3.5 hops
    assert metrics["average_hop_count"] == 3.5


def test_get_packets_history(client):
    for _ in range(5):
        client.post("/simulate", json={"source": "S1", "destination": "SRV"})

    response = client.get("/packets?limit=3")
    assert response.status_code == 200
    packets = response.json()
    assert len(packets) == 3


def test_reset_simulation_history(client):
    # Create some packets
    client.post("/simulate", json={"source": "S1", "destination": "SRV"})
    client.post("/simulate", json={"source": "S2", "destination": "SRV"})

    # Verify packets exist
    assert len(client.get("/packets").json()) == 2

    # Reset
    reset_res = client.post("/reset")
    assert reset_res.status_code == 200
    assert reset_res.json()["success"] is True

    # Packets and metrics should be clean
    assert len(client.get("/packets").json()) == 0
    metrics = client.get("/metrics").json()
    assert metrics["total_packets"] == 0

    # Network topology remains intact
    topo = client.get("/network").json()
    assert len(topo["nodes"]) == 7


# --- 6. WebSocket Connectivity ---

def test_websocket_connection(client):
    with client.websocket_connect("/ws") as websocket:
        # Initial greeting from server
        data = websocket.receive_json()
        assert data["event"] == "connected"

        # Client ping
        websocket.send_text("ping")
        response = websocket.receive_json()
        assert response["event"] == "echo"
        assert response["received"] == "ping"
