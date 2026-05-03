import os
import re
import sys
import json
import time
import traceback
from pathlib import Path
from datetime import datetime
from openai import OpenAI

# ---------------------------------------------------------------------------
# CONFIGURAZIONE MODELLI
# ---------------------------------------------------------------------------

MODEL_CRITIC = "nvidia/nemotron-3-super-120b-a12b:free"
KEY_CRITIC   = "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"

MODEL_LOGIC  = "minimax/minimax-m2.5:free"
KEY_LOGIC    = "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"

LOCAL_MODEL_CRITIC = "gemma2:latest"
LOCAL_MODEL_LOGIC  = "qwen2.5-coder:latest"
OLLAMA_URL         = "http://localhost:11434/v1"

CHUNK_SIZE = 35_000 
MAX_TOTAL_CHARS = 1_000_000 

# ---------------------------------------------------------------------------
# PROVIDER CON LOGICA DI FALLBACK UNICA
# ---------------------------------------------------------------------------

class ModelProvider:
    def __init__(self):
        self.client_critic_remote = OpenAI(api_key=KEY_CRITIC, base_url="https://openrouter.ai/api/v1")
        self.client_logic_remote  = OpenAI(api_key=KEY_LOGIC,  base_url="https://openrouter.ai/api/v1")
        self.client_local = OpenAI(api_key="ollama", base_url=OLLAMA_URL)
        # Se il remoto fallisce una volta, non ci riproviamo più per questa esecuzione
        self.remote_active = True

    def get_completion(self, task_type, system_prompt, user_content):
        is_critic = (task_type == "critic")
        remote_client = self.client_critic_remote if is_critic else self.client_logic_remote
        remote_model  = MODEL_CRITIC if is_critic else MODEL_LOGIC
        local_model   = LOCAL_MODEL_CRITIC if is_critic else LOCAL_MODEL_LOGIC

        # 1. TENTATIVO REMOTO (Solo se ancora attivo)
        if self.remote_active:
            try:
                print(f"    [REMOTE] Invio a {remote_model.split('/')[-1]}...")
                resp = remote_client.chat.completions.create(
                    model=remote_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Contenuto da elaborare:\n\n{user_content}"}
                    ],
                    temperature=0.3,
                    timeout=150
                )
                content = resp.choices[0].message.content
                if content: return content
            except Exception as e:
                print(f"    [AVVISO] Fallimento remoto ({type(e).__name__}). Disattivo remoto e passo a locale.")
                self.remote_active = False # Fallimento definitivo per questa sessione

        # 2. FALLBACK LOCALE
        try:
            print(f"    [LOCAL] Invio a {local_model}...")
            resp = self.client_local.chat.completions.create(
                model=local_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Contenuto da elaborare:\n\n{user_content}"}
                ],
                temperature=0.3
            )
            return resp.choices[0].message.content
        except Exception as e:
            print(f"    [ERRORE] Anche Ollama ha fallito: {e}")
            return None

# ---------------------------------------------------------------------------
# ISTRUZIONI
# ---------------------------------------------------------------------------

def build_instructions(data_oggi: str) -> dict:
    return {
        "review": f"""TASK 1: RECENSIONE JEKYLL (.md). Genera una recensione da critico letterario e programmatore.
Inizia con il seguente front matter ESATTO:
---
layout: libro
title: TITOLO DEL LIBRO
autore: AUTORE
sintesi: >
      BREVE SINTESI DI MAX 50 PAROLE
date: {data_oggi}
tech: SINGOLO TAG CHE IDENTIFICA IL GENERE
link: LINK AD AMAZON DEL LIBRO
link_img: LINK DELL'IMMAGINE DEL LIBRO PRESA DA AMAZON
---

Dopo il front matter, includi 15 punti chiave (H4 + paragrafo).
Lunghezza corpo: 1200-1800 parole.
Tono: prima persona, divulgativo ma tecnico.""",

        "mindmap": """TASK 2: MAPPA MENTALE JSON (mindmap.json)
Crea una mappa mentale bilanciata e profonda basata sui concetti chiave del libro.
Suddividi gli argomenti in macro-categorie logiche (da 3 a 5 per il lato 'left' e da 3 a 5 per il lato 'right').
Ogni macro-categoria ha almeno 5 ulteriori sotto-categorie.

REGOLE STRUTTURALI OBBLIGATORIE:
1. "title": Titolo del Libro. Se lungo, usa '\\n' per andare a capo.
2. "left" e "right": Ciascuno deve contenere esattamente 3 oggetti categoria.
3. Ogni categoria deve avere:
   - "name": titolo evocativo per la macro-categoria.
   - "color": codice esadecimale (es: #e74c3c).
   - "items": lista sotto-categorie di esattamente alemeno 5 sotto-punti.
4. Ogni sotto-punto è un array di due stringhe: ["Etichetta Breve", "Descrizione di una riga"].

ESEMPIO FORMATO:
{
  "title": "Titolo\\nLibro",
  "left": [
    {
      "name": "Nome Categoria",
      "color": "#hex",
      "items": [["Concetto", "Spiegazione breve."], ...]
    }
  ],
  "right": [...]
}

Restituisci SOLO il JSON valido.""",

        "cheatsheet": """TASK 3: LOGIC TABLES JSON (cheatsheet.json)
Genera un cheat sheet tecnico in formato JSON basato sui concetti pratici del libro.

REGOLE DI STRUTTURA:
1. "meta": titoli e colori.
   - "title_accent", "title_rest", "accent_color_hex", "title_rest_color_hex", "background".

2. "cards": esattamente 15 card numerate, ognuna con "id", "title", "color" e "content".
   - Colori disponibili: orange, green, blue, navy, amber, teal, red, darkgreen, purple.

3. COMPONENTI SUPPORTATI:
   - {"type": "table", "headers": [...], "rows": [[...]], "key_col": true}
   - {"type": "list", "style": "arrow|bullet|numbered", "items": [...]}
   - {"type": "kv_list", "items": [{"key": "...", "value": "..."}]}
   - {"type": "shot_grid", "items": [{"label": "TAG", "style": "zero|one|few", "text": "..."}]}
   - {"type": "check_grid", "items": [...]}
   - {"type": "note", "content": "...", "html": true}
   - {"type": "section_label", "content": "..."}
   - {"type": "divider"}

4. Se una card ha molti contenuti, aggiungi "force_layout": "full" alla card.

Restituisci SOLO il JSON valido."""
    }

# ---------------------------------------------------------------------------
# ELABORAZIONE CON PERSISTENZA SUMMARY
# ---------------------------------------------------------------------------

def process_large_book(book_content, provider, task_key, instructions, cache_dir: Path):
    full_text = book_content[:MAX_TOTAL_CHARS]
    chunks = [full_text[i:i+CHUNK_SIZE] for i in range(0, len(full_text), CHUNK_SIZE)]
    
    if len(chunks) == 1:
        return provider.get_completion("critic" if task_key == "review" else "logic", instructions, chunks[0])

    summaries = []
    cache_dir.mkdir(parents=True, exist_ok=True)
    print(f"  [MAP-REDUCE] {len(chunks)} blocchi rilevati.")
    
    for idx, chunk in enumerate(chunks):
        cache_file = cache_dir / f"summary_chunk_{idx}.txt"
        
        # Se il summary esiste già, lo carichiamo
        if cache_file.exists():
            print(f"    - Caricamento summary blocco {idx+1}/{len(chunks)} da cache.")
            summaries.append(cache_file.read_text(encoding="utf-8"))
            continue

        print(f"    - Elaborazione summary blocco {idx+1}/{len(chunks)}...")
        map_prompt = "Estrai concetti chiave, dettagli tecnici e punti salienti. Sii dettagliato ma schematico."
        summary = provider.get_completion("logic", map_prompt, chunk)
        
        if summary:
            cache_file.write_text(summary, encoding="utf-8")
            summaries.append(summary)
            time.sleep(1)
        else:
            print(f"    [FAIL] Impossibile ottenere summary per blocco {idx}")

    combined_context = "\n\n".join(summaries)
    print(f"  [FINAL] Generazione {task_key} dai summary accumulati...")
    return provider.get_completion("critic" if task_key == "review" else "logic", instructions, combined_context)

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    force_regenerate = "--force" in sys.argv
    provider = ModelProvider()
    
    base_dir = Path(__file__).parent
    libri_dir = base_dir / "libri"
    out_dir = base_dir / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    txt_files = list(libri_dir.glob("*.txt"))
    if not txt_files:
        print("Nessun file .txt trovato.")
        return

    instructions_map = build_instructions(datetime.now().strftime("%Y-%m-%d"))

    for filepath in txt_files:
        book_name = filepath.stem
        print(f"\n{'='*70}\nPROCESSO: {book_name}\n{'='*70}")
        
        book_content = filepath.read_text(encoding="utf-8")
        book_out_dir = out_dir / book_name
        # Sottocartella per i summary temporanei
        cache_dir = book_out_dir / "cache_summaries"
        book_out_dir.mkdir(parents=True, exist_ok=True)

        tasks = [
            ("review.md", "review", "text"),
            ("mindmap.json", "mindmap", "json"),
            ("cheatsheet.json", "cheatsheet", "json")
        ]

        for filename, task_key, fmt in tasks:
            dest_path = book_out_dir / filename
            if dest_path.exists() and not force_regenerate:
                print(f"  [SKIP] {filename} esiste già.")
                continue

            result = process_large_book(book_content, provider, task_key, instructions_map[task_key], cache_dir)
            
            if result:
                if fmt == "json":
                    result = re.sub(r"```(?:json)?\s*(.*?)\s*```", r"\1", result, flags=re.DOTALL)
                    start, end = result.find("{"), result.rfind("}")
                    if start != -1 and end != -1:
                        result = result[start : end + 1].strip()
                
                dest_path.write_text(result, encoding="utf-8")
                print(f"  [OK] Creato {filename}")
            else:
                print(f"  [FAIL] Impossibile completare {filename}")

    print("\n[DONE] Pipeline completata.")

if __name__ == "__main__":
    main()