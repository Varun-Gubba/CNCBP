import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { 
  ShieldAlert, 
  Cpu, 
  Wifi, 
  WifiOff, 
  RefreshCw, 
  Activity, 
  Flame, 
  Droplets, 
  Wind, 
  Sun, 
  Mountain, 
  AlertOctagon, 
  Sparkles, 
  CheckCircle2, 
  AlertTriangle, 
  Clock, 
  Send, 
  Sliders, 
  Check,
  Database
} from 'lucide-react';
import { 
  getEdgeNodes, 
  getEdgeRiskAssessments, 
  getEdgeAnomalies, 
  getEdgeAlerts, 
  toggleEdgeConnectivity, 
  syncEdgeNodeAlerts, 
  simulateEdgeScenario,
  resetEdgeNodes
} from '../api';

const HAZARD_CONFIG = {
  FLOOD: {
    label: 'Flood & Flash Surge',
    icon: Droplets,
    color: '#0284c7',
    bg: '#f0f9ff',
    border: '#bae6fd',
    desc: 'River stage, rainfall accumulation, and water-level rise rate',
  },
  FOREST_FIRE: {
    label: 'Forest Fire Danger',
    icon: Flame,
    color: '#ea580c',
    bg: '#fff7ed',
    border: '#fed7aa',
    desc: 'Dry heat, low humidity, and smoke particulate byproducts',
  },
  AIR_POLLUTION: {
    label: 'Air Quality (NAAQS)',
    icon: Wind,
    color: '#7c3aed',
    bg: '#f5f3ff',
    border: '#ddd6fe',
    desc: 'CPCB 24-hr PM2.5, PM10, and sustained smog episodes',
  },
  EXTREME_HEAT: {
    label: 'Extreme Heatwave',
    icon: Sun,
    color: '#dc2626',
    bg: '#fef2f2',
    border: '#fecaca',
    desc: 'IMD heatwave criteria (> 40°C) & apparent Heat Index',
  },
  LANDSLIDE_PRECURSOR: {
    label: 'Landslide Precursor',
    icon: Mountain,
    color: '#b45309',
    bg: '#fffbeb',
    border: '#fde68a',
    desc: 'Volumetric pore saturation & slope micro-vibrations',
  },
  INDUSTRIAL_GAS: {
    label: 'Industrial Gas Leak',
    icon: AlertOctagon,
    color: '#e11d48',
    bg: '#fff1f2',
    border: '#fecdd3',
    desc: 'Toxic/volatile gas concentrations above ambient baseline',
  },
  WATER_QUALITY: {
    label: 'Water Degradation',
    icon: Sparkles,
    color: '#059669',
    bg: '#ecfdf5',
    border: '#a7f3d0',
    desc: 'BIS IS 10500 standards: pH, turbidity, and dissolved oxygen',
  },
};

export default function EdgeAISection({ wsConnected }) {
  const [nodes, setNodes] = useState([]);
  const [selectedNodeId, setSelectedNodeId] = useState('S1');
  const [riskAssessments, setRiskAssessments] = useState({});
  const [anomalies, setAnomalies] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [timelineEvents, setTimelineEvents] = useState([]);

  const [isLoading, setIsLoading] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [isInjecting, setIsInjecting] = useState(false);
  const [activeScenario, setActiveScenario] = useState('normal');
  const [feedbackMsg, setFeedbackMsg] = useState(null);
  const [error, setError] = useState(null);

  // Fetch all Edge AI data
  const fetchEdgeData = useCallback(async (isSilent = false) => {
    if (!isSilent) setIsLoading(true);
    try {
      const [nodesRes, risksRes, anomaliesRes, alertsRes] = await Promise.all([
        getEdgeNodes().catch(() => []),
        getEdgeRiskAssessments().catch(() => ({})),
        getEdgeAnomalies().catch(() => []),
        getEdgeAlerts(null, null, 50).catch(() => []),
      ]);

      setNodes(nodesRes || []);
      setRiskAssessments(risksRes || {});
      setAnomalies(anomaliesRes || []);
      setAlerts(alertsRes || []);
      setError(null);
    } catch (err) {
      console.error('Failed to load Edge AI intelligence:', err);
      setError(err.message || 'Error communicating with Edge AI backend');
    } finally {
      if (!isSilent) setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchEdgeData();
    // Periodic refresh every 4 seconds to sync live telemetry
    const interval = setInterval(() => {
      fetchEdgeData(true);
    }, 4000);
    return () => clearInterval(interval);
  }, [fetchEdgeData]);

  // Active selected node object
  const activeNode = useMemo(() => {
    return nodes.find((n) => n.node_id === selectedNodeId) || nodes[0] || null;
  }, [nodes, selectedNodeId]);

  // Active risk assessments for selected node
  const activeRisks = useMemo(() => {
    if (!activeNode) return {};
    return riskAssessments[activeNode.node_id] || {};
  }, [riskAssessments, activeNode]);

  // Active pending alerts in queue for selected node
  const pendingAlerts = useMemo(() => {
    return alerts.filter((a) => a.sensor_id === selectedNodeId && !a.synced);
  }, [alerts, selectedNodeId]);

  // Toggle node connectivity
  const handleToggleConnectivity = async (nodeId, currentOnline) => {
    try {
      const updated = await toggleEdgeConnectivity(nodeId, !currentOnline);
      setNodes((prev) => prev.map((n) => (n.node_id === nodeId ? updated : n)));
      
      const eventTitle = !currentOnline ? `Edge Node ${nodeId} Reconnected` : `Outage Simulated: Node ${nodeId} Offline`;
      const eventDesc = !currentOnline ? 'Network restored; queued alerts ready for synchronization.' : 'Local edge computing active; buffering alerts in persistent queue.';
      
      addTimelineEvent({
        type: !currentOnline ? 'online' : 'offline',
        title: eventTitle,
        desc: eventDesc,
        nodeId,
      });

      setFeedbackMsg(`Node ${nodeId} is now ${!currentOnline ? 'ONLINE' : 'OFFLINE (Local Buffering Active)'}`);
      setTimeout(() => setFeedbackMsg(null), 4000);
    } catch (err) {
      setError(`Failed to toggle connectivity: ${err.message}`);
    }
  };

  // Synchronize queued alerts
  const handleSyncAlerts = async (nodeId) => {
    setIsSyncing(true);
    try {
      const res = await syncEdgeNodeAlerts(nodeId);
      await fetchEdgeData(true);
      
      addTimelineEvent({
        type: 'sync',
        title: `Alerts Synchronized: ${nodeId}`,
        desc: `Transmitted ${res.synced_count} pending alerts via Dijkstra router to Central Server SRV.`,
        nodeId,
      });

      setFeedbackMsg(`Successfully synchronized ${res.synced_count} alerts from ${nodeId} to Central Server!`);
      setTimeout(() => setFeedbackMsg(null), 4500);
    } catch (err) {
      setError(`Sync failed: ${err.message}`);
    } finally {
      setIsSyncing(false);
    }
  };

  // Inject a multi-hazard scenario for interactive evaluation
  const handleInjectScenario = async (scenarioName) => {
    setIsInjecting(true);
    setActiveScenario(scenarioName);
    try {
      const res = await simulateEdgeScenario(scenarioName, selectedNodeId);
      await fetchEdgeData(true);

      const emitted = res.processing_result?.emitted_alerts || [];
      const anomCount = res.processing_result?.anomalies_detected_count || 0;

      addTimelineEvent({
        type: scenarioName === 'normal' ? 'normal' : 'hazard',
        title: `Scenario Injected: ${scenarioName.toUpperCase()}`,
        desc: `${anomCount} anomalies detected; ${emitted.length} prioritized alert(s) generated on ${selectedNodeId}.`,
        nodeId: selectedNodeId,
      });

      setFeedbackMsg(`Injected '${scenarioName}' on ${selectedNodeId}: ${anomCount} anomalies detected.`);
      setTimeout(() => setFeedbackMsg(null), 4000);
    } catch (err) {
      setError(`Scenario injection failed: ${err.message}`);
    } finally {
      setIsInjecting(false);
    }
  };

  // Reset edge node states
  const handleResetEdge = async () => {
    try {
      await resetEdgeNodes();
      await fetchEdgeData(true);
      setTimelineEvents([]);
      setFeedbackMsg('All Edge AI nodes and persistent queues reset to baseline.');
      setTimeout(() => setFeedbackMsg(null), 3000);
    } catch (err) {
      setError(`Reset failed: ${err.message}`);
    }
  };

  // Helper to append to local timeline
  const addTimelineEvent = (evt) => {
    setTimelineEvents((prev) => [
      {
        id: Math.random().toString(36).substring(2, 9),
        time: new Date().toLocaleTimeString(),
        ...evt,
      },
      ...prev.slice(0, 19),
    ]);
  };

  // Severity color badge helper
  const getSeverityBadge = (sev) => {
    switch (sev) {
      case 'CRITICAL':
        return { label: 'CRITICAL', bg: '#fef2f2', color: '#dc2626', border: '#fca5a5' };
      case 'HIGH':
        return { label: 'HIGH RISK', bg: '#fff7ed', color: '#c2410c', border: '#fed7aa' };
      case 'MODERATE':
        return { label: 'MODERATE', bg: '#fffbeb', color: '#b45309', border: '#fde68a' };
      default:
        return { label: 'LOW / SAFE', bg: '#f0fdf4', color: '#15803d', border: '#bbf7d0' };
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Top Banner & Scenario Injector Bar */}
      <div 
        className="glass-panel" 
        style={{ 
          padding: '1.25rem 1.5rem', 
          display: 'flex', 
          flexDirection: 'column', 
          gap: '1rem',
          background: 'linear-gradient(135deg, rgba(255,255,255,0.92) 0%, rgba(240,253,244,0.85) 100%)',
          border: '1px solid #bbf7d0'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div 
              style={{ 
                width: 42, 
                height: 42, 
                borderRadius: '12px', 
                background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                color: '#fff',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: '0 4px 12px rgba(16,185,129,0.25)'
              }}
            >
              <ShieldAlert size={24} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <h2 style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--text-main)', margin: 0 }}>
                  Edge AI Intelligence & Early Warning
                </h2>
                <span className="status-pill delivered" style={{ fontSize: '0.7rem', padding: '0.15rem 0.5rem' }}>
                  Phase 2 Active
                </span>
                <span className={`status-pill ${wsConnected ? 'delivered' : 'in-transit'}`} style={{ fontSize: '0.7rem', padding: '0.15rem 0.5rem' }}>
                  {wsConnected ? 'Live Channel Active' : 'Polling Sync'}
                </span>
              </div>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.2rem', marginBottom: 0 }}>
                On-device anomaly detection, multi-hazard risk engine, and persistent offline operation for Indian Early Warning.
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <button 
              className="btn-glass" 
              onClick={() => fetchEdgeData(false)}
              disabled={isLoading}
              title="Refresh Edge AI State"
              style={{ fontSize: '0.78rem', padding: '0.45rem 0.85rem' }}
            >
              <RefreshCw size={13} className={isLoading ? 'spin-icon' : ''} />
              <span>Refresh</span>
            </button>
            <button 
              className="btn-glass" 
              onClick={handleResetEdge}
              title="Reset all edge node states and alert queues"
              style={{ fontSize: '0.78rem', padding: '0.45rem 0.85rem', color: '#b91c1c' }}
            >
              <Sliders size={13} />
              <span>Reset State</span>
            </button>
          </div>
        </div>

        {/* Quick Scenario Injector */}
        <div style={{ paddingTop: '0.75rem', borderTop: '1px solid #dcfce7' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Test Scenario Injection (Target: Node {selectedNodeId})
            </span>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
              Evaluates explainable threshold rules, moving statistics & Isolation Forest
            </span>
          </div>

          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
            {[
              { id: 'normal', label: 'Nominal Baseline', icon: Check, color: '#15803d' },
              { id: 'flood', label: 'Flash Flood Surge', icon: Droplets, color: '#0284c7' },
              { id: 'fire', label: 'Forest Fire Danger', icon: Flame, color: '#ea580c' },
              { id: 'pollution', label: 'Severe PM2.5 Smog', icon: Wind, color: '#7c3aed' },
              { id: 'heat', label: 'Extreme Heatwave', icon: Sun, color: '#dc2626' },
              { id: 'landslide', label: 'Landslide Precursor', icon: Mountain, color: '#b45309' },
              { id: 'gas', label: 'Toxic Gas Leak', icon: AlertOctagon, color: '#e11d48' },
              { id: 'water', label: 'Water Contamination', icon: Sparkles, color: '#059669' },
            ].map((sc) => {
              const Icon = sc.icon;
              const isCurrent = activeScenario === sc.id;
              return (
                <button
                  key={sc.id}
                  onClick={() => handleInjectScenario(sc.id)}
                  disabled={isInjecting}
                  style={{
                    background: isCurrent ? '#ffffff' : 'rgba(255,255,255,0.7)',
                    border: isCurrent ? `2px solid ${sc.color}` : '1px solid #d5e5da',
                    color: isCurrent ? sc.color : 'var(--text-main)',
                    fontWeight: isCurrent ? 800 : 600,
                    borderRadius: '8px',
                    padding: '0.35rem 0.65rem',
                    fontSize: '0.76rem',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 5,
                    cursor: 'pointer',
                    boxShadow: isCurrent ? '0 2px 8px rgba(0,0,0,0.06)' : 'none',
                    transition: 'all 0.15s ease'
                  }}
                >
                  <Icon size={13} color={sc.color} />
                  <span>{sc.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Feedback message banner */}
        {feedbackMsg && (
          <div 
            style={{ 
              background: '#ecfdf5', 
              color: '#065f46', 
              padding: '0.5rem 0.75rem', 
              borderRadius: '8px', 
              fontSize: '0.78rem',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              border: '1px solid #a7f3d0'
            }}
          >
            <CheckCircle2 size={14} color="#059669" />
            <span>{feedbackMsg}</span>
          </div>
        )}

        {error && (
          <div 
            style={{ 
              background: '#fef2f2', 
              color: '#991b1b', 
              padding: '0.5rem 0.75rem', 
              borderRadius: '8px', 
              fontSize: '0.78rem',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              border: '1px solid #fecaca'
            }}
          >
            <AlertTriangle size={14} color="#dc2626" />
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* Section A: Edge Node Cards */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
          <h3 className="card-title-styled" style={{ fontSize: '1.05rem' }}>
            <Cpu size={18} />
            <span>Edge Computing Nodes</span>
          </h3>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Select node to inspect telemetry and local risk models
          </span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1rem' }}>
          {nodes.map((node) => {
            const isSelected = selectedNodeId === node.node_id;
            const isOnline = node.is_online;
            return (
              <div
                key={node.node_id}
                onClick={() => setSelectedNodeId(node.node_id)}
                className="glass-panel"
                style={{
                  padding: '1.25rem',
                  border: isSelected ? '2px solid #10b981' : '1px solid #d5e5da',
                  background: isSelected ? '#ffffff' : '#fcfdfd',
                  cursor: 'pointer',
                  position: 'relative',
                  boxShadow: isSelected ? '0 4px 16px rgba(16,185,129,0.12)' : 'none',
                  transition: 'all 0.2s ease',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span 
                      style={{ 
                        fontSize: '0.85rem', 
                        fontWeight: 900, 
                        background: isSelected ? '#047857' : '#0284c7', 
                        color: '#fff',
                        padding: '0.2rem 0.55rem',
                        borderRadius: '6px'
                      }}
                    >
                      {node.node_id}
                    </span>
                    <div>
                      <h4 style={{ fontWeight: 800, fontSize: '0.9rem', color: 'var(--text-main)', margin: 0 }}>
                        {node.node_id === 'S1' ? 'Himalayan Basin Station' : 'Delhi-NCR Station'}
                      </h4>
                      <p style={{ fontSize: '0.72rem', color: 'var(--text-muted)', margin: 0 }}>
                        {node.location}
                      </p>
                    </div>
                  </div>

                  <span 
                    className={`status-pill ${isOnline ? 'delivered' : 'failed'}`}
                    style={{ fontSize: '0.7rem', padding: '0.2rem 0.55rem' }}
                  >
                    {isOnline ? (
                      <>
                        <Wifi size={11} style={{ marginRight: 3 }} /> Online
                      </>
                    ) : (
                      <>
                        <WifiOff size={11} style={{ marginRight: 3 }} /> Offline (Buffered)
                      </>
                    )}
                  </span>
                </div>

                {/* Node Metrics Grid */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.5rem', marginBottom: '0.85rem' }}>
                  <div style={{ background: '#f8fafc', padding: '0.5rem', borderRadius: '8px', border: '1px solid #e2e8f0', textAlign: 'center' }}>
                    <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)', display: 'block' }}>Processed</span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 800, fontSize: '0.95rem', color: 'var(--text-main)' }}>
                      {node.readings_processed}
                    </span>
                  </div>
                  <div style={{ background: '#f8fafc', padding: '0.5rem', borderRadius: '8px', border: '1px solid #e2e8f0', textAlign: 'center' }}>
                    <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)', display: 'block' }}>Pending Queue</span>
                    <span 
                      style={{ 
                        fontFamily: 'var(--font-mono)', 
                        fontWeight: 800, 
                        fontSize: '0.95rem', 
                        color: node.pending_alerts_count > 0 ? '#ea580c' : 'var(--text-main)' 
                      }}
                    >
                      {node.pending_alerts_count}
                    </span>
                  </div>
                  <div style={{ background: '#f8fafc', padding: '0.5rem', borderRadius: '8px', border: '1px solid #e2e8f0', textAlign: 'center' }}>
                    <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)', display: 'block' }}>Synced Alerts</span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 800, fontSize: '0.95rem', color: '#15803d' }}>
                      {node.synced_alerts_count}
                    </span>
                  </div>
                </div>

                {/* Actions & Offline Toggle */}
                <div style={{ display: 'flex', gap: '0.5rem', paddingTop: '0.5rem', borderTop: '1px solid #f1f5f3' }}>
                  <button
                    className="btn-glass"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleToggleConnectivity(node.node_id, isOnline);
                    }}
                    style={{ 
                      flex: 1, 
                      padding: '0.35rem 0.5rem', 
                      fontSize: '0.72rem',
                      color: isOnline ? '#b91c1c' : '#15803d',
                      borderColor: isOnline ? '#fca5a5' : '#86efac'
                    }}
                  >
                    {isOnline ? <WifiOff size={12} /> : <Wifi size={12} />}
                    <span>{isOnline ? 'Simulate Outage' : 'Restore Online'}</span>
                  </button>

                  <button
                    className="btn-emerald"
                    disabled={!isOnline || node.pending_alerts_count === 0 || isSyncing}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleSyncAlerts(node.node_id);
                    }}
                    style={{ 
                      flex: 1, 
                      padding: '0.35rem 0.5rem', 
                      fontSize: '0.72rem',
                      opacity: (!isOnline || node.pending_alerts_count === 0) ? 0.5 : 1
                    }}
                  >
                    <Send size={12} />
                    <span>Sync Queue ({node.pending_alerts_count})</span>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Section B: Multi-Hazard Monitoring Cards */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
          <h3 className="card-title-styled" style={{ fontSize: '1.05rem' }}>
            <Activity size={18} />
            <span>Multi-Hazard Risk Engine (Node {selectedNodeId})</span>
          </h3>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Calculated locally at edge via documented physical rules & Isolation Forest
          </span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
          {Object.keys(HAZARD_CONFIG).map((hKey) => {
            const cfg = HAZARD_CONFIG[hKey];
            const Icon = cfg.icon;
            const assessment = activeRisks[hKey];

            const riskScore = assessment ? assessment.risk_score : 0.0;
            const severity = assessment ? assessment.severity : 'LOW';
            const badge = getSeverityBadge(severity);
            const conf = assessment ? assessment.confidence_score : 20.0;
            const anomaliesList = assessment ? assessment.detected_anomalies : [];
            const action = assessment ? assessment.recommended_action : 'Normal conditions';

            return (
              <div 
                key={hKey} 
                className="glass-panel" 
                style={{ 
                  padding: '1.15rem', 
                  display: 'flex', 
                  flexDirection: 'column', 
                  gap: '0.65rem',
                  border: `1px solid ${cfg.border}`,
                  background: '#ffffff',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <div 
                      style={{ 
                        width: 32, 
                        height: 32, 
                        borderRadius: '8px', 
                        background: cfg.bg, 
                        color: cfg.color,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        border: `1px solid ${cfg.border}`
                      }}
                    >
                      <Icon size={17} />
                    </div>
                    <div>
                      <h4 style={{ fontWeight: 800, fontSize: '0.86rem', color: 'var(--text-main)', margin: 0 }}>
                        {cfg.label}
                      </h4>
                      <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
                        Confidence: {conf}%
                      </span>
                    </div>
                  </div>

                  <span 
                    style={{ 
                      fontSize: '0.65rem', 
                      fontWeight: 800, 
                      padding: '0.15rem 0.45rem', 
                      borderRadius: '4px',
                      background: badge.bg,
                      color: badge.color,
                      border: `1px solid ${badge.border}`
                    }}
                  >
                    {badge.label}
                  </span>
                </div>

                {/* Risk Score Progress Bar */}
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '0.25rem' }}>
                    <span style={{ color: 'var(--text-secondary)' }}>Risk Score</span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 800, color: badge.color }}>
                      {riskScore} / 100
                    </span>
                  </div>
                  <div style={{ width: '100%', height: '6px', background: '#f1f5f9', borderRadius: '3px', overflow: 'hidden' }}>
                    <div 
                      style={{ 
                        width: `${Math.min(riskScore, 100)}%`, 
                        height: '100%', 
                        background: riskScore >= 85 ? '#dc2626' : (riskScore >= 65 ? '#ea580c' : (riskScore >= 40 ? '#d97706' : '#10b981')),
                        borderRadius: '3px',
                        transition: 'width 0.4s ease'
                      }} 
                    />
                  </div>
                </div>

                {/* Anomalies Detected or Baseline */}
                <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', background: '#fafafa', padding: '0.45rem 0.6rem', borderRadius: '6px', border: '1px solid #f1f5f9' }}>
                  {anomaliesList && anomaliesList.length > 0 ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                      <span style={{ fontWeight: 700, color: badge.color }}>Active Anomaly:</span>
                      <span>{anomaliesList[0]}</span>
                    </div>
                  ) : (
                    <span style={{ color: 'var(--text-muted)' }}>Within safe baseline envelope.</span>
                  )}
                </div>

                {/* Recommended Action */}
                <div style={{ fontSize: '0.72rem', color: 'var(--text-main)', borderTop: '1px solid #f1f5f3', paddingTop: '0.45rem' }}>
                  <span style={{ fontWeight: 700, color: 'var(--text-muted)', display: 'block', fontSize: '0.65rem', textTransform: 'uppercase' }}>
                    Recommended Action
                  </span>
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                    {action}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Section C & D: Anomaly Detection Panel & Offline Operation Panel */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '1.25rem' }}>
        {/* Panel C: Detected Anomalies */}
        <div className="glass-panel" style={{ padding: '1.25rem' }}>
          <div className="card-header-styled" style={{ padding: '0 0 0.85rem 0' }}>
            <h3 className="card-title-styled" style={{ fontSize: '1rem' }}>
              <AlertTriangle size={17} />
              <span>Edge Anomaly Detections</span>
            </h3>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
              Statistical Z-Score & Moving Window Rules
            </span>
          </div>

          {anomalies.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '2rem 1rem', color: 'var(--text-muted)' }}>
              <CheckCircle2 size={32} color="#10b981" style={{ margin: '0 auto 0.5rem auto' }} />
              <p style={{ fontSize: '0.85rem', fontWeight: 600 }}>All Readings Within Normal Range</p>
              <p style={{ fontSize: '0.75rem' }}>No statistical outliers or threshold breaches detected.</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem', maxHeight: '380px', overflowY: 'auto' }}>
              {anomalies.map((anom) => (
                <div
                  key={anom.anomaly_id}
                  style={{
                    background: '#fff',
                    border: '1px solid #fed7aa',
                    borderRadius: '8px',
                    padding: '0.75rem',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 4,
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span style={{ fontSize: '0.72rem', fontWeight: 800, padding: '0.1rem 0.4rem', borderRadius: '4px', background: '#e0f2fe', color: '#0284c7' }}>
                        {anom.sensor_id}
                      </span>
                      <span style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-main)' }}>
                        {anom.metric}
                      </span>
                    </div>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', fontWeight: 800, color: '#ea580c' }}>
                      Score: {anom.anomaly_score}
                    </span>
                  </div>

                  <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', margin: '0.2rem 0' }}>
                    {anom.explanation}
                  </p>

                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.68rem', color: 'var(--text-muted)' }}>
                    <span>Method: {anom.detection_method}</span>
                    <span>Observed: {anom.observed_value}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Panel D: Offline Operation & Persistent Queue Panel */}
        <div className="glass-panel" style={{ padding: '1.25rem' }}>
          <div className="card-header-styled" style={{ padding: '0 0 0.85rem 0' }}>
            <h3 className="card-title-styled" style={{ fontSize: '1rem' }}>
              <Database size={17} />
              <span>Offline Queue & Synchronization</span>
            </h3>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
              SQLite Persistent Buffer
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
            {/* Status card */}
            <div style={{ background: '#f8fafc', padding: '0.85rem', borderRadius: '10px', border: '1px solid #e2e8f0' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-main)' }}>
                  Local Node Status ({selectedNodeId})
                </span>
                <span className={`status-pill ${activeNode?.is_online ? 'delivered' : 'failed'}`} style={{ fontSize: '0.68rem' }}>
                  {activeNode?.is_online ? 'Online' : 'Offline Buffer Active'}
                </span>
              </div>
              <p style={{ fontSize: '0.74rem', color: 'var(--text-secondary)', margin: 0 }}>
                {activeNode?.is_online 
                  ? 'Transmitting alerts immediately over Dijkstra shortest path to SRV.'
                  : 'Central server unreachable. All critical events retained in FIFO local queue.'}
              </p>
            </div>

            {/* Pending alerts list */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.45rem' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                  Pending Alerts in Queue ({pendingAlerts.length})
                </span>
                {pendingAlerts.length > 0 && activeNode?.is_online && (
                  <button 
                    className="btn-emerald" 
                    onClick={() => handleSyncAlerts(selectedNodeId)}
                    disabled={isSyncing}
                    style={{ fontSize: '0.7rem', padding: '0.25rem 0.55rem' }}
                  >
                    Sync All Now
                  </button>
                )}
              </div>

              {pendingAlerts.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '1.5rem', background: '#fff', borderRadius: '8px', border: '1px solid #e2e8f0', color: 'var(--text-muted)' }}>
                  <Check size={20} color="#10b981" style={{ margin: '0 auto 0.25rem auto' }} />
                  <p style={{ fontSize: '0.76rem', margin: 0 }}>Queue is empty. All generated alerts synchronized.</p>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', maxHeight: '240px', overflowY: 'auto' }}>
                  {pendingAlerts.map((alt) => (
                    <div 
                      key={alt.event_id} 
                      style={{ 
                        background: '#fff', 
                        padding: '0.65rem', 
                        borderRadius: '8px', 
                        border: '1px solid #fed7aa',
                        fontSize: '0.74rem'
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 3 }}>
                        <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 800, color: 'var(--text-main)' }}>
                          {alt.event_id}
                        </span>
                        <span style={{ fontWeight: 800, color: '#dc2626' }}>
                          {alt.severity}
                        </span>
                      </div>
                      <p style={{ margin: '0 0 4px 0', color: 'var(--text-secondary)' }}>
                        {alt.hazard_type}: {alt.explanation}
                      </p>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.68rem', color: 'var(--text-muted)' }}>
                        <span>Lifecycle: {alt.lifecycle_state}</span>
                        <span>Attempts: {alt.delivery_attempts}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Section E: Live Activity Timeline */}
      <div className="glass-panel" style={{ padding: '1.25rem' }}>
        <div className="card-header-styled" style={{ padding: '0 0 0.85rem 0' }}>
          <h3 className="card-title-styled" style={{ fontSize: '1rem' }}>
            <Clock size={17} />
            <span>Edge Activity & Audit Timeline</span>
          </h3>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
            Real-time chronological events across edge nodes
          </span>
        </div>

        {timelineEvents.length === 0 ? (
          <div style={{ padding: '1.5rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
            No recent activity recorded yet. Use the scenario buttons above or toggle connectivity to generate live events.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
            {timelineEvents.map((evt) => (
              <div 
                key={evt.id} 
                style={{ 
                  display: 'flex', 
                  alignItems: 'flex-start', 
                  gap: '0.75rem',
                  padding: '0.65rem 0.85rem',
                  background: '#ffffff',
                  borderRadius: '8px',
                  border: '1px solid #e2e8f0'
                }}
              >
                <div 
                  style={{ 
                    marginTop: 2,
                    width: 20, 
                    height: 20, 
                    borderRadius: '50%',
                    background: evt.type === 'hazard' ? '#fee2e2' : (evt.type === 'sync' ? '#dcfce7' : (evt.type === 'offline' ? '#ffedd5' : '#e0f2fe')),
                    color: evt.type === 'hazard' ? '#dc2626' : (evt.type === 'sync' ? '#15803d' : (evt.type === 'offline' ? '#ea580c' : '#0284c7')),
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '0.65rem',
                    fontWeight: 800
                  }}
                >
                  •
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '0.8rem', fontWeight: 800, color: 'var(--text-main)' }}>
                      {evt.title}
                    </span>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                      {evt.time}
                    </span>
                  </div>
                  <p style={{ fontSize: '0.74rem', color: 'var(--text-secondary)', margin: '0.15rem 0 0 0' }}>
                    {evt.desc}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
