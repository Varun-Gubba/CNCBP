import React from 'react';
import { X, CheckCircle2, XCircle, Code } from 'lucide-react';

export default function PacketDetailsModal({ packet, onClose }) {
  if (!packet) return null;

  const isDelivered = packet.status === 'DELIVERED';

  return (
    <div className="modal-backdrop-clean" onClick={onClose}>
      <div className="modal-card-clean" onClick={(e) => e.stopPropagation()}>
        <button 
          style={{ position: 'absolute', top: '1.25rem', right: '1.25rem', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }} 
          onClick={onClose}
        >
          <X size={20} />
        </button>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: '1.25rem' }}>
          <h3 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.35rem', fontWeight: 700, color: 'var(--text-main)' }}>
            Packet Inspection
          </h3>
          <span className={`status-pill ${isDelivered ? 'delivered' : 'failed'}`}>
            {isDelivered ? <CheckCircle2 size={11} /> : <XCircle size={11} />}
            {packet.status}
          </span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.85rem', marginBottom: '1.25rem' }}>
          <div style={{ background: '#f8faf9', padding: '0.85rem', borderRadius: '12px', border: '1px solid #e1eee5' }}>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'block', fontWeight: 600 }}>Packet ID</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: '#15803d', fontSize: '0.95rem' }}>{packet.packet_id}</span>
          </div>
          <div style={{ background: '#f8faf9', padding: '0.85rem', borderRadius: '12px', border: '1px solid #e1eee5' }}>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'block', fontWeight: 600 }}>Created At</span>
            <span style={{ fontSize: '0.82rem', color: 'var(--text-main)', fontWeight: 600 }}>{new Date(packet.created_at).toLocaleString()}</span>
          </div>
          <div style={{ background: '#f8faf9', padding: '0.85rem', borderRadius: '12px', border: '1px solid #e1eee5' }}>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'block', fontWeight: 600 }}>Source ➔ Destination</span>
            <span style={{ fontWeight: 700, color: 'var(--text-main)' }}>{packet.source} ➔ {packet.destination}</span>
          </div>
          <div style={{ background: '#f8faf9', padding: '0.85rem', borderRadius: '12px', border: '1px solid #e1eee5' }}>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'block', fontWeight: 600 }}>Transmission Metrics</span>
            <span style={{ fontSize: '0.82rem', color: 'var(--text-main)', fontWeight: 600 }}>
              Cost: {packet.total_cost} | {packet.estimated_latency_ms}ms | {packet.hop_count} hops
            </span>
          </div>
        </div>

        {/* Selected Route Breadcrumbs */}
        <div style={{ marginBottom: '1.25rem' }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: 4, fontWeight: 600 }}>
            Traversed Route:
          </span>
          {packet.route && packet.route.length > 0 ? (
            <div className="route-breadcrumbs-list" style={{ margin: 0 }}>
              {packet.route.map((node, idx) => (
                <span key={idx} className="route-step-pill">{node}</span>
              ))}
            </div>
          ) : (
            <span style={{ color: '#dc2626', fontSize: '0.85rem', fontWeight: 500 }}>
              No route traversed ({packet.failure_reason || 'Routing failed'})
            </span>
          )}
        </div>

        {/* Environmental Payload Breakdown */}
        {packet.payload && (
          <div style={{ marginBottom: '1.25rem', background: '#f0fdf4', padding: '0.85rem', borderRadius: '12px', border: '1px solid #bbf7d0' }}>
            <span style={{ fontSize: '0.78rem', fontWeight: 700, color: '#15803d', display: 'block', marginBottom: 4 }}>
              Environmental Telemetry Payload
            </span>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 6, fontSize: '0.82rem' }}>
              <div>Temp: <strong>{packet.payload.temperature_celsius}°C</strong></div>
              <div>Humidity: <strong>{packet.payload.humidity_percentage}%</strong></div>
              <div>AQI: <strong>{packet.payload.air_quality_aqi || 'N/A'}</strong></div>
            </div>
          </div>
        )}

        {/* Raw JSON viewer */}
        <div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 4, marginBottom: 4, fontWeight: 600 }}>
            <Code size={13} />
            <span>Raw Packet JSON:</span>
          </span>
          <pre 
            style={{ 
              background: '#14281d', 
              padding: '0.85rem', 
              borderRadius: '8px', 
              fontSize: '0.74rem', 
              fontFamily: 'var(--font-mono)', 
              color: '#d1fae5',
              maxHeight: '160px',
              overflowY: 'auto'
            }}
          >
            {JSON.stringify(packet, null, 2)}
          </pre>
        </div>
      </div>
    </div>
  );
}
