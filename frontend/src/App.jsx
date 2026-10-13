import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import Sidebar from './components/Sidebar';
import TopNav from './components/TopNav';
import MetricCards from './components/MetricCards';
import TopologyGraph from './components/TopologyGraph';
import RouteControlPanel from './components/RouteControlPanel';
import RoutingInsightsCard from './components/RoutingInsightsCard';
import NetworkHealthGauge from './components/NetworkHealthGauge';
import SmartAlerts from './components/SmartAlerts';
import SensorPanel from './components/SensorPanel';
import PacketHistoryTable from './components/PacketHistoryTable';
import PerformanceAnalytics from './components/PerformanceAnalytics';
import PacketDetailsModal from './components/PacketDetailsModal';
import EdgeAISection from './components/EdgeAISection';
import { 
  getHealth, 
  getMetrics, 
  getNetwork, 
  getSensors, 
  getShortestRoute, 
  simulatePacket, 
  getPackets, 
  resetSimulation, 
  updateNodeStatus, 
  resetNetworkTopology, 
  createWebSocketConnection 
} from './api';

export default function App() {
  const [activeTab, setActiveTab] = useState('overview');
  const [searchQuery, setSearchQuery] = useState('');

  // Backend state
  const [metrics, setMetrics] = useState({
    total_packets: 0,
    delivered_packets: 0,
    failed_packets: 0,
    delivery_ratio_percentage: 0.0,
    average_latency_ms: 0.0,
    average_hop_count: 0.0,
  });

  const [networkData, setNetworkData] = useState({
    nodes: [],
    links: [],
    active_nodes_count: 0,
    active_links_count: 0,
  });

  const [sensors, setSensors] = useState([]);
  const [packets, setPackets] = useState([]);
  const [latestTelemetryBySensor, setLatestTelemetryBySensor] = useState({});

  const [selectedRoute, setSelectedRoute] = useState([]);
  const [currentRouteResult, setCurrentRouteResult] = useState(null);
  const [lastPacketResult, setLastPacketResult] = useState(null);

  const [backendHealthy, setBackendHealthy] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [selectedModalPacket, setSelectedModalPacket] = useState(null);

  const wsRef = useRef(null);

  // Fetch all initial dashboard data
  const loadAllData = useCallback(async (isSilent = false) => {
    if (!isSilent) setIsRefreshing(true);
    try {
      try {
        await getHealth();
        setBackendHealthy(true);
      } catch {
        setBackendHealthy(false);
      }

      const [metricsRes, networkRes, sensorsRes, packetsRes] = await Promise.all([
        getMetrics().catch(() => null),
        getNetwork().catch(() => null),
        getSensors().catch(() => null),
        getPackets(100).catch(() => null),
      ]);

      if (metricsRes) setMetrics(metricsRes);
      if (networkRes) setNetworkData(networkRes);
      if (sensorsRes) setSensors(sensorsRes);
      if (packetsRes) {
        setPackets(packetsRes);
        const telemetryMap = {};
        for (const pkt of packetsRes) {
          if (pkt.payload?.sensor_id && !telemetryMap[pkt.payload.sensor_id]) {
            telemetryMap[pkt.payload.sensor_id] = pkt.payload;
          }
        }
        setLatestTelemetryBySensor((prev) => ({ ...prev, ...telemetryMap }));
      }

      setError(null);
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
      setError(err.message || 'Unable to connect to backend server');
    } finally {
      if (!isSilent) setIsRefreshing(false);
    }
  }, []);

  // Initialize data and WebSocket
  useEffect(() => {
    loadAllData();

    wsRef.current = createWebSocketConnection({
      onOpen: () => setWsConnected(true),
      onMessage: (data) => {
        if (data.event === 'packet_simulated' && data.packet) {
          const newPkt = data.packet;
          setPackets((prev) => [newPkt, ...prev.slice(0, 99)]);
          if (newPkt.payload?.sensor_id) {
            setLatestTelemetryBySensor((prev) => ({
              ...prev,
              [newPkt.payload.sensor_id]: newPkt.payload,
            }));
          }
          getMetrics().then((m) => setMetrics(m)).catch(() => {});
        }
      },
      onClose: () => setWsConnected(false),
      onError: () => setWsConnected(false),
    });

    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, [loadAllData]);

  // Simulate a packet transmission
  const handleSimulatePacket = async (source, destination, customPayload = null) => {
    setIsLoading(true);
    setError(null);
    setCurrentRouteResult(null);

    try {
      const packet = await simulatePacket(source, destination, customPayload);
      setLastPacketResult(packet);

      if (packet.status === 'DELIVERED') {
        setSelectedRoute(packet.route || []);
      } else {
        setSelectedRoute([]);
      }

      if (packet.payload?.sensor_id) {
        setLatestTelemetryBySensor((prev) => ({
          ...prev,
          [packet.payload.sensor_id]: packet.payload,
        }));
      }

      const [updatedMetrics, updatedPackets] = await Promise.all([
        getMetrics(),
        getPackets(100),
      ]);
      setMetrics(updatedMetrics);
      setPackets(updatedPackets);
    } catch (err) {
      console.error('Packet simulation error:', err);
      setError(err.message || 'Simulation failed');
      setSelectedRoute([]);
    } finally {
      setIsLoading(false);
    }
  };

  // Preview Dijkstra route without creating a packet
  const handleCalculateRouteOnly = async (source, destination) => {
    setIsLoading(true);
    setError(null);
    setLastPacketResult(null);

    try {
      const routeData = await getShortestRoute(source, destination);
      setCurrentRouteResult(routeData);
      setSelectedRoute(routeData.route || []);
    } catch (err) {
      console.error('Route calculation error:', err);
      setError(err.message || 'Could not find path');
      setSelectedRoute([]);
      setCurrentRouteResult(null);
    } finally {
      setIsLoading(false);
    }
  };

  // Toggle node operational status (active / inactive)
  const handleToggleNodeStatus = async (nodeId, newStatus) => {
    try {
      await updateNodeStatus(nodeId, newStatus);
      const updatedTopology = await getNetwork();
      setNetworkData(updatedTopology);

      if (newStatus === 'inactive' && selectedRoute.includes(nodeId)) {
        setSelectedRoute([]);
        setError(`Node ${nodeId} was disabled. Any active routes traversing it are now invalid.`);
      }
    } catch (err) {
      setError(`Failed to update status for ${nodeId}: ${err.message}`);
    }
  };

  // Reset simulation packet history and metrics
  const handleResetSimulation = async () => {
    try {
      await resetSimulation();
      setPackets([]);
      setSelectedRoute([]);
      setCurrentRouteResult(null);
      setLastPacketResult(null);
      const resetMetrics = await getMetrics();
      setMetrics(resetMetrics);
    } catch (err) {
      setError(`Reset failed: ${err.message}`);
    }
  };

  // Reset virtual network topology
  const handleResetTopology = async () => {
    try {
      await resetNetworkTopology();
      const defaultTopology = await getNetwork();
      setNetworkData(defaultTopology);
      setError(null);
    } catch (err) {
      setError(`Topology reset failed: ${err.message}`);
    }
  };

  // Generate Smart Alerts honestly from backend states
  const smartAlerts = useMemo(() => {
    const alerts = [];
    const inactiveNodes = networkData.nodes.filter((n) => n.status === 'inactive');
    for (const node of inactiveNodes) {
      alerts.push({
        type: 'error',
        title: `Node ${node.id} (${node.name.split('-')[0].trim()}) is Offline`,
        time: 'Active Outage • Rerouting in effect',
      });
    }

    const failedRecent = packets.filter((p) => p.status === 'FAILED').slice(0, 2);
    for (const fp of failedRecent) {
      alerts.push({
        type: 'warn',
        title: `Packet Drop: ${fp.packet_id} (${fp.source} ➔ ${fp.destination})`,
        time: fp.failure_reason || 'Unreachable destination',
      });
    }

    if (alerts.length === 0) {
      alerts.push({
        type: 'info',
        title: 'Topology Nominal: All 7 Nodes Operational',
        time: 'Dijkstra shortest-path engine ready',
      });
    }

    return alerts;
  }, [networkData.nodes, packets]);

  return (
    <div className="app-layout">
      {/* Tall Rounded Left Sidebar */}
      <Sidebar
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        backendHealthy={backendHealthy}
        onResetNetwork={handleResetTopology}
      />

      {/* Main Workspace */}
      <div className="main-workspace">
        {/* Top Navbar */}
        <TopNav
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          wsConnected={wsConnected}
          onRefresh={() => loadAllData(false)}
          isRefreshing={isRefreshing}
          alerts={smartAlerts}
        />

        {/* Top Metric Cards */}
        <MetricCards metrics={metrics} />

        {/* Tab Content Rendering */}
        {activeTab === 'overview' && (
          <>
            {/* Main Balanced Multi-Column Grid */}
            <div className="dashboard-grid">
              {/* Left Column: Live Topology & Routing Insights */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                <TopologyGraph
                  networkData={networkData}
                  selectedRoute={selectedRoute}
                  onToggleNodeStatus={handleToggleNodeStatus}
                  onResetTopology={handleResetTopology}
                />

                <RoutingInsightsCard
                  routeData={currentRouteResult}
                  packetData={lastPacketResult}
                  error={error}
                />
              </div>

              {/* Right Column: Routing Simulator, Health Gauge & Smart Alerts */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                <RouteControlPanel
                  nodes={networkData.nodes}
                  onSimulatePacket={handleSimulatePacket}
                  onCalculateRouteOnly={handleCalculateRouteOnly}
                  isLoading={isLoading}
                  error={error}
                />

                <div className="glass-panel" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', alignItems: 'center' }}>
                  <NetworkHealthGauge
                    networkData={networkData}
                    metrics={metrics}
                  />
                  <div style={{ padding: '1rem', borderLeft: '1px solid var(--glass-border-subtle)' }}>
                    <SmartAlerts alerts={smartAlerts} />
                  </div>
                </div>

                <SensorPanel
                  sensors={sensors}
                  latestTelemetryBySensor={latestTelemetryBySensor}
                />
              </div>
            </div>

            {/* Bottom Row: Packet Activity & Performance Analytics */}
            <div style={{ display: 'grid', gridTemplateColumns: '1.45fr 1fr', gap: '1.25rem' }}>
              <PacketHistoryTable
                packets={packets}
                onSelectPacket={(pkt) => setSelectedModalPacket(pkt)}
              />

              <PerformanceAnalytics
                packets={packets}
                metrics={metrics}
              />
            </div>
          </>
        )}

        {activeTab === 'edge-ai' && (
          <EdgeAISection wsConnected={wsConnected} />
        )}

        {activeTab === 'topology' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            <TopologyGraph
              networkData={networkData}
              selectedRoute={selectedRoute}
              onToggleNodeStatus={handleToggleNodeStatus}
              onResetTopology={handleResetTopology}
            />
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.25rem' }}>
              <RoutingInsightsCard
                routeData={currentRouteResult}
                packetData={lastPacketResult}
                error={error}
              />
              <SmartAlerts alerts={smartAlerts} />
            </div>
          </div>
        )}

        {activeTab === 'simulator' && (
          <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '1.25rem' }}>
            <TopologyGraph
              networkData={networkData}
              selectedRoute={selectedRoute}
              onToggleNodeStatus={handleToggleNodeStatus}
              onResetTopology={handleResetTopology}
            />
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              <RouteControlPanel
                nodes={networkData.nodes}
                onSimulatePacket={handleSimulatePacket}
                onCalculateRouteOnly={handleCalculateRouteOnly}
                isLoading={isLoading}
                error={error}
              />
              <RoutingInsightsCard
                routeData={currentRouteResult}
                packetData={lastPacketResult}
                error={error}
              />
            </div>
          </div>
        )}

        {activeTab === 'monitoring' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            <SensorPanel
              sensors={sensors}
              latestTelemetryBySensor={latestTelemetryBySensor}
            />
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.25rem' }}>
              <NetworkHealthGauge
                networkData={networkData}
                metrics={metrics}
              />
              <SmartAlerts alerts={smartAlerts} />
            </div>
          </div>
        )}

        {activeTab === 'history' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            <PacketHistoryTable
              packets={packets}
              onSelectPacket={(pkt) => setSelectedModalPacket(pkt)}
            />
          </div>
        )}

        {activeTab === 'analytics' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            <PerformanceAnalytics
              packets={packets}
              metrics={metrics}
            />
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.25rem' }}>
              <NetworkHealthGauge
                networkData={networkData}
                metrics={metrics}
              />
              <SmartAlerts alerts={smartAlerts} />
            </div>
          </div>
        )}

        {activeTab === 'settings' && (
          <div className="glass-panel" style={{ padding: '2rem', maxWidth: '800px' }}>
            <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.5rem', marginBottom: '1rem', color: 'var(--text-main)' }}>
              NetFlow Intelligence Settings
            </h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              <div style={{ background: '#fff', padding: '1.25rem', borderRadius: '14px', border: '1px solid #d5e5da' }}>
                <h4 style={{ fontWeight: 700, marginBottom: '0.35rem' }}>Backend API Connection</h4>
                <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                  Active Endpoint: <code>http://127.0.0.1:8000</code>
                </p>
                <div style={{ marginTop: '0.65rem' }}>
                  <span className={`status-pill ${backendHealthy ? 'delivered' : 'failed'}`}>
                    {backendHealthy ? 'FastAPI Connected (Healthy)' : 'Backend Unreachable'}
                  </span>
                </div>
              </div>

              <div style={{ background: '#fff', padding: '1.25rem', borderRadius: '14px', border: '1px solid #d5e5da' }}>
                <h4 style={{ fontWeight: 700, marginBottom: '0.35rem' }}>Simulation Memory Management</h4>
                <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginBottom: '0.85rem' }}>
                  Clear in-memory packet logs or restore original network graph topology.
                </p>
                <div style={{ display: 'flex', gap: '0.75rem' }}>
                  <button className="btn-emerald" onClick={handleResetTopology}>
                    Reset Network Graph
                  </button>
                  <button className="btn-glass" onClick={handleResetSimulation} style={{ color: '#dc2626' }}>
                    Clear Packet History
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Packet Inspection Details Modal */}
      {selectedModalPacket && (
        <PacketDetailsModal
          packet={selectedModalPacket}
          onClose={() => setSelectedModalPacket(null)}
        />
      )}
    </div>
  );
}
