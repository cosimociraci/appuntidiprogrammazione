import os
import json
import requests
import hashlib
from collections import Counter

# ---------------------------------------------------------------------------
# Configurazione centralizzata: tengo tutto qui per modifiche rapide
# ---------------------------------------------------------------------------
API_URL      = "http://localhost:11434/api/generate"
MODEL_NAME   = "qwen2.5-coder:3b"
ARTICOLI_DIR = "_articoli"
CACHE_FILE   = "tag_cache.json"
OUTPUT_FILE  = "top_tags.txt"
TOP_N        = 20

# ---------------------------------------------------------------------------
# Utility: hash MD5 del contenuto per rilevare modifiche al file senza
# dover rileggere l'intera cache a confronto byte per byte
# ---------------------------------------------------------------------------
def get_file_hash(content: str) -> str:
    return hashlib.md5(content.encode("utf-8")).hexdigest()

# ---------------------------------------------------------------------------
# Cache su disco: carico all'avvio, salvo incrementalmente dopo ogni LLM call
# ---------------------------------------------------------------------------
def load_cache() -> dict:
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_cache(cache: dict) -> None:
    # Scrivo su file temporaneo e poi rinomino per evitare corruzione
    # in caso di interruzione durante la scrittura
    tmp = CACHE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=4, ensure_ascii=False)
    os.replace(tmp, CACHE_FILE)

# ---------------------------------------------------------------------------
# Chiamata LLM: chiedo esattamente i tag tecnici, temperatura bassa per
# output deterministico e coerente tra run successivi
# ---------------------------------------------------------------------------
def get_tags_from_llm(content: str) -> list[str]:
    prompt = f"""Analizza il seguente articolo tecnico ed estrai esattamente 50 tag (parole chiave) in minuscolo.
I tag devono rappresentare tecnologie, linguaggi, pattern e concetti chiave.
NON tradurre i termini tecnici in italiano (es. usa 'virtual threads', 'garbage collector', 'pattern matching').
Restituisci ESCLUSIVAMENTE i tag separati da virgola, senza commenti, senza numerazione, senza testo aggiuntivo.

ARTICOLO:
{content[:5000]}"""

    payload = {
        "model":   MODEL_NAME,
        "prompt":  prompt,
        "stream":  False,
        "options": {"temperature": 0.1}
    }

    try:
        response = requests.post(API_URL, json=payload, timeout=120)
        response.raise_for_status()
        raw = response.json().get("response", "")
        # Filtro token vuoti o troppo corti (rumore del modello)
        tags = [t.strip().lower() for t in raw.split(",") if len(t.strip()) > 1]
        return tags
    except requests.exceptions.Timeout:
        print("  [!] Timeout LLM superato.")
        return []
    except Exception as e:
        print(f"  [!] Errore API: {e}")
        return []

# ---------------------------------------------------------------------------
# Output finale: scrivo su file i top N tag con conteggio occorrenze,
# così ho un artefatto persistente senza dipendere dall'output del terminale
# ---------------------------------------------------------------------------
def write_output(classifica: list[tuple[str, int]]) -> None:
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(f"TOP {TOP_N} TAG - generato da {MODEL_NAME}\n")
        f.write("=" * 40 + "\n")
        for i, (tag, count) in enumerate(classifica, 1):
            f.write(f"{i:2}. {tag:<30} ({count} occorrenze)\n")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    if not os.path.exists(ARTICOLI_DIR):
        print(f"[ERRORE] Cartella '{ARTICOLI_DIR}' non trovata.")
        return

    cache     = load_cache()
    all_tags  = []
    file_list = [f for f in os.listdir(ARTICOLI_DIR) if f.endswith(".md")]

    if not file_list:
        print("[ERRORE] Nessun file .md trovato.")
        return

    print(f"Trovati {len(file_list)} articoli. Modello: {MODEL_NAME}\n")

    for i, filename in enumerate(file_list, 1):
        path = os.path.join(ARTICOLI_DIR, filename)

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        file_hash = get_file_hash(content)

        # Uso la cache se il file non è cambiato dall'ultima analisi
        if filename in cache and cache[filename].get("hash") == file_hash:
            tags = cache[filename].get("tags", [])
            print(f"[{i:>3}/{len(file_list)}] [CACHE] {filename}")
        else:
            print(f"[{i:>3}/{len(file_list)}] [LLM]   {filename} ... ", end="", flush=True)
            tags = get_tags_from_llm(content)

            if tags:
                # Salvo immediatamente: se lo script viene interrotto
                # non perdo i tag già estratti
                cache[filename] = {"hash": file_hash, "tags": tags}
                save_cache(cache)
                print(f"{len(tags)} tag estratti.")
            else:
                # Non metto in cache i fallimenti: al prossimo avvio
                # il file verrà ritentato automaticamente
                print("FALLITO, verrà ritentato al prossimo avvio.")

        all_tags.extend(tags)

    if not all_tags:
        print("\n[ERRORE] Nessun tag raccolto. Controlla la connessione a Ollama.")
        return

    classifica = Counter(all_tags).most_common(TOP_N)

    write_output(classifica)

    print(f"\n{'='*40}")
    print(f"  TOP {TOP_N} TAG  →  salvati in '{OUTPUT_FILE}'")
    print(f"{'='*40}")
    for i, (tag, count) in enumerate(classifica, 1):
        print(f"{i:2}. {tag:<30} ({count} occorrenze)")


if __name__ == "__main__":
    main()