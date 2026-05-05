# modules/pipeline_coordinator.py

import logging
from pathlib import Path
from modules.ingest.document_loader import DocumentLoader
from modules.ingest.chunker import SlidingWindowChunker, Chunk
from modules.extract.triple_extractor import TripleExtractor
from modules.extract.entity_resolver import EntityResolver
from modules.graph.graph_builder import KnowledgeGraphBuilder
from modules.visualization.pyvis_renderer import PyvisRenderer

logger = logging.getLogger(__name__)


class PipelineCoordinator:
    def __init__(self, model_name: str = "mistral:7b-instruct"):
        self.loader = DocumentLoader()
        self.chunker = SlidingWindowChunker()
        self.extractor = TripleExtractor(model_name=model_name)
        self.resolver = EntityResolver()
        self.graph_builder = KnowledgeGraphBuilder()
        self.renderer = PyvisRenderer()

    def run(self, file_path: str, progress_callback=None) -> str:
        """
        Cosa: Esegue l'intera pipeline dal file al grafo HTML.
        Come: Sequenza lineare load→chunk→extract→resolve→build→render.
              Il progress_callback permette a Streamlit di aggiornare
              la progress bar senza bloccare l'UI.
        Perché: Ho scelto una pipeline sincrona (non async) per semplicità
                e perché Ollama locale è già il bottleneck: parallelizzare
                le chiamate LLM non darebbe benefici su una singola GPU/CPU.
        """
        doc_id = Path(file_path).stem
        
        # Step 1: carico il documento
        if progress_callback: progress_callback(0.05, "Caricamento documento...")
        raw_text = self.loader.load(file_path)

        # Step 2: chunking con sliding window
        if progress_callback: progress_callback(0.10, "Segmentazione in chunk...")
        chunks = list(self.chunker.chunk_document(raw_text, doc_id))
        
        logger.info(f"[Pipeline] {len(chunks)} chunk generati per '{doc_id}'")

        # Step 3: estrazione triple per ogni chunk
        # Aggiorno l'anchor con le entità estratte dal chunk corrente
        # prima di processare il successivo — questo è il meccanismo
        # di "memoria" cross-chunk.
        all_triples = []
        previous_entities = []
        
        for i, chunk in enumerate(chunks):
            chunk.previous_entities_anchor = previous_entities
            
            if progress_callback:
                progress = 0.10 + (i / len(chunks)) * 0.65
                progress_callback(progress, f"Analisi chunk {i+1}/{len(chunks)}...")
            
            triples = self.extractor.extract_from_chunk(chunk)
            all_triples.extend(triples)
            
            # Aggiorno l'anchor con le entità più menzionate di questo chunk
            chunk_entities = list({t["head"] for t in triples} | {t["tail"] for t in triples})
            previous_entities = chunk_entities[:self.chunker.anchor_entity_count]

        logger.info(f"[Pipeline] {len(all_triples)} triple estratte totali")

        # Step 4: risoluzione entità (deduplicazione + normalizzazione)
        if progress_callback: progress_callback(0.78, "Risoluzione entità...")
        resolved_triples = self.resolver.resolve(all_triples)

        # Step 5: costruzione grafo e clustering
        if progress_callback: progress_callback(0.85, "Costruzione grafo...")
        self.graph_builder.add_triples(resolved_triples, doc_id)
        partition = self.graph_builder.compute_clusters()

        # Step 6: rendering
        if progress_callback: progress_callback(0.95, "Rendering visualizzazione...")
        output_path = self.renderer.render(
            self.graph_builder.graph,
            partition,
            doc_title=doc_id
        )

        if progress_callback: progress_callback(1.0, "Completato.")
        return output_path