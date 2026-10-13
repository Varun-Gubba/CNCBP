import React, { useState } from 'react';
import { 
  Database, 
  Search, 
  CheckCircle2, 
  XCircle, 
  ArrowRight, 
  Eye, 
  FileText 
} from 'lucide-react';

export default function PacketHistoryTable({ packets = [], onSelectPacket }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');

  const filteredPackets = packets.filter((packet) => {
    const matchesSearch = 
      packet.packet_id?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      packet.source?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      packet.destination?.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesStatus = 
      statusFilter === 'ALL' || packet.status === statusFilter;

    return matchesSearch && matchesStatus;
  });

  return (
    <div className="glass-panel" style={{ padding: '1.25rem' }}>
      <div className="card-header-styled" style={{ padding: '0 0 1rem 0' }}>
        <h3 className="card-title-styled" style={{ fontSize: '1.05rem' }}>
          <Database size={18} />
          <span>Packet Activity History</span>
          <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontWeight: 500 }}>
            ({packets.length} stored)
          </span>
        </h3>

        {/* Filter & Search Bar */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
          <div style={{ position: 'relative' }}>
            <Search 
              size={14} 
              style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} 
            />
            <input
              type="text"
              placeholder="Search packet or node..."
              className="clean-input"
              style={{ paddingLeft: '2rem', height: '34px', fontSize: '0.78rem', width: '180px' }}
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            {['ALL', 'DELIVERED', 'FAILED'].map((st) => (
              <button
                key={st}
                className={statusFilter === st ? 'btn-emerald' : 'btn-glass'}
                style={{ padding: '0.25rem 0.65rem', fontSize: '0.72rem', height: '34px' }}
                onClick={() => setStatusFilter(st)}
              >
                {st}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="table-wrapper-clean">
        {filteredPackets.length === 0 ? (
          <div style={{ padding: '2.5rem', textAlign: 'center', color: 'var(--text-muted)' }}>
            <FileText size={36} color="#9ab2a3" style={{ margin: '0 auto 0.5rem auto' }} />
            <p style={{ fontWeight: 600, color: 'var(--text-main)' }}>No packet records found</p>
            <p style={{ fontSize: '0.78rem', marginTop: 2 }}>
              {packets.length === 0 
                ? 'Send a packet using the routing simulator above to view transmission logs.' 
                : 'No packets match your search and filter criteria.'}
            </p>
          </div>
        ) : (
          <table className="clean-table">
            <thead>
              <tr>
                <th>Packet ID</th>
                <th>Time (UTC)</th>
                <th>Route Path</th>
                <th>Status</th>
                <th>Cost</th>
                <th>Delay</th>
                <th>Hops</th>
                <th>Telemetry Preview</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredPackets.map((pkt) => {
                const isDelivered = pkt.status === 'DELIVERED';
                const timeString = pkt.created_at 
                  ? new Date(pkt.created_at).toLocaleTimeString() 
                  : '--';

                return (
                  <tr key={pkt.packet_id}>
                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: '#15803d' }}>
                      {pkt.packet_id}
                    </td>
                    <td style={{ fontSize: '0.75rem' }}>{timeString}</td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                        <span style={{ fontWeight: 700, color: 'var(--text-main)' }}>{pkt.source}</span>
                        <ArrowRight size={11} color="var(--text-muted)" />
                        <span style={{ fontWeight: 700, color: 'var(--text-main)' }}>{pkt.destination}</span>
                        {pkt.route && pkt.route.length > 0 && (
                          <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginLeft: 4 }}>
                            ({pkt.route.join('→')})
                          </span>
                        )}
                      </div>
                    </td>
                    <td>
                      <span className={`status-pill ${isDelivered ? 'delivered' : 'failed'}`}>
                        {isDelivered ? <CheckCircle2 size={11} /> : <XCircle size={11} />}
                        {pkt.status}
                      </span>
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                      {isDelivered ? pkt.total_cost : '--'}
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                      {isDelivered ? `${pkt.estimated_latency_ms}ms` : '--'}
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                      {isDelivered ? pkt.hop_count : '--'}
                    </td>
                    <td style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      {pkt.payload ? (
                        <span>
                          {pkt.payload.temperature_celsius}°C, {pkt.payload.humidity_percentage}%
                        </span>
                      ) : (
                        '--'
                      )}
                    </td>
                    <td>
                      <button
                        className="btn-glass"
                        style={{ padding: '0.25rem 0.55rem', fontSize: '0.72rem' }}
                        onClick={() => onSelectPacket(pkt)}
                        title="View complete packet metadata and JSON details"
                      >
                        <Eye size={12} />
                        <span>Details</span>
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
