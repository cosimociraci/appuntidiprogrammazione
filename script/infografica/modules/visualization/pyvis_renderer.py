# modules/visualization/pyvis_renderer.py

from pyvis.network import Network
import networkx as nx
import hashlib
import os


class PyvisRenderer:
    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    # Mappa colori per cluster: ho scelto una palette distinguibile
    # anche per chi ha difficoltà cromatiche (deuteranopia-safe).
    CLUSTER_COLORS = [
        "#4E79A7", "#F28E2B", "#E15759", "#76B7B2",
        "#59A14F", "#EDC948", "#B07AA1", "#FF9DA7",
        "#9C755F", "#BAB0AC"
    ]

    def render(
        self,
        graph: nx.DiGraph,
        partition: dict[str, int],
        doc_title: str = "knowledge_map"
    ) -> str:
        """
        Cosa: Genera un file HTML interattivo del grafo.
        Come: Trasferisce nodi e archi da NetworkX a Pyvis,
              applicando cluster_id come colore nodo.
        Perché: Pyvis genera un HTML self-contained che Streamlit
                può embedded via components.html() senza server extra.
        Returns: path del file HTML generato.
        """
        net = Network(
            height="750px",
            width="100%",
            directed=True,
            bgcolor="#1a1a2e",   # dark background per leggibilità
            font_color="#e0e0e0"
        )
        
        # Fisso la fisica per stabilizzare il layout:
        # senza questo i nodi continuano a muoversi infinitamente
        # rendendo la mappa inutilizzabile su grafi grandi.
        net.set_options("""
        {
          "physics": {
            "forceAtlas2Based": {
              "gravitationalConstant": -50,
              "centralGravity": 0.01,
              "springLength": 100
            },
            "solver": "forceAtlas2Based",
            "stabilization": { "iterations": 150 }
          },
          "edges": {
            "arrows": { "to": { "enabled": true, "scaleFactor": 0.5 } },
            "smooth": { "type": "curvedCW", "roundness": 0.2 }
          }
        }
        """)

        for node, attrs in graph.nodes(data=True):
            cluster_id = partition.get(node, 0)
            color = self.CLUSTER_COLORS[cluster_id % len(self.CLUSTER_COLORS)]
            # La size del nodo è proporzionale al mention_count:
            # i concetti più citati appaiono più grandi, fornendo
            # un immediato segnale visivo di importanza.
            size = min(10 + attrs.get("mention_count", 1) * 3, 40)
            
            net.add_node(
                node,
                label=node,
                color=color,
                size=size,
                title=f"Cluster {cluster_id} | Mentions: {attrs.get('mention_count', 1)}"
            )

        for src, dst, attrs in graph.edges(data=True):
            relations_label = " / ".join(list(attrs.get("relations", {"related to"}))[:2])
            net.add_edge(
                src, dst,
                label=relations_label,
                value=attrs.get("weight", 1.0),
                title=f"weight: {attrs.get('weight', 1.0):.2f}"
            )

        safe_title = "".join(c for c in doc_title if c.isalnum() or c in "_-")
        output_path = os.path.join(self.output_dir, f"{safe_title}_map.html")
        net.save_graph(output_path)
        
        return output_path