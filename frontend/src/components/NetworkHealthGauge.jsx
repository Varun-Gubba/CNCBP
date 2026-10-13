import React from 'react';
import { ShieldCheck, AlertTriangle } from 'lucide-react';

export default function NetworkHealthGauge({ networkData, metrics }) {
  const { nodes = [], links = [], active_nodes_count = 0, active_links_count = 0 } = networkData || {};
  const { total_packets = 0, delivery_ratio_percentage = 100 } = metrics || {};

  const totalNodes = nodes.length || 7;
  const totalLinks = links.length || 10;

  // Calculate health score honestly from operational components
  const nodeScore = totalNodes > 0 ? (active_nodes_count / totalNodes) * 50 : 50;
  const linkScore = totalLinks > 0 ? (active_links_count / totalLinks) * 25 : 25;
  const packetScore = total_packets === 0 ? 25 : (delivery_ratio_percentage / 100) * 25;

  const healthScore = Math.round(nodeScore + linkScore + packetScore);

  // SVG circular circumference
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (healthScore / 100) * circumference;

  const gaugeColor = healthScore >= 90 ? '#15803d' : healthScore >= 70 ? '#d97706' : '#dc2626';

  return (
    <div className="health-gauge-card">
      <div className="gauge-svg-wrap">
        <svg width="140" height="140" style={{ transform: 'rotate(-90deg)' }}>
          {/* Background track */}
          <circle
            cx="70"
            cy="70"
            r={radius}
            fill="transparent"
            stroke="#e2eee6"
            strokeWidth="11"
          />
          {/* Active progress arc */}
          <circle
            cx="70"
            cy="70"
            r={radius}
            fill="transparent"
            stroke={gaugeColor}
            strokeWidth="11"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            style={{ transition: 'stroke-dashoffset 0.8s ease, stroke 0.5s ease' }}
          />
        </svg>

        <div className="gauge-center-text">
          <span className="gauge-percent" style={{ color: gaugeColor }}>
            {healthScore}%
          </span>
          <span className="gauge-label">HEALTH</span>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 6, justifyContent: 'center' }}>
        {healthScore >= 90 ? (
          <ShieldCheck size={16} color="#15803d" />
        ) : (
          <AlertTriangle size={16} color={gaugeColor} />
        )}
        <span style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--text-main)' }}>
          {healthScore >= 90 
            ? 'Optimal Topology' 
            : healthScore >= 70 
            ? 'Degraded Performance' 
            : 'Subsystem Outage'}
        </span>
      </div>

      <p style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginTop: '0.35rem' }}>
        {active_nodes_count}/{totalNodes} Nodes • {active_links_count}/{totalLinks} Links Active
      </p>
    </div>
  );
}
