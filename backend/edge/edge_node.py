"""
Edge Node Processing Unit.

Maintains independent local processing state for a simulated IoT edge node:
- Sensor ID and location
- Latest sensor measurements
- Local anomaly-detection results
- Hazard risk assessments
- Connectivity status (simulated online/offline)
- Local persistent queue for offline operation
- Alert lifecycle and de-duplication tracking (NEW, CONTINUING, WORSENING, RESOLVED)
- Network transmission and synchronization logic
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable, Tuple
import uuid

from models import (
    EnvironmentalData,
    HazardType,
    SeverityLevel,
    AlertLifecycle,
    AnomalyResult,
    RiskAssessment,
    EdgeAlert,
    EdgeNodeState,
)
from .config import EdgeThresholdConfig, DEFAULT_THRESHOLDS
from .detector import AnomalyDetector
from .risk_engine import RiskEngine
from .persistence import EdgeQueuePersistence


class EdgeNode:
    """
    Independent Edge Computing Node for Environmental Multi-Hazard Early Warning.
    Executes locally without requiring continuous server connectivity.
    """

    def __init__(
        self,
        node_id: str,
        location: str,
        config: Optional[EdgeThresholdConfig] = None,
        persistence: Optional[EdgeQueuePersistence] = None,
    ):
        self.node_id = node_id
        self.location = location
        self.config = config or DEFAULT_THRESHOLDS
        self.detector = AnomalyDetector(sensor_id=node_id, config=self.config)
        self.risk_engine = RiskEngine(config=self.config)
        self.persistence = persistence or EdgeQueuePersistence()

        # Operational state
        self.is_online: bool = True
        self.readings_processed: int = 0
        self.last_processed_at: Optional[str] = None
        self.latest_measurements: Optional[Dict[str, Any]] = None
        self.latest_anomalies: List[AnomalyResult] = []
        self.active_risk_assessments: Dict[str, RiskAssessment] = {}

        # Alert lifecycle tracking: hazard_type -> (previous_severity, last_alert_time)
        self._hazard_lifecycle: Dict[str, Tuple[SeverityLevel, str]] = {}

        # Transmission callback: signature (edge_node, alert_dict) -> Optional[packet_dict]
        self._transmission_callback: Optional[Callable[["EdgeNode", Dict[str, Any]], Optional[Dict[str, Any]]]] = None

    def set_transmission_callback(
        self,
        callback: Callable[["EdgeNode", Dict[str, Any]], Optional[Dict[str, Any]]]
    ) -> None:
        """Sets the router callback used to transmit alerts across the NetworkX graph."""
        self._transmission_callback = callback

    def set_connectivity(self, is_online: bool) -> bool:
        """Toggles edge node connectivity state (simulating link outages)."""
        self.is_online = is_online
        return self.is_online

    def get_state(self) -> EdgeNodeState:
        """Returns the full runtime state of this edge node."""
        pending_alerts = self.persistence.get_pending_alerts(sensor_id=self.node_id)
        all_alerts = self.persistence.get_all_alerts(sensor_id=self.node_id)
        synced_count = sum(1 for a in all_alerts if a.get("synced"))

        return EdgeNodeState(
            node_id=self.node_id,
            location=self.location,
            is_online=self.is_online,
            readings_processed=self.readings_processed,
            last_processed_at=self.last_processed_at,
            latest_measurements=self.latest_measurements,
            active_risk_assessments=self.active_risk_assessments,
            pending_alerts_count=len(pending_alerts),
            synced_alerts_count=synced_count,
            total_alerts_count=len(all_alerts),
        )

    def _determine_lifecycle_and_should_alert(
        self,
        hazard_type: str,
        current_severity: SeverityLevel,
        current_risk_score: float = 0.0,
    ) -> Tuple[AlertLifecycle, bool]:
        """
        Prevents duplicate alerts for identical abnormal readings.
        Tracks whether condition is NEW, CONTINUING, WORSENING, or RESOLVED.
        Returns: (lifecycle_state, should_emit_alert)
        """
        prev = self._hazard_lifecycle.get(hazard_type)

        # Baseline safe conditions
        if current_severity == SeverityLevel.LOW:
            if prev and prev[0] != SeverityLevel.LOW:
                # Hazard resolved!
                self._hazard_lifecycle[hazard_type] = (SeverityLevel.LOW, current_risk_score, datetime.now(timezone.utc).isoformat())
                return AlertLifecycle.RESOLVED, True
            self._hazard_lifecycle[hazard_type] = (SeverityLevel.LOW, current_risk_score, datetime.now(timezone.utc).isoformat())
            return AlertLifecycle.RESOLVED, False

        # If previous was LOW or non-existent, this is NEW
        if not prev or prev[0] == SeverityLevel.LOW:
            self._hazard_lifecycle[hazard_type] = (current_severity, current_risk_score, datetime.now(timezone.utc).isoformat())
            return AlertLifecycle.NEW, True

        prev_severity, prev_score, _ = prev if len(prev) == 3 else (prev[0], 50.0, prev[1])

        # Severity ranks for comparison
        rank = {
            SeverityLevel.LOW: 0,
            SeverityLevel.MODERATE: 1,
            SeverityLevel.HIGH: 2,
            SeverityLevel.CRITICAL: 3,
        }

        # Check if condition worsened (either severity jumped or risk score escalated by >= 12 pts)
        if rank[current_severity] > rank[prev_severity] or (current_risk_score - prev_score >= 12.0 and current_severity != SeverityLevel.LOW):
            # Hazard escalated!
            self._hazard_lifecycle[hazard_type] = (current_severity, current_risk_score, datetime.now(timezone.utc).isoformat())
            return AlertLifecycle.WORSENING, True
        else:
            # Continuing at same or lesser severity - suppress duplicate alert
            self._hazard_lifecycle[hazard_type] = (current_severity, current_risk_score, datetime.now(timezone.utc).isoformat())
            return AlertLifecycle.CONTINUING, False

    def process_reading(self, reading: Dict[str, Any]) -> Dict[str, Any]:
        """
        Modular edge processing:
        1. Validates and extracts measurements.
        2. Runs local Anomaly Detector.
        3. Evaluates Multi-Hazard Risk Engine.
        4. Evaluates Alert Lifecycle & De-duplication.
        5. Enqueues critical alerts locally.
        6. If online, attempts instant transmission through routing callback.
        Returns processing summary.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        self.readings_processed += 1
        self.last_processed_at = now_iso
        self.latest_measurements = dict(reading)

        # Step 1: Detect Anomalies
        anomalies = self.detector.detect_anomalies(reading)
        self.latest_anomalies = anomalies

        # Step 2: Risk Assessments
        assessments = self.risk_engine.evaluate_all_hazards(
            sensor_id=self.node_id,
            location=self.location,
            reading=reading,
            anomalies=anomalies,
            history_len=len(self.detector._history),
        )
        self.active_risk_assessments = assessments

        # Step 3: Lifecycle and Alerts Generation
        emitted_alerts: List[Dict[str, Any]] = []

        for hazard_type_str, assessment in assessments.items():
            lifecycle, should_emit = self._determine_lifecycle_and_should_alert(
                hazard_type=hazard_type_str,
                current_severity=assessment.severity,
                current_risk_score=assessment.risk_score,
            )

            # Generate alert only for actionable conditions (MODERATE, HIGH, CRITICAL, or RESOLVED)
            if should_emit and (assessment.severity != SeverityLevel.LOW or lifecycle == AlertLifecycle.RESOLVED):
                event_id = f"EVT-{self.node_id}-{hazard_type_str[:3]}-{uuid.uuid4().hex[:6].upper()}"
                alert_dict = {
                    "event_id": event_id,
                    "sensor_id": self.node_id,
                    "location": self.location,
                    "hazard_type": assessment.hazard_type.value,
                    "severity": assessment.severity.value,
                    "risk_score": assessment.risk_score,
                    "confidence_score": assessment.confidence_score,
                    "lifecycle_state": lifecycle.value,
                    "detected_anomalies": assessment.detected_anomalies,
                    "contributing_measurements": assessment.contributing_measurements,
                    "explanation": assessment.explanation,
                    "recommended_action": assessment.recommended_action,
                    "created_at": now_iso,
                    "synced": False,
                    "delivery_attempts": 0,
                    "delivery_status": "QUEUED",
                }

                # Always enqueue locally in persistent SQLite buffer
                self.persistence.enqueue_alert(alert_dict)

                # Step 4: Transmission Attempt if Online
                if self.is_online and self._transmission_callback:
                    try:
                        tx_result = self._transmission_callback(self, alert_dict)
                        if tx_result and tx_result.get("status") == "DELIVERED":
                            self.persistence.mark_synced(
                                event_id=event_id,
                                packet_id=tx_result.get("packet_id"),
                                route_used=tx_result.get("route"),
                            )
                            alert_dict["synced"] = True
                            alert_dict["synced_at"] = now_iso
                            alert_dict["delivery_status"] = "DELIVERED"
                            alert_dict["packet_id"] = tx_result.get("packet_id")
                            alert_dict["route_used"] = tx_result.get("route")
                        else:
                            self.persistence.increment_attempt(event_id)
                            alert_dict["delivery_status"] = "FAILED_RETRY_QUEUED"
                    except Exception:
                        self.persistence.increment_attempt(event_id)
                        alert_dict["delivery_status"] = "FAILED_RETRY_QUEUED"

                emitted_alerts.append(alert_dict)

        return {
            "node_id": self.node_id,
            "location": self.location,
            "processed_at": now_iso,
            "is_online": self.is_online,
            "anomalies_detected_count": len(anomalies),
            "anomalies": [a.model_dump() for a in anomalies],
            "risk_assessments": {k: v.model_dump() for k, v in assessments.items()},
            "emitted_alerts": emitted_alerts,
        }

    def sync_pending_alerts(self) -> List[str]:
        """
        Synchronizes all pending locally buffered alerts to the central server.
        Uses FIFO order and de-duplicates by event_id.
        """
        if not self.is_online:
            return []

        pending = self.persistence.get_pending_alerts(sensor_id=self.node_id)
        synced_ids = []

        for alert in pending:
            event_id = alert["event_id"]
            if self._transmission_callback:
                try:
                    tx_result = self._transmission_callback(self, alert)
                    if tx_result and tx_result.get("status") == "DELIVERED":
                        self.persistence.mark_synced(
                            event_id=event_id,
                            packet_id=tx_result.get("packet_id"),
                            route_used=tx_result.get("route"),
                        )
                        synced_ids.append(event_id)
                    else:
                        self.persistence.increment_attempt(event_id)
                except Exception:
                    self.persistence.increment_attempt(event_id)
            else:
                # No callback attached, simulate local sync completion
                self.persistence.mark_synced(event_id=event_id)
                synced_ids.append(event_id)

        return synced_ids
