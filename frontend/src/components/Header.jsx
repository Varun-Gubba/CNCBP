import React from 'react';
import { 
  Radio, 
  Activity, 
  RefreshCw, 
  RotateCcw, 
  Layers, 
  Wifi, 
  WifiOff,
  Server
} from 'lucide-react';

export default function Header({ 
  backendHealthy, 
  wsConnected, 
  onRefresh, 
  onResetSimulation, 
  onResetTopology, 
  isRefreshing 
}) {
  return (
    <header className="header-container">
      <div className="brand-wrapper">
        <div className="brand-icon">
          <Radio size={22} />
        </div>
        <div>
          <h1 className="brand-title">
            Network Monitoring & Intelligent Routing
          </h1>
          <p className="brand-subtitle">
            <span>Dijkstra Shortest Path Engine</span>
            <span>•</span>
            <span>Virtual IoT Telemetry Simulation</span>
          </p>
        </div>
      </div>

      <div className="header-status-group">
        {/* Backend Server Health */}
        <div className={`status-chip ${backendHealthy ? 'healthy' : 'ws-offline'}`}>
          <span className="pulse-dot"></span>
          <Server size={13} />
          <span>{backendHealthy ? 'API Active (8000)' : 'API Disconnected'}</span>
        </div>

        {/* WebSocket Live Stream Status */}
        <div className={`status-chip ${wsConnected ? 'ws-active' : 'ws-offline'}`}>
          {wsConnected ? <Wifi size={13} /> : <WifiOff size={13} />}
          <span>{wsConnected ? 'Live Stream Active' : 'Polling Mode'}</span>
        </div>

        {/* Refresh Button */}
        <button 
          className="btn btn-secondary" 
          onClick={onRefresh} 
          disabled={isRefreshing}
          title="Refresh metrics, topology, and packet records"
        >
          <RefreshCw size={14} className={isRefreshing ? 'spinner' : ''} />
          <span>Refresh</span>
        </button>

        {/* Reset Topology Button */}
        <button 
          className="btn btn-secondary" 
          onClick={onResetTopology}
          title="Restore all nodes and links to active operational state"
        >
          <Layers size={14} />
          <span>Reset Network</span>
        </button>

        {/* Reset History Button */}
        <button 
          className="btn btn-danger" 
          onClick={onResetSimulation}
          title="Clear packet history and reset performance metrics"
        >
          <RotateCcw size={14} />
          <span>Clear History</span>
        </button>
      </div>
    </header>
  );
}
