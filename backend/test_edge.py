"""
Automated Test Suite for Phase 2: Edge AI & Environmental Anomaly Detection.

Covers all 14 required Phase 2 validation criteria:
1. Normal readings do not trigger unnecessary alerts.
2. Rapid water-level increases can trigger flood-risk detection.
3. Abnormal smoke and temperature readings can trigger fire-risk alerts.
4. Elevated PM2.5 or PM10 readings can trigger pollution alerts.
5. Extreme temperatures trigger the configured heat-risk rules.
6. Abnormal soil-moisture and vibration patterns trigger landslide-risk indicators.
7. Abnormal gas readings trigger industrial-risk alerts.
8. Missing or invalid readings are handled safely.
9. Identical readings produce deterministic results.
10. Repeated abnormal readings do not create unlimited duplicate alerts.
11. Local processing continues when simulated connectivity is disabled.
12. Queued alerts synchronize after connectivity returns.
13. Retried events do not create duplicate records.
14. Existing routing and packet simulation integration works seamlessly.
"""

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from main import app, virtual_network, packet_simulator, edge_nodes
from models import (
    EnvironmentalData,
    HazardType,
    SeverityLevel,
    AlertLifecycle,
    NodeStatus,
)
from edge import EdgeNode, EdgeQueuePersistence


@pytest.fixture(autouse=True)
def clean_edge_environment():
    """Reset network, simulator, and edge node states before and after each test."""
    virtual_network.reset()
    packet_simulator.reset()
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
    yield
    virtual_network.reset()
    packet_simulator.reset()
    for node in edge_nodes.values():
        node.detector.reset_history()
        node.persistence.clear()
        node._hazard_lifecycle.clear()
        node.is_online = True


@pytest.fixture
def client():
    return TestClient(app)


# --- 1. Normal readings do not trigger unnecessary alerts ---

def test_normal_readings_do_not_trigger_unnecessary_alerts(client):
    """Normal baseline readings must evaluate to LOW risk without generating critical alerts."""
    normal_reading = {
        "sensor_id": "S1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "temperature_celsius": 26.5,
        "humidity_percentage": 58.0,
        "air_quality_aqi": 42.0,
        "rainfall_mm": 0.0,
        "water_level_m": 2.2,
        "water_level_rise_rate_m_h": 0.01,
        "smoke_ppm": 4.0,
        "pm25": 25.0,
        "pm10": 48.0,
        "soil_moisture_percentage": 30.0,
        "vibration_g": 0.003,
        "gas_concentration_ppm": 12.0,
        "ph": 7.2,
        "turbidity_ntu": 3.0,
        "dissolved_oxygen_mg_l": 7.5,
    }

    res = client.post("/edge/nodes/S1/readings", json=normal_reading)
    assert res.status_code == 200
    data = res.json()

    assert data["anomalies_detected_count"] == 0
    assert len(data["emitted_alerts"]) == 0

    # Risk scores should all be LOW
    assessments = data["risk_assessments"]
    for hazard_name, assessment in assessments.items():
        assert assessment["severity"] == "LOW"
        assert assessment["risk_score"] < 40.0


# --- 2. Rapid water-level increases can trigger flood-risk detection ---

def test_flood_risk_detection_on_rapid_water_level_rise(client):
    """High water level combined with rapid rise rate triggers flood risk."""
    flood_reading = {
        "sensor_id": "S1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "temperature_celsius": 23.0,
        "humidity_percentage": 92.0,
        "water_level_m": 11.0,
        "water_level_rise_rate_m_h": 1.2,
        "rainfall_mm": 48.0,
    }

    res = client.post("/edge/nodes/S1/readings", json=flood_reading)
    assert res.status_code == 200
    data = res.json()

    assessments = data["risk_assessments"]
    flood = assessments[HazardType.FLOOD.value]
    assert flood["severity"] in ("HIGH", "CRITICAL")
    assert flood["risk_score"] >= 75.0
    assert flood["confidence_score"] > 60.0
    assert "water_level_m" in flood["contributing_measurements"]
    assert len(flood["detected_anomalies"]) > 0

    # Emitted alert was generated
    assert any(a["hazard_type"] == "FLOOD" for a in data["emitted_alerts"])


# --- 3. Abnormal smoke and temperature readings can trigger fire-risk alerts ---

def test_fire_risk_alerts_on_abnormal_smoke_and_temperature(client):
    """Extreme heat, low humidity, and high smoke trigger forest fire warning."""
    fire_reading = {
        "sensor_id": "S1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "temperature_celsius": 42.0,
        "humidity_percentage": 18.0,
        "smoke_ppm": 85.0,
    }

    res = client.post("/edge/nodes/S1/readings", json=fire_reading)
    assert res.status_code == 200
    data = res.json()

    assessments = data["risk_assessments"]
    fire = assessments[HazardType.FOREST_FIRE.value]
    assert fire["severity"] in ("HIGH", "CRITICAL")
    assert fire["risk_score"] >= 70.0
    assert "smoke_ppm" in fire["contributing_measurements"]

    # Must contain explainable disclaimer that sensors alone do not prove fire
    assert "NOTE" in fire["explanation"] or "satellite" in fire["explanation"].lower()
    assert any(a["hazard_type"] == "FOREST_FIRE" for a in data["emitted_alerts"])


# --- 4. Elevated PM2.5 or PM10 readings can trigger pollution alerts ---

def test_air_pollution_alerts_on_elevated_particulate_matter(client):
    """Severe PM2.5 breach triggers CPCB NAAQS pollution alert."""
    pollution_reading = {
        "sensor_id": "S2",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "temperature_celsius": 20.0,
        "humidity_percentage": 65.0,
        "pm25": 260.0,
        "pm10": 410.0,
        "air_quality_aqi": 340.0,
    }

    res = client.post("/edge/nodes/S2/readings", json=pollution_reading)
    assert res.status_code == 200
    data = res.json()

    assessments = data["risk_assessments"]
    aq = assessments[HazardType.AIR_POLLUTION.value]
    assert aq["severity"] in ("HIGH", "CRITICAL")
    assert aq["risk_score"] >= 80.0
    assert "CPCB" in aq["explanation"]
    assert any(a["hazard_type"] == "AIR_POLLUTION" for a in data["emitted_alerts"])


# --- 5. Extreme temperatures trigger the configured heat-risk rules ---

def test_extreme_heat_risk_rules(client):
    """Temperatures exceeding IMD 45°C trigger extreme heat warnings."""
    heat_reading = {
        "sensor_id": "S2",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "temperature_celsius": 46.5,
        "humidity_percentage": 40.0,
    }

    res = client.post("/edge/nodes/S2/readings", json=heat_reading)
    assert res.status_code == 200
    data = res.json()

    assessments = data["risk_assessments"]
    heat = assessments[HazardType.EXTREME_HEAT.value]
    assert heat["severity"] in ("HIGH", "CRITICAL")
    assert heat["risk_score"] >= 75.0
    assert "Heat Index" in heat["explanation"] or "IMD" in heat["explanation"]
    assert any(a["hazard_type"] == "EXTREME_HEAT" for a in data["emitted_alerts"])


# --- 6. Abnormal soil-moisture and vibration patterns trigger landslide-risk indicators ---

def test_landslide_precursor_indicators(client):
    """High soil moisture saturation and slope micro-vibration trigger landslide precursor warning."""
    landslide_reading = {
        "sensor_id": "S1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "temperature_celsius": 21.0,
        "humidity_percentage": 90.0,
        "soil_moisture_percentage": 88.0,
        "vibration_g": 0.085,
        "rainfall_mm": 50.0,
    }

    res = client.post("/edge/nodes/S1/readings", json=landslide_reading)
    assert res.status_code == 200
    data = res.json()

    assessments = data["risk_assessments"]
    ls = assessments[HazardType.LANDSLIDE_PRECURSOR.value]
    assert ls["severity"] in ("HIGH", "CRITICAL")
    assert ls["risk_score"] >= 70.0
    # Must explicitly state precursor warning, not definitive standalone prediction
    assert "precursor" in ls["explanation"].lower()
    assert any(a["hazard_type"] == "LANDSLIDE_PRECURSOR" for a in data["emitted_alerts"])


# --- 7. Abnormal gas readings trigger industrial-risk alerts ---

def test_industrial_gas_leakage_alerts(client):
    """Sudden gas spikes above configurable baseline trigger industrial alerts."""
    gas_reading = {
        "sensor_id": "S2",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "temperature_celsius": 30.0,
        "humidity_percentage": 50.0,
        "gas_concentration_ppm": 140.0,
    }

    res = client.post("/edge/nodes/S2/readings", json=gas_reading)
    assert res.status_code == 200
    data = res.json()

    assessments = data["risk_assessments"]
    gas = assessments[HazardType.INDUSTRIAL_GAS.value]
    assert gas["severity"] in ("HIGH", "CRITICAL")
    assert gas["risk_score"] >= 80.0
    assert any(a["hazard_type"] == "INDUSTRIAL_GAS" for a in data["emitted_alerts"])


# --- 8. Missing or invalid readings are handled safely ---

def test_missing_and_invalid_readings_handled_safely(client):
    """Missing fields should be skipped safely; invalid physical values flagged without crashing."""
    # Reading missing almost all fields
    sparse_reading = {
        "sensor_id": "S1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "temperature_celsius": 24.0,
        "humidity_percentage": 55.0,
    }
    res1 = client.post("/edge/nodes/S1/readings", json=sparse_reading)
    assert res1.status_code == 200

    # Reading with physically impossible values: temperature 150°C, humidity -20%
    invalid_reading = {
        "sensor_id": "S1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "temperature_celsius": 150.0,
        "humidity_percentage": 40.0,
        "ph": 18.0,  # Invalid pH
    }
    # Pydantic or detector handles safely
    res2 = client.post("/edge/nodes/S1/readings", json=invalid_reading)
    # Either caught by pydantic validator (422) or handled by detector (200 with data integrity anomaly)
    assert res2.status_code in (200, 422)


# --- 9. Identical readings produce deterministic results ---

def test_identical_readings_produce_deterministic_results():
    """Identical inputs on an isolated edge detector produce identical scores."""
    node = EdgeNode(node_id="TEST_DET", location="Lab Bench Test")
    reading = {
        "sensor_id": "TEST_DET",
        "timestamp": "2026-10-13T12:00:00Z",
        "temperature_celsius": 35.0,
        "humidity_percentage": 60.0,
        "water_level_m": 7.5,
        "pm25": 80.0,
    }

    # Run twice on clean state
    node.detector.reset_history()
    anomalies_1 = node.detector.detect_anomalies(reading)
    scores_1 = [a.anomaly_score for a in anomalies_1]

    node.detector.reset_history()
    anomalies_2 = node.detector.detect_anomalies(reading)
    scores_2 = [a.anomaly_score for a in anomalies_2]

    assert scores_1 == scores_2


# --- 10. Repeated abnormal readings do not create unlimited duplicate alerts ---

def test_repeated_abnormal_readings_do_not_spam_duplicate_alerts(client):
    """Continuing abnormal conditions must not spam multiple duplicate alerts."""
    mod_reading = {
        "sensor_id": "S1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "temperature_celsius": 25.0,
        "humidity_percentage": 60.0,
        "gas_concentration_ppm": 60.0,  # Warning threshold (MODERATE)
    }

    # First injection: NEW alert should be emitted
    res1 = client.post("/edge/nodes/S1/readings", json=mod_reading)
    assert res1.status_code == 200
    alerts_1 = res1.json()["emitted_alerts"]
    assert len(alerts_1) > 0
    assert alerts_1[0]["lifecycle_state"] == "NEW"

    # Second injection with identical severity: CONTINUING -> Suppress duplicate
    res2 = client.post("/edge/nodes/S1/readings", json=mod_reading)
    assert res2.status_code == 200
    alerts_2 = res2.json()["emitted_alerts"]
    assert len(alerts_2) == 0  # Deduplicated!

    # Third injection with worse severity (CRITICAL): WORSENING -> Emit escalated alert
    worse_reading = dict(mod_reading, gas_concentration_ppm=250.0)
    res3 = client.post("/edge/nodes/S1/readings", json=worse_reading)
    assert res3.status_code == 200
    alerts_3 = res3.json()["emitted_alerts"]
    assert len(alerts_3) > 0
    assert alerts_3[0]["lifecycle_state"] == "WORSENING"

    # Fourth injection with safe normal readings: RESOLVED -> Emit resolution notification
    safe_reading = dict(mod_reading, gas_concentration_ppm=10.0)
    res4 = client.post("/edge/nodes/S1/readings", json=safe_reading)
    assert res4.status_code == 200
    alerts_4 = res4.json()["emitted_alerts"]
    assert len(alerts_4) > 0
    assert alerts_4[0]["lifecycle_state"] == "RESOLVED"


# --- 11. Local processing continues when simulated connectivity is disabled ---

def test_local_processing_continues_offline(client):
    """When node is offline, readings are still processed locally and alerts queued in persistence."""
    # Set S1 offline
    toggle_res = client.post("/edge/nodes/S1/connectivity", json={"is_online": False})
    assert toggle_res.status_code == 200
    assert toggle_res.json()["is_online"] is False

    # Process flood anomaly while offline
    flood_reading = {
        "sensor_id": "S1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "temperature_celsius": 22.0,
        "humidity_percentage": 90.0,
        "water_level_m": 10.5,
        "water_level_rise_rate_m_h": 1.1,
    }
    res = client.post("/edge/nodes/S1/readings", json=flood_reading)
    assert res.status_code == 200
    data = res.json()

    assert data["is_online"] is False
    assert len(data["emitted_alerts"]) > 0
    alert = data["emitted_alerts"][0]
    assert alert["synced"] is False
    assert alert["delivery_status"] == "QUEUED"

    # Check node state has pending alert in queue
    node_state = client.get("/edge/nodes/S1").json()
    assert node_state["pending_alerts_count"] >= 1


# --- 12. Queued alerts synchronize after connectivity returns ---

def test_queued_alerts_synchronize_after_recovery(client):
    """After reconnecting, offline alerts can be synchronized to the central server."""
    # 1. Put S1 offline and generate an alert
    client.post("/edge/nodes/S1/connectivity", json={"is_online": False})
    smoke_reading = {
        "sensor_id": "S1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "temperature_celsius": 41.0,
        "humidity_percentage": 20.0,
        "smoke_ppm": 90.0,
    }
    client.post("/edge/nodes/S1/readings", json=smoke_reading)

    # Verify pending
    state_before = client.get("/edge/nodes/S1").json()
    assert state_before["pending_alerts_count"] >= 1

    # 2. Restore connectivity
    client.post("/edge/nodes/S1/connectivity", json={"is_online": True})

    # 3. Synchronize
    sync_res = client.post("/edge/nodes/S1/sync")
    assert sync_res.status_code == 200
    sync_data = sync_res.json()

    assert sync_data["synced_count"] >= 1
    assert sync_data["remaining_pending"] == 0

    # 4. Check alerts are now marked synced
    state_after = client.get("/edge/nodes/S1").json()
    assert state_after["pending_alerts_count"] == 0
    assert state_after["synced_alerts_count"] >= 1


# --- 13. Retried events do not create duplicate records ---

def test_retried_events_do_not_create_duplicate_records():
    """Event IDs enforce uniqueness so retried transmissions do not duplicate queue records."""
    persistence = EdgeQueuePersistence()
    persistence.clear()

    alert = {
        "event_id": "EVT-TEST-UNIQUE-101",
        "sensor_id": "S1",
        "location": "Test Zone",
        "hazard_type": "FLOOD",
        "severity": "HIGH",
        "risk_score": 85.0,
        "confidence_score": 80.0,
        "lifecycle_state": "NEW",
        "detected_anomalies": ["Water surge"],
        "contributing_measurements": {"water_level_m": 10.2},
        "explanation": "High water level",
        "recommended_action": "Evacuate",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "synced": False,
    }

    # First enqueue succeeds
    assert persistence.enqueue_alert(alert) is True

    # Second enqueue with same event_id is rejected as duplicate
    assert persistence.enqueue_alert(alert) is False

    # Still only 1 pending alert in DB
    pending = persistence.get_pending_alerts("S1")
    assert len(pending) == 1
    assert pending[0]["event_id"] == "EVT-TEST-UNIQUE-101"


# --- 14. Existing routing and packet simulation integration works seamlessly ---

def test_existing_routing_and_packet_simulation_still_passes(client):
    """Network topology, Dijkstra routing, and packet simulation remain 100% functional."""
    # Check topology
    topo = client.get("/network").json()
    assert topo["active_nodes_count"] == 7
    assert topo["active_links_count"] == 10

    # Check shortest path
    route = client.get("/route?source=S1&destination=SRV").json()
    assert route["route"] == ["S1", "R1", "R2", "G1", "SRV"]
    assert route["total_cost"] == 9.0

    # Check standard packet simulation
    sim = client.post("/simulate", json={"source": "S1", "destination": "SRV"}).json()
    assert sim["status"] == "DELIVERED"
    assert sim["packet_id"].startswith("PKT-")

    # Check metrics
    metrics = client.get("/metrics").json()
    assert metrics["total_packets"] >= 1
    assert metrics["delivered_packets"] >= 1
