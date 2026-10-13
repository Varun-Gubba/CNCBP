import React from 'react';
import { Compass, ArrowRight, Clock, Layers, DollarSign, AlertCircle, CheckCircle2 } from 'lucide-react';

export default function RoutingInsightsCard({ routeData, packetData, error }) {
  const isPacket = Boolean(packetData);
  const data = routeData || packetData;
  const isFailed = packetData?.status === 'FAILED' || (error && !data);

  return (
    <div className="glass-panel" style={{ padding: '1.25rem' }}>
      <div className="card-header-styled" style={{ padding: '0 0 0.85rem 0' }}>
        <h3 className="card-title-styled" style={{ fontSize: '1.05rem' }}>
          <Compass size={18} />
          <span>Routing Insights</span>
        </h3>
        {data?.route && data.route.length > 0 && (
          <span className="status-pill delivered" style={{ fontSize: '0.72rem' }}>
            <CheckCircle2 size={11} />
            Dijkstra Optimal
          </span>
        )}
      </div>

      {!data && !error ? (
        <div style={{ padding: '1.5rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
          Select source and destination nodes to calculate shortest path insights.
        </div>
      ) : isFailed ? (
        <div className="insights-result-box failed">
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#dc2626', fontWeight: 600, fontSize: '0.88rem' }}>
            <AlertCircle size={16} />
            <span>Path Unreachable / Inactive</span>
          </div>
          <p style={{ fontSize: '0.8rem', color: '#b91c1c', marginTop: '0.4rem' }}>
            {packetData?.failure_reason || error || 'No active route exists between the selected nodes.'}
          </p>
        </div>
      ) : (
        <div className="insights-result-box">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
              Traversed Path ({data.source} ➔ {data.destination})
            </span>
            {packetData?.packet_id && (
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                {packetData.packet_id}
              </span>
            )}
          </div>

          {/* Breadcrumbs */}
          <div className="route-breadcrumbs-list">
            {data.route?.map((nodeId, idx) => {
              const isSensor = nodeId.startsWith('S') && nodeId !== 'SRV';
              const isServer = nodeId === 'SRV';
              return (
                <React.Fragment key={idx}>
                  <span className={`route-step-pill ${isServer ? 'server' : isSensor ? 'sensor' : ''}`}>
                    {nodeId}
                  </span>
                  {idx < data.route.length - 1 && (
                    <ArrowRight size={13} color="var(--text-muted)" />
                  )}
                </React.Fragment>
              );
            })}
          </div>

          {/* Three Key Metrics */}
          <div className="insights-stats-grid">
            <div className="insight-metric">
              <span className="label">Total Cost</span>
              <span className="value" style={{ color: '#15803d' }}>
                {data.total_cost ?? 0.0}
              </span>
            </div>
            <div className="insight-metric">
              <span className="label">Hop Count</span>
              <span className="value" style={{ color: '#4f46e5' }}>
                {data.hop_count ?? 0} hops
              </span>
            </div>
            <div className="insight-metric">
              <span className="label">Est. Latency</span>
              <span className="value" style={{ color: '#0d9488' }}>
                {data.estimated_latency_ms ?? 0.0} ms
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
