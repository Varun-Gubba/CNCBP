"""
Live integration test script testing every endpoint against a running Uvicorn server.
"""

import httpx

base_url = "http://127.0.0.1:8000"
client = httpx.Client(base_url=base_url)

print("--- 1. Testing GET / ---")
res = client.get("/")
print("Status:", res.status_code)
print("Response:", res.json())
assert res.status_code == 200

print("\n--- 2. Testing GET /health ---")
res = client.get("/health")
print("Status:", res.status_code)
print("Response:", res.json())
assert res.status_code == 200

print("\n--- 3. Testing GET /network ---")
res = client.get("/network")
data = res.json()
print("Status:", res.status_code)
print(f"Total Nodes: {len(data['nodes'])}, Total Links: {len(data['links'])}")
assert res.status_code == 200

print("\n--- 4. Testing GET /sensors ---")
res = client.get("/sensors")
print("Status:", res.status_code)
print("Sensors:", [s["id"] for s in res.json()])
assert res.status_code == 200

print("\n--- 5. Testing GET /route?source=S1&destination=SRV ---")
res = client.get("/route?source=S1&destination=SRV")
print("Status:", res.status_code)
route_data = res.json()
print("Optimal Route:", route_data["route"])
print("Total Cost:", route_data["total_cost"])
print("Hops:", route_data["hop_count"])
print("Estimated Latency:", route_data["estimated_latency_ms"], "ms")
assert res.status_code == 200
assert route_data["route"] == ["S1", "R1", "R2", "G1", "SRV"]

print("\n--- 6. Testing GET /route?source=S2&destination=SRV ---")
res = client.get("/route?source=S2&destination=SRV")
print("Status:", res.status_code)
route_data2 = res.json()
print("Optimal Route:", route_data2["route"])
print("Total Cost:", route_data2["total_cost"])
assert route_data2["route"] == ["S2", "R3", "G1", "SRV"]

print("\n--- 7. Testing GET /route?source=INVALID&destination=SRV (Error Handling) ---")
res = client.get("/route?source=INVALID&destination=SRV")
print("Status:", res.status_code)
print("Response:", res.json())
assert res.status_code == 404

print("\n--- 8. Testing POST /simulate (Default Auto Payload) ---")
res = client.post("/simulate", json={"source": "S1", "destination": "SRV"})
print("Status:", res.status_code)
packet = res.json()
print("Packet ID:", packet["packet_id"])
print("Status:", packet["status"])
print("Route:", packet["route"])
print("Telemetry:", packet["payload"])
assert res.status_code == 200
assert packet["status"] == "DELIVERED"

print("\n--- 9. Testing POST /simulate (Custom Payload) ---")
custom_payload = {
    "sensor_id": "S2",
    "timestamp": "2026-10-12T10:00:00Z",
    "temperature_celsius": 26.8,
    "humidity_percentage": 58.4,
    "air_quality_aqi": 48.0,
    "is_simulated": True,
    "notes": "Custom test telemetry",
}
res = client.post("/simulate", json={"source": "S2", "destination": "SRV", "payload": custom_payload})
print("Status:", res.status_code)
packet2 = res.json()
print("Packet ID:", packet2["packet_id"])
print("Status:", packet2["status"])
print("Route:", packet2["route"])
assert res.status_code == 200
assert packet2["payload"]["temperature_celsius"] == 26.8

print("\n--- 10. Testing GET /packets ---")
res = client.get("/packets")
print("Status:", res.status_code)
print(f"Stored Packets Count: {len(res.json())}")
assert len(res.json()) >= 2

print("\n--- 11. Testing Failure Simulation (Deactivate Gateway G1) ---")
client.patch("/network/nodes/G1/status", json={"status": "inactive"})
res = client.get("/route?source=S1&destination=SRV")
print("Route status when G1 down:", res.status_code, res.json())
assert res.status_code == 400

res_sim = client.post("/simulate", json={"source": "S1", "destination": "SRV"})
print("Simulate status when G1 down:", res_sim.status_code, res_sim.json()["status"], res_sim.json()["failure_reason"])
assert res_sim.json()["status"] == "FAILED"

print("\n--- 12. Testing GET /metrics (Includes delivered and failed) ---")
res = client.get("/metrics")
print("Status:", res.status_code)
print("Metrics:", res.json())
metrics = res.json()
assert metrics["delivered_packets"] >= 2
assert metrics["failed_packets"] >= 1

print("\n--- 13. Testing POST /reset ---")
res = client.post("/reset")
print("Status:", res.status_code, res.json())
metrics_after = client.get("/metrics").json()
print("Metrics After Reset:", metrics_after)
assert metrics_after["total_packets"] == 0

print("\n--- 14. Testing POST /network/reset ---")
res = client.post("/network/reset")
print("Status:", res.status_code, res.json())
topo_restored = client.get("/network").json()
assert topo_restored["active_nodes_count"] == 7

print("\n--- 15. Testing GET /edge/nodes ---")
res = client.get("/edge/nodes")
print("Status:", res.status_code)
edge_nodes_list = res.json()
print("Edge Nodes:", [n["node_id"] for n in edge_nodes_list])
assert res.status_code == 200
assert len(edge_nodes_list) >= 2

print("\n--- 16. Testing POST /edge/simulate-scenario (Flash Flood) ---")
res = client.post("/edge/simulate-scenario", json={"scenario": "flood", "sensor_id": "S1"})
print("Status:", res.status_code)
flood_res = res.json()
print("Anomalies Detected:", flood_res["processing_result"]["anomalies_detected_count"])
print("Alerts Emitted:", len(flood_res["processing_result"]["emitted_alerts"]))
assert res.status_code == 200
assert flood_res["processing_result"]["anomalies_detected_count"] >= 1

print("\n--- 17. Testing GET /edge/risk-assessments ---")
res = client.get("/edge/risk-assessments")
print("Status:", res.status_code)
risks = res.json()
s1_risks = risks.get("S1", {})
print("S1 Flood Risk Score:", s1_risks.get("FLOOD", {}).get("risk_score"))
assert res.status_code == 200
assert s1_risks.get("FLOOD", {}).get("severity") in ("HIGH", "CRITICAL")

print("\n--- 18. Testing Offline Outage Mode on Node S1 ---")
res = client.post("/edge/nodes/S1/connectivity", json={"is_online": False})
print("Set S1 Offline Status:", res.status_code, "Online:", res.json()["is_online"])
assert res.json()["is_online"] is False

# Inject Forest Fire while offline
res_fire = client.post("/edge/simulate-scenario", json={"scenario": "fire", "sensor_id": "S1"})
print("Offline Processed Fire, Emitted:", len(res_fire.json()["processing_result"]["emitted_alerts"]))

# Check pending queue
s1_state = client.get("/edge/nodes/S1").json()
print("Pending Queue Count during outage:", s1_state["pending_alerts_count"])
assert s1_state["pending_alerts_count"] >= 1

print("\n--- 19. Restoring Connectivity & Syncing Queued Alerts ---")
client.post("/edge/nodes/S1/connectivity", json={"is_online": True})
res_sync = client.post("/edge/nodes/S1/sync")
print("Sync Status:", res_sync.status_code, res_sync.json())
assert res_sync.status_code == 200
assert res_sync.json()["synced_count"] >= 1

s1_after_sync = client.get("/edge/nodes/S1").json()
print("Pending Count After Sync:", s1_after_sync["pending_alerts_count"])
assert s1_after_sync["pending_alerts_count"] == 0

print("\n--- 20. Testing POST /edge/reset ---")
res = client.post("/edge/reset")
print("Status:", res.status_code, res.json())
assert res.status_code == 200

print("\nALL PHASE 1 & PHASE 2 LIVE TESTS COMPLETED SUCCESSFULLY!")
