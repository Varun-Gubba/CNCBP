import React from 'react';
import { Handle, Position } from '@xyflow/react';
import { 
  Radio, 
  Cpu, 
  Share2, 
  Server, 
  Power,
  CheckCircle2,
  AlertTriangle 
} from 'lucide-react';
import { NODE_TYPE_METADATA } from '../constants';

export default function NetworkNode({ data }) {
  const { 
    id, 
    name, 
    type = 'router', 
    status = 'active', 
    isInRoute = false, 
    onToggleStatus 
  } = data;

  const meta = NODE_TYPE_METADATA[type] || NODE_TYPE_METADATA.router;
  const isActive = status === 'active';

  const getTypeIcon = () => {
    switch (type) {
      case 'sensor':
        return <Radio size={12} />;
      case 'gateway':
        return <Share2 size={12} />;
      case 'server':
        return <Server size={12} />;
      default:
        return <Cpu size={12} />;
    }
  };

  const handleToggle = (e) => {
    e.stopPropagation();
    if (onToggleStatus) {
      const newStatus = isActive ? 'inactive' : 'active';
      onToggleStatus(id, newStatus);
    }
  };

  return (
    <div 
      className={`netflow-node ${isInRoute ? 'in-route' : ''} ${!isActive ? 'inactive' : ''}`}
      style={{
        '--node-color': meta.color,
        '--node-border': isInRoute ? '#15803d' : meta.border,
        '--node-light-bg': meta.lightBg,
      }}
    >
      {/* Handles on four sides for multi-hop graph connectivity */}
      <Handle type="target" position={Position.Left} id="left-in" style={{ opacity: 0 }} />
      <Handle type="source" position={Position.Right} id="right-out" style={{ opacity: 0 }} />
      <Handle type="target" position={Position.Top} id="top-in" style={{ opacity: 0 }} />
      <Handle type="source" position={Position.Bottom} id="bottom-out" style={{ opacity: 0 }} />

      <div className="netflow-node-header">
        <span className="node-title-code">{id}</span>
        <span className="node-badge-type">
          {getTypeIcon()}
          <span>{meta.label}</span>
        </span>
      </div>

      <div className="node-label-desc" title={name}>
        {name}
      </div>

      <div className="node-controls-bar">
        <span 
          className="node-status-text"
          style={{ color: isActive ? '#15803d' : '#dc2626' }}
        >
          {isActive ? <CheckCircle2 size={11} /> : <AlertTriangle size={11} />}
          {isActive ? 'Active' : 'Offline'}
        </span>

        <button 
          className="node-outage-btn"
          onClick={handleToggle}
          title={isActive ? `Disable ${id} to simulate failure` : `Enable ${id}`}
        >
          <Power size={10} style={{ marginRight: 2, verticalAlign: -1 }} />
          {isActive ? 'Fail' : 'Up'}
        </button>
      </div>
    </div>
  );
}
