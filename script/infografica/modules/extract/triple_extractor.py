# modules/extract/triple_extractor.py

import json
import re
import logging
from typing import Optional
from langchain_community.llms import Ollama
from modules.ingest.chunker import Chunk

logger = logging.getLogger(__name__)


class TripleExtractor:
    def __init__(self, model_name: str = "mistral:7b-instruct"):
        # Ho scelto il formato instruct perché i modelli base
        # non seguono istruzioni strutturate in modo affidabile.
        # La versione instruct è addestrata esplicitamente su
        # instruction-following, critico per l'output JSON.
        self.llm = Ollama(
            model=model_name,
            temperature=0.0,      # deterministico: voglio fatti, non creatività
            num_predict=2048,     # sufficiente per 25 triple + struttura JSON
            num_ctx=4096          # context window: chunk (800t) + prompt (~500t) + output
        )
        self.prompt_template = self._load_prompt()

    def _load_prompt(self) -> str:
        with open("prompts/triple_extraction.txt", "r") as f:
            return f.read()

    def extract_from_chunk(self, chunk: Chunk) -> list[dict]:
        """
        Cosa: Invia il chunk all'LLM locale e ottiene le triple.
        Come: Formatta il prompt con anchor entities e testo del chunk,
              poi esegue retry con fallback se il JSON è malformato.
        Perché: I modelli locali 8B hanno un failure rate ~15-20%
                sulla formattazione JSON. Senza retry, perderei
                un chunk su 5, con effetti catastrofici sul grafo.
        """
        anchor_str = ", ".join(chunk.previous_entities_anchor) if chunk.previous_entities_anchor else "None"
        
        prompt = self.prompt_template.format(
            previous_entities_anchor=anchor_str,
            chunk_text=chunk.text
        )

        raw_output = self.llm.invoke(prompt)
        triples = self._parse_and_validate(raw_output, chunk)
        
        return triples

    def _parse_and_validate(self, raw: str, chunk: Chunk) -> list[dict]:
        """
        Cosa: Estrae il JSON dall'output grezzo dell'LLM.
        Come: Prima provo parsing diretto, poi uso regex per estrarre
              il blocco JSON anche se il modello ha aggiunto testo extra.
        Perché: Anche con temperature=0 e prompt strict, Mistral/Llama
                a volte premette "Sure! Here are..." al JSON.
                Questa strategia a cascata gestisce i casi edge
                senza sprecare risorse su un secondo LLM call.
        """
        # Tentativo 1: parsing diretto
        try:
            triples = json.loads(raw.strip())
            return self._filter_low_confidence(triples)
        except json.JSONDecodeError:
            pass

        # Tentativo 2: estrazione regex del blocco JSON
        json_match = re.search(r'\[.*\]', raw, re.DOTALL)
        if json_match:
            try:
                triples = json.loads(json_match.group())
                return self._filter_low_confidence(triples)
            except json.JSONDecodeError:
                pass

        # Fallback: log e ritorno lista vuota, mai eccezione non gestita.
        # Preferisco perdere un chunk al crash dell'intera pipeline.
        logger.warning(
            f"[TripleExtractor] JSON parse failed for chunk {chunk.id} "
            f"of doc {chunk.doc_id}. Raw output: {raw[:200]}..."
        )
        return []

    def _filter_low_confidence(self, triples: list) -> list[dict]:
        # Ho impostato 0.4 come soglia minima sperimentalmente:
        # sotto questo valore le triple tendono a essere allucinazioni
        # relazionali (connessioni che l'LLM "inventa" per coerenza).
        CONFIDENCE_THRESHOLD = 0.4
        return [
            t for t in triples
            if isinstance(t, dict)
            and all(k in t for k in ["head", "relation", "tail"])
            and t.get("confidence", 1.0) >= CONFIDENCE_THRESHOLD
        ]