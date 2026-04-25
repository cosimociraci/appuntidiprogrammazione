import os
import re
import json
import requests

# ---------------------------------------------------------------------------
# Configurazione
# ---------------------------------------------------------------------------
ARTICOLI_DIR = "_articoli"
CACHE_FILE   = "tag_cache.json"
API_URL      = "http://localhost:11434/api/generate"
MODEL_NAME   = "qwen2.5-coder:3b"

ALLOWED_TAGS = {
    "java", "db", "sql", "spring boot", "thymeleaf", "javascript",
    "pattern matching", "garbage collector", "concorrenza", "postgresql",
    "threads", "performance", "concurrency", "query", "analyze", "multithreading"
}

# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------
def load_cache(path: str) -> dict:
    if not os.path.exists(path):
        print(f"[ERRORE] Cache '{path}' non trovata. Esegui prima lo script di analisi.")
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# ---------------------------------------------------------------------------
# Parsing front matter: leggo solo tech e tags, niente altro
# ---------------------------------------------------------------------------
def extract_frontmatter_fields(content: str) -> dict:
    fields = {}
    match = re.search(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return fields

    fm = match.group(1)

    tech_match = re.search(r'^tech:\s*"?([^"\n]+)"?', fm, re.MULTILINE)
    if tech_match:
        fields["tech"] = tech_match.group(1).strip().lower()

    tags_match = re.search(r'^tags:\s*(\[.*?\])', fm, re.MULTILINE)
    if tags_match:
        try:
            fields["tags"] = json.loads(tags_match.group(1))
        except json.JSONDecodeError:
            fields["tags"] = []

    return fields

# ---------------------------------------------------------------------------
# Calcolo tag finali dalla combinazione di front matter + cache LLM
# ---------------------------------------------------------------------------
def compute_final_tags(fields: dict, cached_tags: list[str]) -> list[str]:
    candidates = []

    tech = fields.get("tech", "")
    if tech:
        candidates.append(tech)

    for t in fields.get("tags", []):
        candidates.append(t.strip().lower())

    for t in cached_tags:
        candidates.append(t.strip().lower())

    seen, result = set(), []
    for t in candidates:
        if t in ALLOWED_TAGS and t not in seen:
            seen.add(t)
            result.append(t)

    return result

# ---------------------------------------------------------------------------
# Fallback LLM: usato SOLO quando compute_final_tags restituisce lista vuota.
# Passo all'LLM il contenuto del file + i tag della cache + la whitelist,
# e chiedo di scegliere quelli più pertinenti tra i soli ALLOWED_TAGS.
# L'LLM non deve inventare nulla: la risposta è vincolata alla whitelist.
# ---------------------------------------------------------------------------
def get_fallback_tags_from_llm(content: str, cached_tags: list[str]) -> list[str]:
    allowed_list  = ", ".join(sorted(ALLOWED_TAGS))
    cached_sample = ", ".join(cached_tags[:30]) if cached_tags else "nessuno"

    prompt = f"""Hai un articolo tecnico e devi assegnargli i tag più pertinenti.
Puoi scegliere ESCLUSIVAMENTE tra questi tag ammessi:
{allowed_list}

I tag estratti automaticamente dall'articolo (usa come contesto):
{cached_sample}

Analizza il seguente articolo e restituisci SOLO i tag pertinenti scelti dalla lista ammessa.
Separali con una virgola. Nessun commento, nessun testo aggiuntivo.
Scegli almeno 1 tag, al massimo 5.

ARTICOLO:
{content[:3000]}"""

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

        # Filtro la risposta: accetto solo token che siano esattamente nella whitelist
        candidates = [t.strip().lower() for t in raw.split(",") if t.strip()]
        result     = list(dict.fromkeys(t for t in candidates if t in ALLOWED_TAGS))
        return result

    except requests.exceptions.Timeout:
        print("  [!] Timeout LLM fallback.")
        return []
    except Exception as e:
        print(f"  [!] Errore LLM fallback: {e}")
        return []

# ---------------------------------------------------------------------------
# Sostituzione chirurgica della sola riga tags nel front matter
# ---------------------------------------------------------------------------
def replace_tags_in_content(content: str, new_tags: list[str]) -> str:
    new_tags_str = json.dumps(new_tags, ensure_ascii=False)
    new_line     = f"tags: {new_tags_str}"

    new_content, n = re.subn(
        r'^tags:\s*\[.*?\]',
        new_line,
        content,
        count=1,
        flags=re.MULTILINE
    )

    if n == 0:
        print("  [!] Riga tags non trovata, file non modificato.")
        return content

    return new_content

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    cache = load_cache(CACHE_FILE)
    if not cache:
        return

    file_list = [f for f in os.listdir(ARTICOLI_DIR) if f.endswith(".md")]
    if not file_list:
        print("[ERRORE] Nessun file .md trovato.")
        return

    print(f"Trovati {len(file_list)} articoli.\n")

    for i, filename in enumerate(file_list, 1):
        path = os.path.join(ARTICOLI_DIR, filename)

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        fields      = extract_frontmatter_fields(content)
        cached_tags = cache.get(filename, {}).get("tags", [])

        if not fields:
            print(f"[{i:>3}/{len(file_list)}] [SKIP]    {filename} — front matter non trovato.")
            continue

        final_tags = compute_final_tags(fields, cached_tags)

        # Se la combinazione front matter + cache non produce nessun tag ammesso,
        # chiedo all'LLM di scegliere direttamente dalla whitelist leggendo
        # il contenuto del file. È il percorso lento: usato solo come ultima risorsa.
        if not final_tags:
            print(f"[{i:>3}/{len(file_list)}] [FALLBACK] {filename} — nessun tag trovato, interrogo LLM...")
            final_tags = get_fallback_tags_from_llm(content, cached_tags)

            if not final_tags:
                # Caso estremo: LLM non riesce a classificare il file.
                # Inserisco il tag tecnico grezzo dal front matter se esiste,
                # altrimenti salto per non scrivere un array vuoto.
                tech = fields.get("tech", "")
                if tech:
                    final_tags = [tech]
                    print(f"           Fallback LLM fallito, uso solo tech: [{tech}]")
                else:
                    print(f"           Impossibile assegnare tag. File saltato.")
                    continue

        new_content = replace_tags_in_content(content, final_tags)

        if new_content == content:
            print(f"[{i:>3}/{len(file_list)}] [=]       {filename} — nessuna modifica.")
            continue

        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(new_content)
        os.replace(tmp, path)

        print(f"[{i:>3}/{len(file_list)}] [OK]      {filename} — tags: {final_tags}")


if __name__ == "__main__":
    main()