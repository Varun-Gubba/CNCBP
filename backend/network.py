"""
Virtual Network and Dijkstra Routing Engine using NetworkX.
Maintains the virtual network topology, node and link statuses, and executes
shortest path calculations based on edge costs while accumulating link delays.
"""

from typing import Dict, List, Optional, Tuple, Any
import networkx as nx

from models import (
    Node,
    Link,
    NodeType,
    NodeStatus,
    LinkStatus,
    NetworkTopologyResponse,
    RouteResponse,
    RouteStepDetail,
)


class NetworkRoutingError(Exception):
    """Custom exception raised when routing fails or nodes are unreachable."""
    pass


class NodeNotFoundError(NetworkRoutingError):
    """Raised when a requested node does not exist in the network topology."""
    pass


class NodeInactiveError(NetworkRoutingError):
    """Raised when the source or destination node is disabled / inactive."""
    pass


class DestinationUnreachableError(NetworkRoutingError):
    """Raised when no active path exists between source and destination."""
    pass


class VirtualNetwork:
    """
    Simulates a virtual network graph consisting of environmental sensors,
    intermediate routers, gateways, and centralized monitoring servers.
    """

    def __init__(self) -> None:
        self.nodes: Dict[str, Node] = {}
        self.links: Dict[Tuple[str, str], Link] = {}
        self._initialize_default_topology()

    def _canonical_edge(self, u: str, v: str) -> Tuple[str, str]:
        """Returns a sorted tuple key for undirected edge lookup."""
        return (u, v) if u < v else (v, u)

    def _initialize_default_topology(self) -> None:
        """Sets up the initial default topology as required by project specification."""
        self.nodes.clear()
        self.links.clear()

        # 1. Default Nodes
        default_nodes = [
            Node(
                id="S1",
                name="Sensor Node 1 - Temp & Humidity",
                type=NodeType.SENSOR,
                status=NodeStatus.ACTIVE,
            ),
            Node(
                id="S2",
                name="Sensor Node 2 - Environmental Monitor",
                type=NodeType.SENSOR,
                status=NodeStatus.ACTIVE,
            ),
            Node(
                id="R1",
                name="Router 1 - Edge Router Alpha",
                type=NodeType.ROUTER,
                status=NodeStatus.ACTIVE,
            ),
            Node(
                id="R2",
                name="Router 2 - Backbone Router Beta",
                type=NodeType.ROUTER,
                status=NodeStatus.ACTIVE,
            ),
            Node(
                id="R3",
                name="Router 3 - Backbone Router Gamma",
                type=NodeType.ROUTER,
                status=NodeStatus.ACTIVE,
            ),
            Node(
                id="G1",
                name="Gateway 1 - Primary Gateway",
                type=NodeType.GATEWAY,
                status=NodeStatus.ACTIVE,
            ),
            Node(
                id="SRV",
                name="Central Server - Monitoring Datacenter",
                type=NodeType.SERVER,
                status=NodeStatus.ACTIVE,
            ),
        ]

        for node in default_nodes:
            self.nodes[node.id] = node

        # 2. Default Weighted Links (Cost for Dijkstra, Delay in ms for Latency)
        default_links = [
            Link(source="S1", destination="R1", cost=3.0, delay=6.0, status=LinkStatus.ACTIVE),
            Link(source="S1", destination="R2", cost=7.0, delay=14.0, status=LinkStatus.ACTIVE),
            Link(source="S2", destination="R2", cost=4.0, delay=9.0, status=LinkStatus.ACTIVE),
            Link(source="S2", destination="R3", cost=2.0, delay=5.0, status=LinkStatus.ACTIVE),
            Link(source="R1", destination="R2", cost=2.0, delay=4.0, status=LinkStatus.ACTIVE),
            Link(source="R1", destination="G1", cost=8.0, delay=18.0, status=LinkStatus.ACTIVE),
            Link(source="R2", destination="R3", cost=3.0, delay=7.0, status=LinkStatus.ACTIVE),
            Link(source="R2", destination="G1", cost=3.0, delay=8.0, status=LinkStatus.ACTIVE),
            Link(source="R3", destination="G1", cost=4.0, delay=9.0, status=LinkStatus.ACTIVE),
            Link(source="G1", destination="SRV", cost=1.0, delay=2.0, status=LinkStatus.ACTIVE),
        ]

        for link in default_links:
            key = self._canonical_edge(link.source, link.destination)
            self.links[key] = link

    def reset(self) -> None:
        """Resets the network topology back to the default operational state."""
        self._initialize_default_topology()

    def get_nodes(self) -> List[Node]:
        """Returns all registered nodes."""
        return list(self.nodes.values())

    def get_node(self, node_id: str) -> Optional[Node]:
        """Retrieves a single node by ID."""
        return self.nodes.get(node_id)

    def get_sensors(self) -> List[Node]:
        """Returns all sensor nodes in the network."""
        return [node for node in self.nodes.values() if node.type == NodeType.SENSOR]

    def get_links(self) -> List[Link]:
        """Returns all registered links."""
        return list(self.links.values())

    def get_link(self, u: str, v: str) -> Optional[Link]:
        """Retrieves link between two nodes if it exists."""
        key = self._canonical_edge(u, v)
        return self.links.get(key)

    def set_node_status(self, node_id: str, status: NodeStatus) -> Node:
        """Enables or disables a network node to simulate hardware or power failures."""
        if node_id not in self.nodes:
            raise NodeNotFoundError(f"Node '{node_id}' does not exist in the network topology.")
        self.nodes[node_id].status = status
        return self.nodes[node_id]

    def set_link_status(self, source: str, destination: str, status: LinkStatus) -> Link:
        """Enables or disables a network link to simulate cable cut or interference."""
        key = self._canonical_edge(source, destination)
        if key not in self.links:
            raise NetworkRoutingError(f"Link between '{source}' and '{destination}' does not exist.")
        self.links[key].status = status
        return self.links[key]

    def get_topology(self) -> NetworkTopologyResponse:
        """Returns complete topology overview with counts."""
        nodes = self.get_nodes()
        links = self.get_links()
        active_nodes = sum(1 for n in nodes if n.status == NodeStatus.ACTIVE)
        active_links = sum(1 for l in links if l.status == LinkStatus.ACTIVE)
        return NetworkTopologyResponse(
            nodes=nodes,
            links=links,
            active_nodes_count=active_nodes,
            active_links_count=active_links,
        )

    def build_active_graph(self) -> nx.Graph:
        """
        Builds a NetworkX graph containing ONLY currently active nodes and active links.
        Inactive components are omitted so Dijkstra's algorithm cannot traverse them.
        """
        graph = nx.Graph()

        # Add active nodes
        for node_id, node in self.nodes.items():
            if node.status == NodeStatus.ACTIVE:
                graph.add_node(node_id, name=node.name, type=node.type.value)

        # Add active links
        for (u, v), link in self.links.items():
            if link.status == LinkStatus.ACTIVE:
                # Both endpoints must be active
                if u in graph and v in graph:
                    graph.add_edge(
                        u,
                        v,
                        weight=link.cost,
                        delay=link.delay,
                        cost=link.cost,
                    )

        return graph

    def find_shortest_path(self, source: str, destination: str) -> RouteResponse:
        """
        Calculates the shortest route using Dijkstra's algorithm based on link cost.
        Also calculates total route cost, hop count, and estimated latency from link delays.
        """
        # 1. Validation: Verify source exists
        if source not in self.nodes:
            raise NodeNotFoundError(f"Source node '{source}' was not found in network topology.")

        # 2. Validation: Verify destination exists
        if destination not in self.nodes:
            raise NodeNotFoundError(f"Destination node '{destination}' was not found in network topology.")

        # 3. Check node operational status
        src_node = self.nodes[source]
        dst_node = self.nodes[destination]

        if src_node.status != NodeStatus.ACTIVE:
            raise NodeInactiveError(f"Cannot route from inactive source node '{source}' (status: {src_node.status.value}).")

        if dst_node.status != NodeStatus.ACTIVE:
            raise NodeInactiveError(f"Cannot route to inactive destination node '{destination}' (status: {dst_node.status.value}).")

        # 4. Trivial case: Source is Destination
        if source == destination:
            return RouteResponse(
                source=source,
                destination=destination,
                route=[source],
                total_cost=0.0,
                hop_count=0,
                estimated_latency_ms=0.0,
                path_details=[],
            )

        # 5. Build active graph
        active_graph = self.build_active_graph()

        # Check if endpoints are present in active graph
        if not active_graph.has_node(source) or not active_graph.has_node(destination):
            raise DestinationUnreachableError(
                f"Source '{source}' or destination '{destination}' is not available in active network graph."
            )

        # 6. Execute Dijkstra's shortest path
        try:
            path = nx.dijkstra_path(active_graph, source=source, target=destination, weight="weight")
        except nx.NetworkXNoPath:
            raise DestinationUnreachableError(
                f"Destination '{destination}' is unreachable from source '{source}'. No active route exists."
            )
        except Exception as e:
            raise NetworkRoutingError(f"Dijkstra routing failed: {str(e)}")

        # 7. Calculate metrics along selected route
        total_cost = 0.0
        total_delay = 0.0
        path_details: List[RouteStepDetail] = []

        for i in range(len(path) - 1):
            u = path[i]
            v = path[i + 1]
            edge_data = active_graph.get_edge_data(u, v)

            if not edge_data:
                raise NetworkRoutingError(f"Edge data missing between {u} and {v}")

            step_cost = float(edge_data.get("weight", 0.0))
            step_delay = float(edge_data.get("delay", 0.0))

            total_cost += step_cost
            total_delay += step_delay

            path_details.append(
                RouteStepDetail(
                    hop_number=i + 1,
                    from_node=u,
                    to_node=v,
                    link_cost=step_cost,
                    link_delay_ms=step_delay,
                )
            )

        hop_count = len(path) - 1

        return RouteResponse(
            source=source,
            destination=destination,
            route=path,
            total_cost=round(total_cost, 2),
            hop_count=hop_count,
            estimated_latency_ms=round(total_delay, 2),
            path_details=path_details,
        )
