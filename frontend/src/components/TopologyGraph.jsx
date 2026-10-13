import React, { useMemo } from 'react';
import { 
  ReactFlow, 
  Controls, 
  MiniMap, 
  Background 
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Network, RotateCcw } from 'lucide-react';
import NetworkNode from './NetworkNode';
import { DEFAULT_NODE_POSITIONS } from '../constants';

const nodeTypes = {
  customNetworkNode: NetworkNode,
};

export default function TopologyGraph({ 
  networkData, 
  selectedRoute = [], 
  onToggleNodeStatus,
  onResetTopology 
}) {
  const { nodes = [], links = [], active_nodes_count = 0, active_links_count = 0 } = networkData || {};

  // Check if an edge between source and destination is in the selected Dijkstra route
  const isEdgeInRoute = useMemo(() => {
    return (source, destination) => {
      if (!selectedRoute || selectedRoute.length < 2) return false;
      for (let i = 0; i < selectedRoute.length - 1; i++) {
        const u = selectedRoute[i];
        const v = selectedRoute[i + 1];
        if ((u === source && v === destination) || (u === destination && v === source)) {
          return true;
        }
      }
      return false;
    };
  }, [selectedRoute]);

  // Construct React Flow Nodes
  const flowNodes = useMemo(() => {
    return nodes.map((node) => {
      const position = DEFAULT_NODE_POSITIONS[node.id] || { x: 100, y: 100 };
      const isInRoute = selectedRoute.includes(node.id);

      return {
        id: node.id,
        type: 'customNetworkNode',
        position,
        data: {
          id: node.id,
          name: node.name,
          type: node.type,
          status: node.status,
          isInRoute,
          onToggleStatus: onToggleNodeStatus,
        },
      };
    });
  }, [nodes, selectedRoute, onToggleNodeStatus]);

  // Construct React Flow Edges
  const flowEdges = useMemo(() => {
    return links.map((link, index) => {
      const inRoute = isEdgeInRoute(link.source, link.destination);
      const isLinkActive = link.status === 'active';

      let edgeStyle = {
        stroke: '#84a98c',
        strokeWidth: 2,
      };

      if (!isLinkActive) {
        edgeStyle = {
          stroke: '#dc2626',
          strokeDasharray: '5,5',
          strokeWidth: 2,
          opacity: 0.6,
        };
      } else if (inRoute) {
        edgeStyle = {
          stroke: '#15803d',
          strokeWidth: 3.5,
          filter: 'drop-shadow(0 2px 8px rgba(21, 128, 61, 0.4))',
        };
      }

      const labelContent = isLinkActive 
        ? `C:${link.cost} | ${link.delay}ms` 
        : 'DOWN';

      return {
        id: `edge-${link.source}-${link.destination}-${index}`,
        source: link.source,
        target: link.destination,
        animated: inRoute && isLinkActive,
        style: edgeStyle,
        label: (
          <div className={`netflow-edge-label ${inRoute ? 'in-route' : ''}`}>
            {labelContent}
          </div>
        ),
      };
    });
  }, [links, isEdgeInRoute]);

  return (
    <div className="glass-panel" style={{ overflow: 'hidden' }}>
      <div className="card-header-styled">
        <h2 className="card-title-styled">
          <Network size={20} />
          <span>Live Network Topology</span>
        </h2>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
          <span 
            className="status-pill delivered" 
            style={{ fontSize: '0.74rem' }}
          >
            {active_nodes_count}/{nodes.length} Nodes Active
          </span>
          <span 
            className="status-pill delivered" 
            style={{ fontSize: '0.74rem' }}
          >
            {active_links_count}/{links.length} Links Active
          </span>
          <button 
            className="btn-glass"
            style={{ padding: '0.35rem 0.75rem', fontSize: '0.75rem' }}
            onClick={onResetTopology}
            title="Reset topology to default state"
          >
            <RotateCcw size={13} />
            <span>Reset</span>
          </button>
        </div>
      </div>

      <div className="topology-container">
        <ReactFlow
          key={`flow-${nodes.length}`}
          nodes={flowNodes}
          edges={flowEdges}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.15 }}
          defaultViewport={{ x: 20, y: 20, zoom: 0.85 }}
          attributionPosition="bottom-left"
          minZoom={0.4}
          maxZoom={1.5}
          proOptions={{ hideAttribution: true }}
        >
          <Background color="#9fc9ab" gap={22} size={1.2} />
          <Controls showInteractive={false} />
          <MiniMap 
            nodeStrokeColor="#15803d"
            nodeColor="#ffffff"
            maskColor="rgba(215, 235, 220, 0.65)"
            style={{
              backgroundColor: '#ffffff',
              border: '1px solid #d5e5da',
              borderRadius: '10px',
            }}
          />
        </ReactFlow>
      </div>
    </div>
  );
}
