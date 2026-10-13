import React, { useState } from 'react';
import { 
  Send, 
  Compass, 
  Sliders, 
  ArrowRight, 
  CheckCircle2, 
  AlertCircle, 
  Clock, 
  Layers 
} from 'lucide-react';

export default function RouteControlPanel({ 
  nodes = [], 
  onSimulatePacket, 
  onCalculateRouteOnly, 
  isLoading, 
  error 
}) {
  const [source, setSource] = useState('S1');
  const [destination, setDestination] = useState('SRV');
  const [customTelemetryEnabled, setCustomTelemetryEnabled] = useState(false);
  const [temp, setTemp] = useState(25.5);
  const [humidity, setHumidity] = useState(62.0);
  const [aqi, setAqi] = useState(48.0);

  const handleSimulate = (e) => {
    e.preventDefault();
    let payload = null;
    if (customTelemetryEnabled) {
      payload = {
        sensor_id: source,
        timestamp: new Date().toISOString(),
        temperature_celsius: parseFloat(temp),
        humidity_percentage: parseFloat(humidity),
        air_quality_aqi: parseFloat(aqi),
        is_simulated: true,
        notes: 'Custom simulated telemetry from NetFlow Intelligence panel',
      };
    }
    onSimulatePacket(source, destination, payload);
  };

  const handleCalculateRoute = () => {
    onCalculateRouteOnly(source, destination);
  };

  return (
    <div className="glass-panel" style={{ padding: '1.25rem' }}>
      <div className="card-header-styled" style={{ padding: '0 0 1rem 0' }}>
        <h3 className="card-title-styled" style={{ fontSize: '1.05rem' }}>
          <Compass size={18} />
          <span>Routing & Packet Simulator</span>
        </h3>
        <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
          Dijkstra Engine
        </span>
      </div>

      <form onSubmit={handleSimulate} style={{ marginTop: '0.85rem' }}>
        <div className="sim-form-row">
          <div>
            <label style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>
              Source Node
            </label>
            <select 
              className="clean-select"
              value={source}
              onChange={(e) => setSource(e.target.value)}
              disabled={isLoading}
            >
              {nodes.map((node) => (
                <option key={node.id} value={node.id}>
                  {node.id} ({node.name.split('-')[0].trim()} - {node.type})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>
              Destination Node
            </label>
            <select 
              className="clean-select"
              value={destination}
              onChange={(e) => setDestination(e.target.value)}
              disabled={isLoading}
            >
              {nodes.map((node) => (
                <option key={node.id} value={node.id}>
                  {node.id} ({node.name.split('-')[0].trim()} - {node.type})
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Custom Telemetry Accordion / Toggle */}
        <div style={{ marginBottom: '1rem' }}>
          <button
            type="button"
            className="btn-glass"
            style={{ width: '100%', fontSize: '0.78rem', padding: '0.5rem 0.85rem', justifyContent: 'space-between' }}
            onClick={() => setCustomTelemetryEnabled(!customTelemetryEnabled)}
          >
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <Sliders size={13} color="var(--brand-emerald)" />
              <span>{customTelemetryEnabled ? 'Using Custom Telemetry' : 'Using Auto Telemetry'}</span>
            </span>
            <span style={{ color: customTelemetryEnabled ? 'var(--brand-emerald)' : 'var(--text-muted)', fontWeight: 600 }}>
              {customTelemetryEnabled ? 'Custom (Active)' : 'Auto-Generate'}
            </span>
          </button>

          {customTelemetryEnabled && (
            <div 
              style={{ 
                marginTop: '0.75rem', 
                padding: '0.85rem', 
                background: '#ffffff', 
                border: '1px solid #d5e5da',
                borderRadius: '12px',
                display: 'grid',
                gridTemplateColumns: 'repeat(3, 1fr)',
                gap: '0.65rem'
              }}
            >
              <div>
                <label style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'block', marginBottom: 2 }}>Temp (°C)</label>
                <input 
                  type="number" 
                  step="0.1" 
                  className="clean-input" 
                  style={{ padding: '0.4rem 0.6rem', fontSize: '0.8rem' }}
                  value={temp} 
                  onChange={(e) => setTemp(e.target.value)} 
                />
              </div>
              <div>
                <label style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'block', marginBottom: 2 }}>Humidity (%)</label>
                <input 
                  type="number" 
                  step="0.1" 
                  className="clean-input" 
                  style={{ padding: '0.4rem 0.6rem', fontSize: '0.8rem' }}
                  value={humidity} 
                  onChange={(e) => setHumidity(e.target.value)} 
                />
              </div>
              <div>
                <label style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'block', marginBottom: 2 }}>AQI Index</label>
                <input 
                  type="number" 
                  step="0.1" 
                  className="clean-input" 
                  style={{ padding: '0.4rem 0.6rem', fontSize: '0.8rem' }}
                  value={aqi} 
                  onChange={(e) => setAqi(e.target.value)} 
                />
              </div>
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.6fr', gap: '0.75rem' }}>
          <button 
            type="button" 
            className="btn-glass"
            onClick={handleCalculateRoute}
            disabled={isLoading || source === destination}
            title="Compute shortest route using Dijkstra algorithm"
          >
            <Compass size={15} />
            <span>Find Route</span>
          </button>

          <button 
            type="submit" 
            className="btn-emerald"
            disabled={isLoading}
            title="Generate environmental packet and transmit along shortest route"
          >
            {isLoading ? (
              <span className="spinner-emerald" style={{ borderColor: 'rgba(255,255,255,0.3)', borderTopColor: '#fff' }}></span>
            ) : (
              <Send size={15} />
            )}
            <span>Send Packet & Route</span>
          </button>
        </div>
      </form>

      {/* Error Banner */}
      {error && (
        <div style={{ marginTop: '0.85rem', padding: '0.75rem', borderRadius: '10px', background: '#fef2f2', border: '1px solid #fecaca', display: 'flex', alignItems: 'center', gap: 6, color: '#dc2626', fontSize: '0.82rem' }}>
          <AlertCircle size={15} />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
}
