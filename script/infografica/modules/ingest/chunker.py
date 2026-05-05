# modules/ingest/chunker.py

from dataclasses import dataclass
from typing import Iterator
import re

@dataclass
class Chunk:
    # Ho definito questo dataclass per trasportare
    # non solo il testo ma anche il contesto posizionale,
    # necessario per il re-linking cross-chunk successivo.
    id: int
    text: str
    doc_id: str
    start_char: int
    end_char: int
    # Anchor: le ultime N entità estratte dal chunk precedente,
    # iniettate come contesto nel prompt del chunk corrente.
    # Questo è il meccanismo chiave per non perdere i collegamenti
    # tra inizio e fine documento.
    previous_entities_anchor: list[str]


class SlidingWindowChunker:
    def __init__(
        self,
        chunk_size: int = 800,       # token approssimati, safe per 8B models
        overlap_size: int = 150,     # overlap per continuità semantica
        anchor_entity_count: int = 5 # entità da portare nel chunk successivo
    ):
        # Ho scelto 800 token come default perché su Mistral 7B/8B
        # oltre i 1200 token nel prompt di estrazione la qualità
        # del JSON degrada significativamente in test empirici.
        self.chunk_size = chunk_size
        self.overlap_size = overlap_size
        self.anchor_entity_count = anchor_entity_count

    def chunk_document(
        self,
        text: str,
        doc_id: str
    ) -> Iterator[Chunk]:
        """
        Cosa: Divide il documento in chunk con overlap.
        Come: Sliding window su word boundaries, non su caratteri,
              per evitare di spezzare entità named.
        Perché: Spezzare "Machine Learning" a metà genera entità
                garbage che il validator downstream deve filtrare.
        """
        # Segmento su boundary di frase quando possibile
        sentences = self._split_sentences(text)
        
        current_chunk_tokens = []
        current_len = 0
        chunk_id = 0
        previous_entities: list[str] = []

        for sentence in sentences:
            sentence_len = len(sentence.split())
            
            if current_len + sentence_len > self.chunk_size and current_chunk_tokens:
                chunk_text = " ".join(current_chunk_tokens)
                yield Chunk(
                    id=chunk_id,
                    text=chunk_text,
                    doc_id=doc_id,
                    start_char=0,  # tracking semplificato
                    end_char=len(chunk_text),
                    previous_entities_anchor=previous_entities.copy()
                )
                chunk_id += 1
                
                # Mantengo overlap: ultime `overlap_size` parole
                # nel buffer del chunk successivo
                overlap_words = " ".join(current_chunk_tokens).split()
                current_chunk_tokens = overlap_words[-self.overlap_size:]
                current_len = len(current_chunk_tokens)
            
            current_chunk_tokens.append(sentence)
            current_len += sentence_len

        # Flush dell'ultimo chunk residuo
        if current_chunk_tokens:
            chunk_text = " ".join(current_chunk_tokens)
            yield Chunk(
                id=chunk_id,
                text=chunk_text,
                doc_id=doc_id,
                start_char=0,
                end_char=len(chunk_text),
                previous_entities_anchor=previous_entities.copy()
            )

    def _split_sentences(self, text: str) -> list[str]:
        # Regex semplice ma efficace: split su punto/punto esclamativo/
        # interrogativo seguiti da spazio e maiuscola.
        # Non uso nltk per evitare dipendenze pesanti.
        return [s.strip() for s in re.split(r'(?<=[.!?])\s+(?=[A-Z])', text) if s.strip()]