"""
Local Queue Persistence for Edge Operation During Network Outages.
Uses Python's standard sqlite3 to store pending alerts locally on the simulated edge node,
ensuring offline alerts persist across application restarts.
"""

import json
import os
import sqlite3
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone


class EdgeQueuePersistence:
    """
    SQLite-backed persistent FIFO queue for an edge node.
    Stores generated alerts waiting for server transmission.
    Prevents duplicates by primary key on event_id.
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            # Default to backend directory
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(base_dir, "edge_buffer.db")
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS edge_alerts (
                    event_id TEXT PRIMARY KEY,
                    sensor_id TEXT NOT NULL,
                    location TEXT NOT NULL,
                    hazard_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    risk_score REAL NOT NULL,
                    confidence_score REAL NOT NULL,
                    lifecycle_state TEXT NOT NULL,
                    detected_anomalies TEXT NOT NULL,
                    contributing_measurements TEXT NOT NULL,
                    explanation TEXT NOT NULL,
                    recommended_action TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    synced INTEGER NOT NULL DEFAULT 0,
                    synced_at TEXT,
                    delivery_attempts INTEGER NOT NULL DEFAULT 0,
                    route_used TEXT,
                    packet_id TEXT,
                    delivery_status TEXT DEFAULT 'QUEUED'
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sensor_synced 
                ON edge_alerts(sensor_id, synced)
            """)
            conn.commit()

    def enqueue_alert(self, alert_dict: Dict[str, Any]) -> bool:
        """
        Inserts alert into queue.
        If event_id already exists, ignores to prevent duplicate records.
        Returns True if inserted, False if duplicate.
        """
        event_id = alert_dict["event_id"]
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT event_id FROM edge_alerts WHERE event_id = ?", (event_id,))
            if cursor.fetchone() is not None:
                # Already exists, avoid duplicate
                return False

            conn.execute("""
                INSERT INTO edge_alerts (
                    event_id, sensor_id, location, hazard_type, severity,
                    risk_score, confidence_score, lifecycle_state,
                    detected_anomalies, contributing_measurements,
                    explanation, recommended_action, created_at, synced,
                    delivery_attempts, delivery_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event_id,
                alert_dict["sensor_id"],
                alert_dict.get("location", "Unknown Location"),
                alert_dict["hazard_type"],
                alert_dict["severity"],
                float(alert_dict["risk_score"]),
                float(alert_dict["confidence_score"]),
                alert_dict["lifecycle_state"],
                json.dumps(alert_dict.get("detected_anomalies", [])),
                json.dumps(alert_dict.get("contributing_measurements", {})),
                alert_dict["explanation"],
                alert_dict["recommended_action"],
                alert_dict["created_at"],
                1 if alert_dict.get("synced", False) else 0,
                int(alert_dict.get("delivery_attempts", 0)),
                alert_dict.get("delivery_status", "QUEUED"),
            ))
            conn.commit()
            return True

    def get_pending_alerts(self, sensor_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns unsynced alerts ordered by creation time (FIFO)."""
        with self._get_connection() as conn:
            if sensor_id:
                cursor = conn.execute(
                    "SELECT * FROM edge_alerts WHERE sensor_id = ? AND synced = 0 ORDER BY created_at ASC",
                    (sensor_id,)
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM edge_alerts WHERE synced = 0 ORDER BY created_at ASC"
                )
            rows = cursor.fetchall()

        results = []
        for r in rows:
            results.append({
                "event_id": r["event_id"],
                "sensor_id": r["sensor_id"],
                "location": r["location"],
                "hazard_type": r["hazard_type"],
                "severity": r["severity"],
                "risk_score": r["risk_score"],
                "confidence_score": r["confidence_score"],
                "lifecycle_state": r["lifecycle_state"],
                "detected_anomalies": json.loads(r["detected_anomalies"]),
                "contributing_measurements": json.loads(r["contributing_measurements"]),
                "explanation": r["explanation"],
                "recommended_action": r["recommended_action"],
                "created_at": r["created_at"],
                "synced": bool(r["synced"]),
                "synced_at": r["synced_at"],
                "delivery_attempts": r["delivery_attempts"],
                "route_used": json.loads(r["route_used"]) if r["route_used"] else None,
                "packet_id": r["packet_id"],
                "delivery_status": r["delivery_status"],
            })
        return results

    def mark_synced(
        self,
        event_id: str,
        packet_id: Optional[str] = None,
        route_used: Optional[List[str]] = None,
    ) -> None:
        """Marks an alert as successfully delivered and synchronized."""
        now_iso = datetime.now(timezone.utc).isoformat()
        route_json = json.dumps(route_used) if route_used else None
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE edge_alerts
                SET synced = 1,
                    synced_at = ?,
                    delivery_status = 'DELIVERED',
                    packet_id = ?,
                    route_used = ?,
                    delivery_attempts = delivery_attempts + 1
                WHERE event_id = ?
            """, (now_iso, packet_id, route_json, event_id))
            conn.commit()

    def increment_attempt(self, event_id: str) -> None:
        """Records a failed delivery transmission attempt."""
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE edge_alerts
                SET delivery_attempts = delivery_attempts + 1,
                    delivery_status = 'FAILED_RETRY_QUEUED'
                WHERE event_id = ?
            """, (event_id,))
            conn.commit()

    def get_all_alerts(self, sensor_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Returns all recorded alerts, newest first."""
        with self._get_connection() as conn:
            if sensor_id:
                cursor = conn.execute(
                    "SELECT * FROM edge_alerts WHERE sensor_id = ? ORDER BY created_at DESC LIMIT ?",
                    (sensor_id, limit)
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM edge_alerts ORDER BY created_at DESC LIMIT ?",
                    (limit,)
                )
            rows = cursor.fetchall()

        results = []
        for r in rows:
            results.append({
                "event_id": r["event_id"],
                "sensor_id": r["sensor_id"],
                "location": r["location"],
                "hazard_type": r["hazard_type"],
                "severity": r["severity"],
                "risk_score": r["risk_score"],
                "confidence_score": r["confidence_score"],
                "lifecycle_state": r["lifecycle_state"],
                "detected_anomalies": json.loads(r["detected_anomalies"]),
                "contributing_measurements": json.loads(r["contributing_measurements"]),
                "explanation": r["explanation"],
                "recommended_action": r["recommended_action"],
                "created_at": r["created_at"],
                "synced": bool(r["synced"]),
                "synced_at": r["synced_at"],
                "delivery_attempts": r["delivery_attempts"],
                "route_used": json.loads(r["route_used"]) if r["route_used"] else None,
                "packet_id": r["packet_id"],
                "delivery_status": r["delivery_status"],
            })
        return results

    def clear(self) -> None:
        """Clears all stored alerts (for testing/reset)."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM edge_alerts")
            conn.commit()
