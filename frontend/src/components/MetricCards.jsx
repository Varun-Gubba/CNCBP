import React from 'react';
import { 
  Activity, 
  CheckCircle2, 
  XCircle, 
  Clock, 
  TrendingUp, 
  TrendingDown,
  Layers
} from 'lucide-react';

export default function MetricCards({ metrics }) {
  const {
    total_packets = 0,
    delivered_packets = 0,
    failed_packets = 0,
    delivery_ratio_percentage = 0,
    average_latency_ms = 0,
    average_hop_count = 0,
  } = metrics || {};

  const cards = [
    {
      label: 'TOTAL PACKETS',
      value: total_packets,
      unit: 'pkts',
      trend: total_packets > 0 ? '+100% created' : 'Idle session',
      trendType: 'neutral',
      icon: Activity,
      iconColor: '#15803d',
      iconBg: 'rgba(21, 128, 61, 0.1)',
      note: 'Total transmitted & routed',
    },
    {
      label: 'DELIVERED PACKETS',
      value: delivered_packets,
      unit: 'pkts',
      trend: `${delivery_ratio_percentage}% success`,
      trendType: 'positive',
      icon: CheckCircle2,
      iconColor: '#15803d',
      iconBg: 'rgba(21, 128, 61, 0.1)',
      note: 'Delivered to target node',
    },
    {
      label: 'FAILED PACKETS',
      value: failed_packets,
      unit: 'pkts',
      trend: failed_packets > 0 ? `${failed_packets} packet drops` : 'Zero errors',
      trendType: failed_packets > 0 ? 'alert' : 'positive',
      icon: XCircle,
      iconColor: failed_packets > 0 ? '#dc2626' : '#15803d',
      iconBg: failed_packets > 0 ? 'rgba(220, 38, 38, 0.1)' : 'rgba(21, 128, 61, 0.1)',
      note: 'Outages or unreachable',
    },
    {
      label: 'AVERAGE LATENCY',
      value: average_latency_ms,
      unit: 'ms',
      trend: `${average_hop_count} avg hops`,
      trendType: 'positive',
      icon: Clock,
      iconColor: '#0d9488',
      iconBg: 'rgba(13, 148, 136, 0.1)',
      note: 'Cumulative link path delay',
    },
  ];

  return (
    <section className="metrics-row">
      {cards.map((card, idx) => {
        const Icon = card.icon;
        return (
          <div key={idx} className="glass-panel clean-metric-card">
            <div className="metric-top-bar">
              <span className="metric-label-clean">{card.label}</span>
              <div 
                className="metric-icon-circle"
                style={{ backgroundColor: card.iconBg, color: card.iconColor }}
              >
                <Icon size={19} />
              </div>
            </div>

            <div>
              <span className="metric-val-main">{card.value}</span>
              <span className="metric-val-unit">{card.unit}</span>
            </div>

            <div className="metric-footer-note">
              <span className={`trend-badge ${card.trendType}`}>
                {card.trend}
              </span>
              <span>•</span>
              <span>{card.note}</span>
            </div>
          </div>
        );
      })}
    </section>
  );
}
