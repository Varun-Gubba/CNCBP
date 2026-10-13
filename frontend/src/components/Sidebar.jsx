import React from 'react';
import { 
  LayoutDashboard, 
  Network, 
  Compass, 
  Activity, 
  Database, 
  BarChart3, 
  Settings, 
  Radio, 
  ShieldCheck, 
  ShieldAlert,
  RotateCcw,
  Layers
} from 'lucide-react';

const NAV_ITEMS = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  { id: 'edge-ai', label: 'Edge AI Intelligence', icon: ShieldAlert },
  { id: 'topology', label: 'Network Topology', icon: Network },
  { id: 'simulator', label: 'Routing Simulator', icon: Compass },
  { id: 'monitoring', label: 'Live Monitoring', icon: Activity },
  { id: 'history', label: 'Packet History', icon: Database },
  { id: 'analytics', label: 'Analytics', icon: BarChart3 },
  { id: 'settings', label: 'Settings', icon: Settings },
];

export default function Sidebar({ activeTab, onSelectTab, backendHealthy, onResetNetwork }) {
  return (
    <aside className="glass-panel sidebar">
      <div>
        {/* Brand Header */}
        <div className="sidebar-brand">
          <div className="brand-icon-leaf">
            <Radio size={22} />
          </div>
          <div>
            <h1 className="brand-text-name">NetFlow</h1>
            <span className="brand-text-tagline">INTELLIGENCE AI</span>
          </div>
        </div>

        {/* Navigation Items */}
        <nav className="sidebar-nav">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                className={`nav-link ${isActive ? 'active' : ''}`}
                onClick={() => onSelectTab(item.id)}
              >
                <Icon size={18} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
      </div>

      {/* Bottom Action & System Health Card */}
      <div className="sidebar-footer-card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
          <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
            System Core
          </span>
          <span 
            className={`status-pill ${backendHealthy ? 'delivered' : 'failed'}`}
            style={{ padding: '0.15rem 0.45rem', fontSize: '0.68rem' }}
          >
            {backendHealthy ? 'Online' : 'Offline'}
          </span>
        </div>
        <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.65rem' }}>
          FastAPI Engine & NetworkX Dijkstra Router
        </p>
        <button 
          className="btn-glass" 
          style={{ width: '100%', padding: '0.45rem', fontSize: '0.75rem', borderRadius: '10px' }}
          onClick={onResetNetwork}
          title="Restore all nodes and links to active state"
        >
          <Layers size={13} />
          <span>Reset Topology</span>
        </button>
      </div>
    </aside>
  );
}
