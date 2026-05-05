# modules/graph/graph_builder.py

import networkx as nx
from typing import Optional
import community as community_louvain  # python-louvain


class KnowledgeGraphBuilder:
    def __init__(self):
        # Ho scelto DiGraph (directed) e non Graph perché
        # le relazioni semantiche sono direzionali:
        # "Python IS_A Language" != "Language IS_A Python".
        # Perdo la bidirezionalità ma guadagno in precisione semantica.
        self.graph = nx.DiGraph()

    def add_triples(self, triples: list[dict], doc_id: str):
        """
        Cosa: Aggiunge le triple al grafo NetworkX.
        Come: Ogni entità diventa un nodo, ogni relazione un arco pesato.
              Il peso aumenta ad ogni occorrenza della stessa triple
              (frequenza come proxy di importanza).
        Perché: Un arco con peso 5 (la relazione appare 5 volte
                in parti diverse del documento) è semanticamente
                più affidabile di un arco con peso 1.
        """
        for triple in triples:
            head = triple["head"].strip().lower()
            tail = triple["tail"].strip().lower()
            relation = triple["relation"].strip().lower()
            confidence = triple.get("confidence", 1.0)

            # Aggiungo o aggiorno il nodo head
            if not self.graph.has_node(head):
                self.graph.add_node(head, doc_ids={doc_id}, mention_count=1)
            else:
                self.graph.nodes[head]["mention_count"] += 1
                self.graph.nodes[head]["doc_ids"].add(doc_id)

            # Stesso per tail
            if not self.graph.has_node(tail):
                self.graph.add_node(tail, doc_ids={doc_id}, mention_count=1)

            # Per gli archi uso (head, tail, relation) come chiave logica.
            # Se l'arco esiste già, incremento il peso invece di duplicarlo.
            if self.graph.has_edge(head, tail):
                self.graph[head][tail]["weight"] += confidence
                self.graph[head][tail]["relations"].add(relation)
            else:
                self.graph.add_edge(
                    head, tail,
                    relations={relation},
                    weight=confidence,
                    doc_id=doc_id
                )

    def compute_clusters(self) -> dict[str, int]:
        """
        Cosa: Raggruppa i nodi in macro-aree tematiche.
        Come: Converto il DiGraph in Graph non direzionale per Louvain,
              che è uno dei migliori algoritmi di community detection
              per grafi di knowledge in letteratura.
        Perché: La direzionalità degli archi disturba Louvain che
                lavora su modularità non direzionale. Per il clustering
                tematico, la direzione è irrilevante: voglio sapere
                quali nodi "parlano" dello stesso argomento.
        Returns: dict {node_name: cluster_id}
        """
        undirected = self.graph.to_undirected()
        
        # Rimuovo nodi isolati prima del clustering:
        # un nodo con 0 archi distorce la modularità
        isolated = list(nx.isolates(undirected))
        undirected.remove_nodes_from(isolated)
        
        if len(undirected.nodes) == 0:
            return {}

        partition = community_louvain.best_partition(
            undirected,
            weight="weight",
            resolution=1.0  # aumentare per cluster più piccoli e granulari
        )
        
        # Propago i cluster_id anche ai nodi originali del DiGraph
        nx.set_node_attributes(self.graph, partition, "cluster_id")
        
        return partition