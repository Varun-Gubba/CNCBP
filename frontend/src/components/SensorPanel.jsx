import React from 'react';
import { 
  Radio, 
  Thermometer, 
  Droplets, 
  Wind, 
  Clock, 
  Info,
  CheckCircle2,
  AlertTriangle
} from 'lucide-react';

export default function SensorPanel({ sensors = [], latestTelemetryBySensor = {} }) {
  const getSensorData = (sensorId) => {
    if (latestTelemetryBySensor[sensorId]) {
      return latestTelemetryBySensor[sensorId];
    }
    if (sensorId === 'S1') {
      return {
        temperature_celsius: 24.8,
        humidity_percentage: 61.5,
        air_quality_aqi: 45.0,
        timestamp: new Date().toISOString(),
        is_simulated: true,
      };
    }
    return {
      temperature_celsius: 27.2,
      humidity_percentage: 55.0,
      air_quality_aqi: 52.0,
      timestamp: new Date().toISOString(),
      is_simulated: true,
    };
  };

  const getAqiStatus = (aqi) => {
    if (aqi <= 50) return { label: 'Good', color: '#15803d', bg: '#f0fdf4' };
    if (aqi <= 100) return { label: 'Moderate', color: '#d97706', bg: '#fffbeb' };
    return { label: 'Unhealthy', color: '#dc2626', bg: '#fef2f2' };
  };

  return (
    <div className="glass-panel" style={{ padding: '1.25rem' }}>
      <div className="card-header-styled" style={{ padding: '0 0 1rem 0' }}>
        <h3 className="card-title-styled" style={{ fontSize: '1.05rem' }}>
          <Radio size={18} />
          <span>Environmental Sensor Nodes</span>
        </h3>
        <span 
          style={{ 
            fontSize: '0.72rem', 
            color: 'var(--text-muted)', 
            display: 'flex', 
            alignItems: 'center', 
            gap: 4 
          }}
          title="Telemetry readings are simulated in software"
        >
          <Info size={12} />
          <span>Simulated Telemetry</span>
        </span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginTop: '1rem' }}>
        {sensors.map((sensor) => {
          const telemetry = getSensorData(sensor.id);
          const aqiStatus = getAqiStatus(telemetry.air_quality_aqi || 50);
          const isActive = sensor.status === 'active';

          return (
            <div 
              key={sensor.id} 
              style={{
                background: '#ffffff',
                border: '1px solid #d5e5da',
                borderRadius: '14px',
                padding: '1.1rem',
                display: 'flex',
                flexDirection: 'column',
                gap: '0.65rem',
                boxShadow: '0 2px 8px rgba(0,0,0,0.02)'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span 
                    style={{ 
                      fontSize: '0.75rem', 
                      fontWeight: 800, 
                      padding: '0.2rem 0.5rem', 
                      borderRadius: '6px',
                      background: '#e0f2fe',
                      color: '#0284c7'
                    }}
                  >
                    {sensor.id}
                  </span>
                  <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-main)' }}>
                    {sensor.name.split('-')[1]?.trim() || sensor.name}
                  </span>
                </div>
                <span 
                  style={{ 
                    fontSize: '0.72rem', 
                    color: isActive ? '#15803d' : '#dc2626',
                    fontWeight: 700,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 3
                  }}
                >
                  {isActive ? <CheckCircle2 size={11} /> : <AlertTriangle size={11} />}
                  {isActive ? 'Active' : 'Offline'}
                </span>
              </div>

              {/* Temperature */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.82rem', padding: '0.35rem 0', borderBottom: '1px solid #f1f5f3' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--text-muted)' }}>
                  <Thermometer size={14} color="#ef4444" />
                  <span>Temperature</span>
                </span>
                <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--text-main)' }}>
                  {telemetry.temperature_celsius}°C
                </span>
              </div>

              {/* Humidity */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.82rem', padding: '0.35rem 0', borderBottom: '1px solid #f1f5f3' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--text-muted)' }}>
                  <Droplets size={14} color="#0284c7" />
                  <span>Humidity</span>
                </span>
                <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--text-main)' }}>
                  {telemetry.humidity_percentage}%
                </span>
              </div>

              {/* Air Quality */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.82rem', padding: '0.35rem 0' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--text-muted)' }}>
                  <Wind size={14} color={aqiStatus.color} />
                  <span>Air Quality</span>
                </span>
                <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                  <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--text-main)' }}>
                    {telemetry.air_quality_aqi} AQI
                  </span>
                  <span 
                    style={{ 
                      fontSize: '0.65rem', 
                      padding: '0.1rem 0.4rem', 
                      borderRadius: '4px',
                      background: aqiStatus.bg,
                      color: aqiStatus.color,
                      fontWeight: 700
                    }}
                  >
                    {aqiStatus.label}
                  </span>
                </div>
              </div>

              {/* Timestamp */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: '0.68rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                <Clock size={11} />
                <span>
                  Updated {telemetry.timestamp ? new Date(telemetry.timestamp).toLocaleTimeString() : 'Just now'}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
