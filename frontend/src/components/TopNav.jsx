import React, { useState } from 'react';
import { 
  Search, 
  Bell, 
  RefreshCw, 
  Wifi, 
  WifiOff, 
  CheckCircle2, 
  AlertTriangle, 
  X,
  Calendar
} from 'lucide-react';

export default function TopNav({ 
  searchQuery, 
  onSearchChange, 
  wsConnected, 
  onRefresh, 
  isRefreshing,
  alerts = [] 
}) {
  const [showNotifications, setShowNotifications] = useState(false);

  const currentDate = new Date().toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });

  return (
    <header className="glass-panel top-navbar">
      {/* Search Input */}
      <div className="search-box">
        <Search size={16} color="var(--text-muted)" />
        <input 
          type="text" 
          placeholder="Search nodes, routes, packets..."
          className="search-input"
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
        />
      </div>

      {/* Right Controls */}
      <div className="top-navbar-actions">
        {/* Date Display */}
        <div className="nav-pill-badge" style={{ display: 'none', md: 'flex' }}>
          <Calendar size={13} />
          <span>{currentDate}</span>
        </div>

        {/* Live Stream Status */}
        <div className={`nav-pill-badge ${wsConnected ? 'live' : ''}`}>
          {wsConnected ? <span className="live-dot"></span> : <WifiOff size={13} color="var(--accent-amber)" />}
          <span>{wsConnected ? 'Live Telemetry' : 'Polling'}</span>
        </div>

        {/* Refresh Action */}
        <button 
          className="icon-button"
          onClick={onRefresh}
          disabled={isRefreshing}
          title="Refresh metrics, network, and packet history"
        >
          <RefreshCw size={16} className={isRefreshing ? 'spinner-emerald' : ''} />
        </button>

        {/* Notifications Bell */}
        <div style={{ position: 'relative' }}>
          <button 
            className="icon-button"
            onClick={() => setShowNotifications(!showNotifications)}
            title="Smart Network Alerts"
          >
            <Bell size={16} />
            {alerts.length > 0 && (
              <span 
                style={{ 
                  position: 'absolute', 
                  top: 4, 
                  right: 4, 
                  width: 8, 
                  height: 8, 
                  borderRadius: '50%', 
                  background: 'var(--brand-emerald)' 
                }}
              />
            )}
          </button>

          {/* Notifications Popover Dropdown */}
          {showNotifications && (
            <div className="notif-popover">
              <div style={{ padding: '0.85rem 1rem', borderBottom: '1px solid #e2eee6', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontWeight: 700, fontSize: '0.88rem', color: 'var(--text-main)' }}>
                  Smart Alerts ({alerts.length})
                </span>
                <button 
                  style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}
                  onClick={() => setShowNotifications(false)}
                >
                  <X size={15} />
                </button>
              </div>

              <div style={{ maxHeight: '260px', overflowY: 'auto', padding: '0.5rem' }}>
                {alerts.length === 0 ? (
                  <p style={{ padding: '1rem', fontSize: '0.8rem', color: 'var(--text-muted)', textAlign: 'center' }}>
                    No critical network events detected.
                  </p>
                ) : (
                  alerts.map((alert, idx) => (
                    <div 
                      key={idx}
                      style={{ 
                        padding: '0.65rem 0.75rem', 
                        borderRadius: '8px', 
                        background: alert.type === 'error' ? '#fef2f2' : alert.type === 'warn' ? '#fffbeb' : '#f0fdf4',
                        marginBottom: '0.35rem',
                        fontSize: '0.78rem'
                      }}
                    >
                      <div style={{ fontWeight: 600, color: 'var(--text-main)' }}>{alert.title}</div>
                      <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: 2 }}>{alert.time}</div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        {/* User / Reviewer Badge */}
        <div className="user-profile-badge">
          <div className="avatar-initials">NF</div>
          <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.1 }}>
            <span style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-main)' }}>Operator</span>
            <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>Project Review</span>
          </div>
        </div>
      </div>
    </header>
  );
}
