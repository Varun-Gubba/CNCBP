"""
Telemetry Generator and Packet Simulation Engine.
Generates realistic simulated environmental readings (temperature, humidity, air quality)
and manages the lifecycle, history, and aggregate transmission metrics of packets.
"""

from collections import deque
from datetime import datetime, timezone
import random
from typing import Deque, List, Optional
import uuid

from models import (
    EnvironmentalData,
    Packet,
    PacketStatus,
    MetricsResponse,
)
from network import (
    VirtualNetwork,
    NetworkRoutingError,
    NodeNotFoundError,
    NodeInactiveError,
    DestinationUnreachableError,
)


class EnvironmentalSimulator:
    """
    Generates realistic synthetic environmental monitoring telemetry.
    Note: These readings are simulated for educational/evaluation purposes
    and do not represent real physical sensor hardware measurements.
    """

    @staticmethod
    def generate_reading(
        sensor_id: str,
        temp_min: float = 21.0,
        temp_max: float = 33.5,
        humidity_min: float = 40.0,
        humidity_max: float = 85.0,
        aqi_min: float = 30.0,
        aqi_max: float = 110.0,
    ) -> EnvironmentalData:
        """Generates a randomized, realistic environmental reading for a given sensor."""
        now_iso = datetime.now(timezone.utc).isoformat()
        temperature = round(random.uniform(temp_min, temp_max), 2)
        humidity = round(random.uniform(humidity_min, humidity_max), 2)
        aqi = round(random.uniform(aqi_min, aqi_max), 1)

        return EnvironmentalData(
            sensor_id=sensor_id,
            timestamp=now_iso,
            temperature_celsius=temperature,
            humidity_percentage=humidity,
            air_quality_aqi=aqi,
            is_simulated=True,
            notes="Simulated environmental reading - not physical sensor measurement",
        )


class PacketSimulator:
    """
    Manages packet creation, simulated transmission over the virtual network,
    bounded in-memory history storage (latest 100 packets), and metrics calculation.
    """

    def __init__(self, max_history: int = 100) -> None:
        self.max_history = max_history
        self._packet_history: Deque[Packet] = deque(maxlen=max_history)
        self._packet_counter: int = 1000

    def _generate_packet_id(self) -> str:
        """Generates sequential and recognizable packet IDs like PKT-1001."""
        self._packet_counter += 1
        short_suffix = uuid.uuid4().hex[:4].upper()
        return f"PKT-{self._packet_counter}-{short_suffix}"

    def simulate_transmission(
        self,
        network: VirtualNetwork,
        source: str,
        destination: str,
        payload: Optional[EnvironmentalData] = None,
    ) -> Packet:
        """
        Simulates the creation and transmission of a packet.
        1. Validates node existence in network.
        2. Creates/attaches environmental payload.
        3. Attempts Dijkstra shortest-path routing.
        4. If route exists, marks packet as DELIVERED with latency and cost.
        5. If route does not exist or node is inactive, marks packet as FAILED.
        6. Stores packet in bounded history.
        """
        # Validate that source and destination are known nodes in topology
        if source not in network.nodes:
            raise NodeNotFoundError(f"Source node '{source}' does not exist in the network topology.")
        if destination not in network.nodes:
            raise NodeNotFoundError(f"Destination node '{destination}' does not exist in the network topology.")

        # Ensure environmental payload exists
        if payload is None:
            payload = EnvironmentalSimulator.generate_reading(sensor_id=source)

        packet_id = self._generate_packet_id()
        created_at = datetime.now(timezone.utc).isoformat()

        # Attempt routing via Dijkstra's shortest path
        try:
            route_result = network.find_shortest_path(source=source, destination=destination)

            packet = Packet(
                packet_id=packet_id,
                source=source,
                destination=destination,
                payload=payload,
                created_at=created_at,
                route=route_result.route,
                status=PacketStatus.DELIVERED,
                hop_count=route_result.hop_count,
                total_cost=route_result.total_cost,
                estimated_latency_ms=route_result.estimated_latency_ms,
                failure_reason=None,
            )
        except (NodeInactiveError, DestinationUnreachableError, NetworkRoutingError) as routing_err:
            # Route failure: packet could not be routed/delivered
            packet = Packet(
                packet_id=packet_id,
                source=source,
                destination=destination,
                payload=payload,
                created_at=created_at,
                route=[],
                status=PacketStatus.FAILED,
                hop_count=0,
                total_cost=0.0,
                estimated_latency_ms=0.0,
                failure_reason=str(routing_err),
            )

        # Append to bounded history (automatically discards oldest when > 100)
        self._packet_history.appendleft(packet)
        return packet

    def get_packets(self, limit: int = 100) -> List[Packet]:
        """Returns recent packet records, newest first, up to the given limit."""
        return list(self._packet_history)[:limit]

    def get_metrics(self) -> MetricsResponse:
        """
        Calculates aggregate network performance metrics across stored packets:
        - Total packets created
        - Delivered packets
        - Failed packets
        - Packet delivery ratio (%)
        - Average estimated latency (ms)
        - Average hop count
        Safely handles division-by-zero when no packets exist.
        """
        total = len(self._packet_history)
        if total == 0:
            return MetricsResponse(
                total_packets=0,
                delivered_packets=0,
                failed_packets=0,
                delivery_ratio_percentage=0.0,
                average_latency_ms=0.0,
                average_hop_count=0.0,
            )

        delivered = [p for p in self._packet_history if p.status == PacketStatus.DELIVERED]
        failed_count = sum(1 for p in self._packet_history if p.status == PacketStatus.FAILED)
        delivered_count = len(delivered)

        delivery_ratio = round((delivered_count / total) * 100.0, 2)

        if delivered_count > 0:
            avg_latency = round(sum(p.estimated_latency_ms for p in delivered) / delivered_count, 2)
            avg_hops = round(sum(p.hop_count for p in delivered) / delivered_count, 2)
        else:
            avg_latency = 0.0
            avg_hops = 0.0

        return MetricsResponse(
            total_packets=total,
            delivered_packets=delivered_count,
            failed_packets=failed_count,
            delivery_ratio_percentage=delivery_ratio,
            average_latency_ms=avg_latency,
            average_hop_count=avg_hops,
        )

    def reset(self) -> None:
        """Clears packet history and resets statistics to initial state."""
        self._packet_history.clear()
        self._packet_counter = 1000
