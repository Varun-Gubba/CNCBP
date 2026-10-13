import React from 'react';
import { Bell, AlertTriangle, CheckCircle2, AlertOctagon, Info } from 'lucide-react';

export default function SmartAlerts({ alerts = [] }) {
  return (
    <div className="glass-panel" style={{ padding: '1.25rem' }}>
      <div className="card-header-styled" style={{ padding: '0 0 0.85rem 0' }}>
        <h3 className="card-title-styled" style={{ fontSize: '1.05rem' }}>
          <Bell size={18} />
          <span>Smart Alerts</span>
        </h3>
        <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
          Real-time Event Stream
        </span>
      </div>

      <div className="smart-alerts-list" style={{ marginTop: '0.75rem' }}>
        {alerts.length === 0 ? (
          <div style={{ padding: '1.25rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.82rem' }}>
            All systems nominal. No alerts generated.
          </div>
        ) : (
          alerts.slice(0, 4).map((alert, idx) => (
            <div key={idx} className={`alert-item-card ${alert.type}`}>
              {alert.type === 'error' ? (
                <AlertOctagon size={16} color="#dc2626" style={{ marginTop: 2, flexShrink: 0 }} />
              ) : alert.type === 'warn' ? (
                <AlertTriangle size={16} color="#d97706" style={{ marginTop: 2, flexShrink: 0 }} />
              ) : (
                <CheckCircle2 size={16} color="#15803d" style={{ marginTop: 2, flexShrink: 0 }} />
              )}
              <div style={{ flex: 1 }}>
                <div className="alert-title">{alert.title}</div>
                <div className="alert-time">{alert.time}</div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
