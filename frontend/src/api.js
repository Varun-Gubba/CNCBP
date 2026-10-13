/**
 * Centralized API client for Network Monitoring and Intelligent Routing System.
 * Connects directly to the FastAPI backend running at http://127.0.0.1:8000.
 */

export const API_BASE_URL = 'http://127.0.0.1:8000';
export const WS_BASE_URL = 'ws://127.0.0.1:8000/ws';

/**
 * Generic fetch wrapper with standardized error handling and clean messages.
 */
async function request(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  try {
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      let errorMessage = `Server error (${response.status})`;
      try {
        const errorData = await response.json();
        errorMessage = errorData.message || errorData.detail || errorData.error || errorMessage;
      } catch {
        // Fallback to text
        const text = await response.text();
        if (text) errorMessage = text;
      }
      throw new Error(errorMessage);
    }

    return await response.json();
  } catch (error) {
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
      throw new Error('Backend server is unreachable. Ensure the FastAPI backend is running on port 8000.');
    }
    throw error;
  }
}

/**
 * Fetch health status of backend server.
 */
export async function getHealth() {
  return request('/health');
}

/**
 * Fetch aggregate network metrics (packet delivery ratio, avg latency, avg hops).
 */
export async function getMetrics() {
  return request('/metrics');
}

/**
 * Fetch complete network topology (nodes, links, and operational status).
 */
export async function getNetwork() {
  return request('/network');
}

/**
 * Fetch registered sensor nodes.
 */
export async function getSensors() {
  return request('/sensors');
}

/**
 * Calculate Dijkstra shortest path without creating a packet.
 */
export async function getShortestRoute(source, destination) {
  const params = new URLSearchParams({
    source: source.trim(),
    destination: destination.trim(),
  });
  return request(`/route?${params.toString()}`);
}

/**
 * Simulate packet creation, telemetry generation, routing, and delivery.
 */
export async function simulatePacket(source, destination, payload = null) {
  const body = {
    source: source.trim(),
    destination: destination.trim(),
  };
  if (payload) {
    body.payload = payload;
  }
  return request('/simulate', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

/**
 * Fetch recent packet transmission history (up to 100 packets).
 */
export async function getPackets(limit = 100) {
  return request(`/packets?limit=${limit}`);
}

/**
 * Reset packet history and simulation metrics.
 */
export async function resetSimulation() {
  return request('/reset', {
    method: 'POST',
  });
}

/**
 * Toggle node operational status (active/inactive) to test fault tolerance.
 */
export async function updateNodeStatus(nodeId, status) {
  return request(`/network/nodes/${nodeId}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  });
}

/**
 * Toggle link operational status (active/inactive).
 */
export async function updateLinkStatus(source, destination, status) {
  return request('/network/links/status', {
    method: 'PATCH',
    body: JSON.stringify({ source, destination, status }),
  });
}

/**
 * Restore network topology back to default state (all nodes and links active).
 */
export async function resetNetworkTopology() {
  return request('/network/reset', {
    method: 'POST',
  });
}

/**
 * Establishes a WebSocket connection for real-time packet transmission events.
 */
export function createWebSocketConnection({ onMessage, onOpen, onClose, onError }) {
  let ws = null;
  let heartbeatTimer = null;
  let isClosedByUser = false;

  try {
    ws = new WebSocket(WS_BASE_URL);

    ws.onopen = (event) => {
      if (onOpen) onOpen(event);
      // Heartbeat ping every 25 seconds to keep connection alive
      heartbeatTimer = setInterval(() => {
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send('ping');
        }
      }, 25000);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (onMessage) onMessage(data);
      } catch (err) {
        console.debug('Received non-JSON WebSocket frame:', event.data);
      }
    };

    ws.onclose = (event) => {
      clearInterval(heartbeatTimer);
      if (onClose && !isClosedByUser) onClose(event);
    };

    ws.onerror = (event) => {
      if (onError) onError(event);
    };
  } catch (err) {
    console.warn('WebSocket connection creation error:', err);
    if (onError) onError(err);
  }

  return {
    close: () => {
      isClosedByUser = true;
      clearInterval(heartbeatTimer);
      if (ws) ws.close();
    },
    send: (msg) => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(typeof msg === 'string' ? msg : JSON.stringify(msg));
      }
    },
  };
}

// --- Phase 2: Edge AI Intelligence Client Functions ---

/**
 * Fetch states for all edge nodes (connectivity, processing stats, pending queues).
 */
export async function getEdgeNodes() {
  return request('/edge/nodes');
}

/**
 * Fetch runtime state for a single edge node.
 */
export async function getEdgeNode(nodeId) {
  return request(`/edge/nodes/${nodeId}`);
}

/**
 * Submit and process an environmental reading locally at an edge node.
 */
export async function processEdgeReading(nodeId, reading) {
  return request(`/edge/nodes/${nodeId}/readings`, {
    method: 'POST',
    body: JSON.stringify(reading),
  });
}

/**
 * Toggle edge node connectivity (online / simulated offline outage).
 */
export async function toggleEdgeConnectivity(nodeId, isOnline) {
  return request(`/edge/nodes/${nodeId}/connectivity`, {
    method: 'POST',
    body: JSON.stringify({ is_online: isOnline }),
  });
}

/**
 * Synchronize offline pending alerts for a specific edge node to Central Server SRV.
 */
export async function syncEdgeNodeAlerts(nodeId) {
  return request(`/edge/nodes/${nodeId}/sync`, {
    method: 'POST',
  });
}

/**
 * Synchronize all online edge nodes.
 */
export async function syncAllEdgeAlerts() {
  return request('/edge/sync', {
    method: 'POST',
  });
}

/**
 * Fetch latest anomaly detection results across edge nodes.
 */
export async function getEdgeAnomalies(nodeId = null) {
  const url = nodeId ? `/edge/anomalies?node_id=${nodeId}` : '/edge/anomalies';
  return request(url);
}

/**
 * Fetch latest multi-hazard risk assessments.
 */
export async function getEdgeRiskAssessments() {
  return request('/edge/risk-assessments');
}

/**
 * Fetch alerts from persistent edge queue.
 */
export async function getEdgeAlerts(nodeId = null, synced = null, limit = 50) {
  const params = new URLSearchParams({ limit: String(limit) });
  if (nodeId) params.append('node_id', nodeId);
  if (synced !== null) params.append('synced', String(synced));
  return request(`/edge/alerts?${params.toString()}`);
}

/**
 * Fetch active configurable hazard thresholds.
 */
export async function getEdgeConfig() {
  return request('/edge/config');
}

/**
 * Trigger test scenario injection (e.g. normal, flood, fire, pollution, heat, landslide, gas, water).
 */
export async function simulateEdgeScenario(scenario, sensorId = 'S1') {
  return request('/edge/simulate-scenario', {
    method: 'POST',
    body: JSON.stringify({ scenario, sensor_id: sensorId }),
  });
}

/**
 * Reset edge node states, histories, and offline queues.
 */
export async function resetEdgeNodes() {
  return request('/edge/reset', {
    method: 'POST',
  });
}

