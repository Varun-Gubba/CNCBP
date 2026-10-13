/**
 * Layout and Styling Metadata for NetFlow Intelligence
 */

export const DEFAULT_NODE_POSITIONS = {
  S1: { x: 50, y: 70 },
  S2: { x: 50, y: 320 },
  R1: { x: 260, y: 50 },
  R2: { x: 280, y: 195 },
  R3: { x: 260, y: 340 },
  G1: { x: 510, y: 195 },
  SRV: { x: 740, y: 195 },
};

export const NODE_TYPE_METADATA = {
  sensor: {
    label: 'Sensor',
    color: '#0284c7', // Sky Blue
    border: '#bae6fd',
    lightBg: '#f0f9ff',
  },
  router: {
    label: 'Router',
    color: '#15803d', // Forest Emerald
    border: '#bbf7d0',
    lightBg: '#f0fdf4',
  },
  gateway: {
    label: 'Gateway',
    color: '#d97706', // Amber
    border: '#fde68a',
    lightBg: '#fffbeb',
  },
  server: {
    label: 'Central Server',
    color: '#4f46e5', // Indigo
    border: '#c7d2fe',
    lightBg: '#eef2ff',
  },
};
