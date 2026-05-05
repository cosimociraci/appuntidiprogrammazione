# modules/extract/entity_resolver.py

import logging
import re
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class EntityResolver:
    """
    Cosa: Deduplica e normalizza le entità nelle triple estratte.
    Come: Due passaggi — normalizzazione lessicale (lowercase, strip,
          rimozione articoli) poi similarità fuzzy per varianti
          vicine (es. "machine learning" vs "machine-learning").
    Perché: L'LLM locale genera la stessa entità in forme diverse
            a seconda del contesto del chunk. Senza questo step
            il grafo si frammenta in decine di nodi isolati
            che rappresentano lo stesso concetto.
    """

    # Soglia di similarità sopra cui due entità sono considerate
    # la stessa. 0.85 è conservativo: preferisco falsi negativi
    # (due nodi separati per lo stesso concetto) a falsi positivi
    # (fusione di concetti distinti).
    SIMILARITY_THRESHOLD = 0.85

    # Articoli e preposizioni da rimuovere nella normalizzazione
    # per evitare che "il Python" e "Python" restino entità separate.
    STOPWORDS = {"il", "lo", "la", "i", "gli", "le", "un", "uno", "una",
                 "the", "a", "an", "of", "in", "on", "at", "to", "for"}

    def resolve(self, triples: list[dict]) -> list[dict]:
        """
        Cosa: Normalizza tutte le entità in head e tail delle triple.
        Come: Prima costruisco un dizionario di mapping
              {variante_grezza -> forma_canonica}, poi lo applico
              a tutte le triple in un secondo passaggio.
        Perché: Due passaggi separati (build map → apply map) è più
                robusto di una risoluzione in-place: garantisce che
                la forma canonica sia coerente per tutte le triple,
                anche quelle processate prima di scoprire una variante.
        """
        # Raccolgo tutte le entità uniche
        all_entities = set()
        for t in triples:
            all_entities.add(t.get("head", "").strip())
            all_entities.add(t.get("tail", "").strip())
        all_entities.discard("")  # rimuovo stringa vuota se presente

        canonical_map = self._build_canonical_map(list(all_entities))
        logger.info(
            f"[EntityResolver] {len(all_entities)} entità grezze → "
            f"{len(set(canonical_map.values()))} forme canoniche"
        )

        # Applico il mapping a tutte le triple
        resolved = []
        for t in triples:
            head_raw = t.get("head", "").strip()
            tail_raw = t.get("tail", "").strip()

            if not head_raw or not tail_raw:
                continue  # scarto triple incomplete

            resolved_triple = {
                **t,
                "head": canonical_map.get(head_raw, head_raw),
                "tail": canonical_map.get(tail_raw, tail_raw),
            }

            # Scarto auto-loop generati dalla normalizzazione:
            # se head e tail diventano uguali dopo la risoluzione,
            # la tripla non ha valore semantico nel grafo.
            if resolved_triple["head"] != resolved_triple["tail"]:
                resolved.append(resolved_triple)

        return resolved

    def _build_canonical_map(self, entities: list[str]) -> dict[str, str]:
        """
        Cosa: Mappa ogni entità grezza alla sua forma canonica.
        Come: Per ogni coppia di entità normalizzate, se la similarità
              supera la soglia, la più corta (o alfabeticamente prima)
              diventa la forma canonica. O(n²) ma su liste di entità
              tipicamente <500 elementi è trascurabile.
        """
        # Normalizzo tutte le entità per il confronto
        normalized = {e: self._normalize(e) for e in entities}

        # canonical_map: variante grezza → forma canonica grezza
        canonical_map: dict[str, str] = {e: e for e in entities}

        entity_list = list(entities)
        for i in range(len(entity_list)):
            for j in range(i + 1, len(entity_list)):
                e1, e2 = entity_list[i], entity_list[j]
                n1, n2 = normalized[e1], normalized[e2]

                sim = SequenceMatcher(None, n1, n2).ratio()
                if sim >= self.SIMILARITY_THRESHOLD:
                    # La forma canonica è la più corta tra le due
                    # normalizzate (tende a essere la più generica)
                    canonical = e1 if len(n1) <= len(n2) else e2
                    other = e2 if canonical == e1 else e1

                    # Propago la canonicità transitivamente:
                    # se A→B e B→C, allora A→C
                    current_canonical = canonical_map[canonical]
                    canonical_map[other] = current_canonical

        return canonical_map

    def _normalize(self, entity: str) -> str:
        # Lowercase, rimozione punteggiatura, rimozione stopwords
        text = entity.lower().strip()
        text = re.sub(r"[^\w\s]", " ", text)  # punteggiatura → spazio
        words = [w for w in text.split() if w not in self.STOPWORDS]
        return " ".join(words)