import React from 'react';
import { BarChart3, TrendingUp, Clock, CheckCircle2, XCircle } from 'lucide-react';

export default function PerformanceAnalytics({ packets = [], metrics = {} }) {
  const deliveredPackets = packets.filter((p) => p.status === 'DELIVERED');
  const recentDelivered = deliveredPackets.slice(0, 10).reverse();

  // Max latency for scaling bar chart
  const maxLatency = Math.max(...recentDelivered.map((p) => p.estimated_latency_ms || 0), 30);

  const {
    total_packets = 0,
    delivered_packets = 0,
    failed_packets = 0,
    delivery_ratio_percentage = 0,
    average_latency_ms = 0,
    average_hop_count = 0,
  } = metrics;

  return (
    <div className="glass-panel" style={{ padding: '1.25rem' }}>
      <div className="card-header-styled" style={{ padding: '0 0 1rem 0' }}>
        <h3 className="card-title-styled" style={{ fontSize: '1.05rem' }}>
          <BarChart3 size={18} />
          <span>Performance Analytics</span>
        </h3>
        <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
          Real-time API Analytics
        </span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '1.25rem', marginTop: '1rem' }}>
        {/* Latency History Chart */}
        <div style={{ background: '#ffffff', borderRadius: '12px', padding: '1rem', border: '1px solid #d5e5da' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)' }}>
              RECENT PACKET LATENCY (ms)
            </span>
            <span style={{ fontSize: '0.72rem', color: '#0d9488', fontWeight: 600 }}>
              Avg: {average_latency_ms} ms
            </span>
          </div>

          {recentDelivered.length === 0 ? (
            <div style={{ height: '120px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
              Transmit packets to generate latency timeline
            </div>
          ) : (
            <div style={{ height: '120px', display: 'flex', alignItems: 'flex-end', gap: '8px', paddingBottom: '4px', borderBottom: '1px solid #e1eee5' }}>
              {recentDelivered.map((p, idx) => {
                const heightPct = Math.max((p.estimated_latency_ms / maxLatency) * 100, 15);
                return (
                  <div key={idx} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', height: '100%', justifyContent: 'flex-end' }}>
                    <span style={{ fontSize: '0.62rem', color: 'var(--text-muted)', marginBottom: 2 }}>
                      {p.estimated_latency_ms}
                    </span>
                    <div 
                      style={{ 
                        width: '100%', 
                        height: `${heightPct}%`, 
                        background: 'linear-gradient(180deg, #10b981, #059669)',
                        borderRadius: '4px 4px 0 0',
                        transition: 'height 0.4s ease'
                      }}
                      title={`${p.packet_id}: ${p.estimated_latency_ms}ms (${p.hop_count} hops)`}
                    />
                    <span style={{ fontSize: '0.58rem', color: 'var(--text-muted)', marginTop: 2, whiteSpace: 'nowrap' }}>
                      P{idx + 1}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Delivery Success Ratio Breakdown */}
        <div style={{ background: '#ffffff', borderRadius: '12px', padding: '1rem', border: '1px solid #d5e5da', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', display: 'block', marginBottom: '0.5rem' }}>
              DELIVERY RATIO BREAKDOWN
            </span>
            
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, margin: '0.75rem 0' }}>
              <div style={{ flex: delivered_packets || 1, height: '12px', borderRadius: '6px 0 0 6px', background: '#16a34a' }} />
              <div style={{ flex: failed_packets || 0, height: '12px', borderRadius: '0 6px 6px 0', background: failed_packets > 0 ? '#dc2626' : '#e2e8f0' }} />
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: 4, color: '#16a34a', fontWeight: 600 }}>
              <CheckCircle2 size={12} /> {delivered_packets} Delivered ({delivery_ratio_percentage}%)
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 4, color: '#dc2626', fontWeight: 600 }}>
              <XCircle size={12} /> {failed_packets} Failed
            </span>
          </div>

          <div style={{ marginTop: '0.5rem', paddingTop: '0.5rem', borderTop: '1px solid #e1eee5', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
            Average Hop Count: <strong style={{ color: 'var(--text-main)' }}>{average_hop_count} hops</strong>
          </div>
        </div>
      </div>
    </div>
  );
}
