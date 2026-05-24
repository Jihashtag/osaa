import networkx as nx
import json
import os
from typing import Dict, Any
from models import MasterIdentity, IdentityAnchor


class GraphReporter:
    """
    Generates relational graph topologies for investigations.
    """

    def __init__(self):
        self.graph = nx.Graph()

    def _create_node(self, node_id: str, node_type: str):
        """Adds a node with metadata."""
        color_map = {
            "email": "blue",
            "username": "green",
            "url": "orange",
            "breach": "red",
        }
        self.graph.add_node(
            node_id, type=node_type, color=color_map.get(node_type, "grey")
        )

    def _create_edge(self, source: str, target: str, source_tool: str):
        """Adds an edge between two nodes."""
        self.graph.add_edge(source, target, tool=source_tool)

    def build_from_identity(self, identity: MasterIdentity):
        """Constructs the graph from a MasterIdentity object."""
        # Add primary identity node
        self.graph.add_node("Subject", type="anchor", color="purple")

        for anchor in identity.email:
            self._create_node(anchor.value, "email")
            self._create_edge("Subject", anchor.value, "discovery")

        for anchor in identity.username:
            self._create_node(anchor.value, "username")
            self._create_edge("Subject", anchor.value, "discovery")

        for url in identity.discovered_urls:
            self._create_node(url, "url")
            # Heuristic: link URLs to usernames found in them (if possible)
            self._create_edge("Subject", url, "discovery")

    def export_json(self, file_path: str):
        """Exports the graph in Cytoscape-compatible JSON format."""
        data = nx.node_link_data(self.graph)
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)

    def apply_louvain(self):
        """Applies community detection to group nodes."""
        try:
            communities = nx.community.louvain_communities(self.graph)
            for idx, community in enumerate(communities):
                for node in community:
                    self.graph.nodes[node]["community"] = idx
        except Exception as e:
            print(f"Community detection failed: {e}")

    def analyze_centrality(self):
        """Calculates degree centrality to identify key hubs."""
        centrality = nx.degree_centrality(self.graph)
        for node, score in centrality.items():
            self.graph.nodes[node]["centrality"] = score
