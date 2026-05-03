#!/usr/bin/env python3
"""
Pipeline NLP senza LLM per la generazione di mindmap.json e cheatsheet.json
da file .txt di libri.

Dipendenze:
    pip install spacy sentence-transformers scikit-learn numpy --break-system-packages
    python -m spacy download it_core_news_lg   # italiano (consigliato)
    python -m spacy download en_core_web_lg    # inglese

La prima esecuzione scarica il modello sentence-transformer (~80MB) e il
modello spaCy (~550MB per lg). Tutto viene messo in cache locale.

Uso:
    python nlp_pipeline.py              # salta i file gia' esistenti
    python nlp_pipeline.py --force      # rigenera tutto
    python nlp_pipeline.py --lang=en    # forza inglese (default: it)
"""

import re
import sys
import json
from pathlib import Path
from collections import Counter

import spacy
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans

# ---------------------------------------------------------------------------
# CONFIGURAZIONE
# ---------------------------------------------------------------------------

# Ho alzato a 150 rispetto alla versione YAKE perché i noun chunks hanno
# qualita' linguistica garantita: nessun rischio di function words.
N_KEYPHRASES = 150

N_CLUSTERS_MINDMAP = 6   # -> 3 left + 3 right
N_CLUSTERS_CHEAT   = 15  # -> 15 card

MIN_ITEMS_MINDMAP = 5
MAX_ITEMS_MINDMAP = 8
MAX_ITEMS_CHEAT   = 8

MAX_CHARS = 1_000_000

MODEL_NAME = "all-MiniLM-L6-v2"

# 0.92 elimina quasi-duplicati senza toccare concetti distinti vicini
DEDUP_THRESHOLD = 0.92

SPACY_MODELS = {
    "it": ["it_core_news_lg", "it_core_news_sm"],
    "en": ["en_core_web_lg",  "en_core_web_sm"],
}

COLORS_MINDMAP = [
    "#e74c3c", "#3498db", "#2ecc71",
    "#f39c12", "#9b59b6", "#1abc9c",
]

COLORS_CHEAT = [
    "orange", "green",    "blue",  "navy",  "amber",
    "teal",   "red",      "orange","green", "darkgreen",
    "purple", "blue",     "navy",  "teal",  "red",
]

# ---------------------------------------------------------------------------
# CARICAMENTO SPACY CON FALLBACK
# ---------------------------------------------------------------------------

def load_spacy(lang: str) -> spacy.Language:
    """
    Carico il modello spaCy per la lingua indicata.
    Provo prima "lg" (vettori migliori), poi "sm" come fallback.
    Se nessuno e' installato, stampo il comando corretto e interrompo:
    un errore esplicito e' meglio di un generico ImportError.
    """
    candidates = SPACY_MODELS.get(lang, SPACY_MODELS["it"])
    for model_name in candidates:
        try:
            nlp = spacy.load(model_name)
            print(f"  [spaCy] Modello '{model_name}' caricato.")
            return nlp
        except OSError:
            continue
    install_cmd = f"python -m spacy download {candidates[0]}"
    raise SystemExit(
        f"\n[ERRORE] Nessun modello spaCy per lang='{lang}'.\n"
        f"Installa con:\n    {install_cmd}\n"
    )

# ---------------------------------------------------------------------------
# PREPROCESSING TESTO
# ---------------------------------------------------------------------------

_BIBLIOGRAPHY_PATTERNS = [
    re.compile(r'https?://\S+'),
    re.compile(r'^\s*\*\s+'),
    re.compile(r'^\s*\d{1,4}\.\s+[A-Z]'),
    re.compile(r'\bpp?\.\s*\d+'),
    re.compile(r'\b(doi|isbn|issn)\b', re.I),
    re.compile(r'«[^»]{3,60}»,\s*\d{4}'),
]

def strip_support_sections(text: str) -> str:
    """
    Rimuovo blocchi bibliografici/note analizzando finestre di 20 righe.
    Se piu' del 60% delle righe in una finestra corrisponde ai pattern
    bibliografici, scarto l'intero blocco.
    Ho scelto la finestra invece della singola riga per evitare di
    eliminare frasi del corpo che per caso contengono un anno o un numero.
    """
    lines = text.splitlines()
    clean_lines = []
    window = 20
    i = 0
    while i < len(lines):
        block = lines[i : i + window]
        dirty = sum(
            1 for line in block
            if any(p.search(line) for p in _BIBLIOGRAPHY_PATTERNS)
        )
        if dirty / max(len(block), 1) > 0.60:
            i += window
        else:
            clean_lines.append(lines[i])
            i += 1
    return "\n".join(clean_lines)


def split_sentences(text: str) -> list[str]:
    """
    Split regex su . ! ? + maiuscola: robusto su italiano e inglese
    senza toccare abbreviazioni tipo "Dr." o "fig. 3".
    """
    text = re.sub(r'\s+', ' ', text).strip()
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-ZA-Za-zÀ-ÜÀ-Ö])', text)
    return [s.strip() for s in sentences if 30 < len(s.strip()) < 450]

# ---------------------------------------------------------------------------
# ESTRAZIONE NOUN CHUNKS CON SPACY
# ---------------------------------------------------------------------------

# POS non accettabili come testa del chunk: eliminano pronomi, congiunzioni,
# avverbi e preposizioni che erano il problema principale nella versione YAKE.
_INVALID_ROOT_POS = {
    "PRON", "CCONJ", "SCONJ", "ADV", "DET",
    "ADP", "PUNCT", "AUX", "VERB", "NUM", "PART"
}

# Stopword editoriali non filtrate da spaCy ma prive di valore come keyphrases
_EXTRA_STOPWORDS = {
    "capitolo", "pagina", "figura", "esempio", "caso", "modo", "tipo",
    "parte", "libro", "autore", "edizione", "anno", "volta", "cosa",
    "fatto", "punto", "senso", "forma", "numero",
}

def is_valid_chunk(chunk: spacy.tokens.Span) -> bool:
    """
    Valido il noun chunk su 5 criteri cumulativi:
    1. Testa NOUN o PROPN: garantisce che nomini un concetto.
    2. 2-5 token: scarto singoli sostantivi ambigui e frasi intere.
    3. Non inizia con ADP/DET: elimina "del machine learning" -> "machine learning".
    4. Almeno un token non-stopword.
    5. Testa non in blacklist editoriale.
    """
    if chunk.root.pos_ not in {"NOUN", "PROPN"}:
        return False
    tokens = [t for t in chunk if not t.is_space]
    if len(tokens) < 2 or len(tokens) > 5:
        return False
    if tokens[0].pos_ in {"ADP", "DET"}:
        return False
    if all(t.is_stop for t in tokens):
        return False
    if chunk.root.lemma_.lower() in _EXTRA_STOPWORDS:
        return False
    return True


def normalize_chunk(chunk: spacy.tokens.Span) -> str:
    """
    Normalizzo in stringa capitalizzata.
    Uso il testo originale (non i lemmi) per leggibilita':
    "machine learning" e' piu' chiaro di "machine learn" dai lemmi inglesi.
    """
    text = re.sub(r'\s+', ' ', chunk.text).strip()
    text = re.sub(r'[^\w\s\-àèéìòùÀÈÉÌÒÙ]', '', text).strip()
    return text.capitalize() if text else ""


def extract_keyphrases_spacy(text: str, nlp: spacy.Language, n: int) -> list[str]:
    """
    Estraggo noun chunks e li ranko per frequenza.
    Perche' frequenza e non TF-IDF: su singolo documento senza corpus
    di riferimento, la frequenza e' il proxy piu' robusto di rilevanza.
    Processo a blocchi da 100k per non saturare la RAM di spaCy.
    Deduplicazione lessicale: tengo il piu' lungo tra coppie dove uno
    e' sottostringa dell'altro ("machine learning" vs "il machine learning").
    """
    nlp.max_length = MAX_CHARS + 10_000
    raw_chunks: list[str] = []

    for start in range(0, len(text), 100_000):
        block = text[start : start + 100_000]
        doc   = nlp(block)
        for chunk in doc.noun_chunks:
            normalized = normalize_chunk(chunk)
            if normalized and is_valid_chunk(chunk):
                raw_chunks.append(normalized.lower())

    if not raw_chunks:
        return []

    freq   = Counter(raw_chunks)
    ranked = [kp.capitalize() for kp, _ in freq.most_common(n * 3)]

    # Deduplicazione lessicale per sottostringa
    final: list[str] = []
    seen_lower: set[str] = set()
    for kp in ranked:
        kp_l = kp.lower()
        dominated = False
        for existing in list(seen_lower):
            if kp_l in existing or existing in kp_l:
                if len(kp_l) > len(existing):
                    seen_lower.discard(existing)
                    final = [x for x in final if x.lower() != existing]
                else:
                    dominated = True
                    break
        if not dominated:
            seen_lower.add(kp_l)
            final.append(kp)
        if len(final) >= n * 2:
            break

    return final[:n]

# ---------------------------------------------------------------------------
# EMBEDDINGS
# ---------------------------------------------------------------------------

def embed(model: SentenceTransformer, texts: list[str]) -> np.ndarray:
    """
    Embeddings L2-normalizzati: dot product = cosine similarity.
    Batch size 64 e' un buon compromesso tra velocita' e uso di RAM su CPU.
    """
    vecs  = model.encode(texts, show_progress_bar=False, batch_size=64)
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    return vecs / np.maximum(norms, 1e-9)

# ---------------------------------------------------------------------------
# DEDUPLICAZIONE EMBEDDING-BASED
# ---------------------------------------------------------------------------

def deduplicate_by_embedding(
    keyphrases: list[str],
    embeddings: np.ndarray,
    threshold: float = DEDUP_THRESHOLD
) -> tuple[list[str], np.ndarray]:
    """
    Rimuovo sinonimi semantici che la deduplicazione lessicale non vede.
    Approccio greedy: scorro in ordine di rilevanza e scarto ogni keyphrase
    con similarity > threshold rispetto a una gia' accettata.
    """
    if not keyphrases:
        return [], np.array([])
    kept_idx = [0]
    for i in range(1, len(keyphrases)):
        sims = embeddings[kept_idx] @ embeddings[i]
        if np.max(sims) < threshold:
            kept_idx.append(i)
    return ([keyphrases[i] for i in kept_idx],
            embeddings[kept_idx])

# ---------------------------------------------------------------------------
# CLUSTERING
# ---------------------------------------------------------------------------

def cluster_keyphrases(embeddings: np.ndarray, n_clusters: int) -> tuple[np.ndarray, np.ndarray]:
    n  = min(n_clusters, len(embeddings))
    km = KMeans(n_clusters=n, random_state=42, n_init=10)
    return km.fit_predict(embeddings), km.cluster_centers_


def find_cluster_name(keyphrases: list[str], embeddings: np.ndarray, centroid: np.ndarray) -> str:
    c_norm = centroid / (np.linalg.norm(centroid) + 1e-9)
    return keyphrases[int(np.argmax(embeddings @ c_norm))]

# ---------------------------------------------------------------------------
# RETRIEVAL DESCRIZIONI ESTRATTIVE
# ---------------------------------------------------------------------------

def find_best_sentence(kp_emb: np.ndarray, sent_embs: np.ndarray,
                       sentences: list[str], max_len: int = 120) -> str:
    """
    La frase piu' vicina alla keyphrase nello spazio embedding diventa
    la descrizione: e' estrattiva (dal testo originale) e attinente al
    contesto per costruzione, non per generazione.
    """
    best = sentences[int(np.argmax(sent_embs @ kp_emb))].strip()
    return best if len(best) <= max_len else best[:max_len - 3] + "..."

# ---------------------------------------------------------------------------
# SELEZIONE AUTOMATICA TIPO CARD
# ---------------------------------------------------------------------------

def select_card_type(items: list[tuple[str, str]]) -> str:
    if not items:
        return "kv_list"
    avg_lbl = sum(len(l.split()) for l, _ in items) / len(items)
    avg_dsc = sum(len(d.split()) for _, d in items) / len(items)
    if avg_lbl <= 2 and len(items) >= 6:
        return "check_grid"
    if avg_dsc > 10:
        return "kv_list"
    if len(items) >= 5:
        return "list"
    return "kv_list"


def build_content_block(card_type: str, items: list[tuple[str, str]]) -> list[dict]:
    if card_type == "kv_list":
        return [{"type": "kv_list",
                 "items": [{"key": l, "value": d} for l, d in items]}]
    if card_type == "check_grid":
        return [{"type": "check_grid", "items": [l for l, _ in items]}]
    # list arrow
    return [{"type": "list", "style": "arrow",
             "items": [f"{l}: {d}" if d else l for l, d in items]}]

# ---------------------------------------------------------------------------
# COSTRUZIONE MINDMAP.JSON
# ---------------------------------------------------------------------------

def build_mindmap(keyphrases, kp_embs, labels, centroids,
                  sent_embs, sentences, book_title) -> dict:
    nodes = []
    for cid in range(N_CLUSTERS_MINDMAP):
        mask  = labels == cid
        c_kps = [kp for kp, m in zip(keyphrases, mask) if m]
        c_emb = kp_embs[mask]
        if len(c_kps) < MIN_ITEMS_MINDMAP:
            continue
        name  = find_cluster_name(c_kps, c_emb, centroids[cid])
        items = [
            [kp, find_best_sentence(emb, sent_embs, sentences)]
            for kp, emb in zip(c_kps[:MAX_ITEMS_MINDMAP], c_emb[:MAX_ITEMS_MINDMAP])
        ]
        nodes.append({"name": name, "color": COLORS_MINDMAP[cid % 6], "items": items})

    while len(nodes) < 6:
        nodes.append(nodes[-1].copy() if nodes else
                     {"name": "Generale", "color": "#999999",
                      "items": [["N/D", "Testo insufficiente."]]})

    title = book_title
    if len(title) > 20:
        mid   = len(title) // 2
        space = title.rfind(' ', 0, mid)
        if space > 0:
            title = title[:space] + "\\n" + title[space + 1:]

    return {"title": title, "left": nodes[:3], "right": nodes[3:6]}

# ---------------------------------------------------------------------------
# COSTRUZIONE CHEATSHEET.JSON
# ---------------------------------------------------------------------------

def build_cheatsheet(keyphrases, kp_embs, labels, centroids,
                     sent_embs, sentences, book_title) -> dict:
    cards = []
    for cid in range(N_CLUSTERS_CHEAT):
        mask  = labels == cid
        c_kps = [kp for kp, m in zip(keyphrases, mask) if m]
        c_emb = kp_embs[mask]
        if not c_kps:
            continue
        name  = find_cluster_name(c_kps, c_emb, centroids[cid])
        items = [
            (kp, find_best_sentence(emb, sent_embs, sentences))
            for kp, emb in zip(c_kps[:MAX_ITEMS_CHEAT], c_emb[:MAX_ITEMS_CHEAT])
        ]
        cards.append({
            "id": cid + 1, "title": name,
            "color":   COLORS_CHEAT[cid % len(COLORS_CHEAT)],
            "content": build_content_block(select_card_type(items), items)
        })

    words = book_title.split()
    mid   = max(1, len(words) // 2)
    return {
        "meta": {
            "title_accent":         " ".join(words[:mid]),
            "title_rest":           " ".join(words[mid:]),
            "accent_color_hex":     "#E07B1E",
            "title_rest_color_hex": "#2B4FBF",
            "background":           "#FFF8DC"
        },
        "cards": cards
    }

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    force = "--force" in sys.argv
    lang  = "it"
    for arg in sys.argv[1:]:
        if arg.startswith("--lang="):
            lang = arg.split("=", 1)[1]

    base_dir  = Path(__file__).parent
    libri_dir = base_dir / "libri"
    out_dir   = base_dir / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    txt_files = list(libri_dir.glob("*.txt"))
    if not txt_files:
        print("[ERRORE] Nessun file .txt trovato in ./libri")
        return

    print(f"[INIT] Carico modello spaCy (lang={lang})...")
    nlp = load_spacy(lang)

    print(f"[INIT] Carico sentence-transformer '{MODEL_NAME}'...")
    st_model = SentenceTransformer(MODEL_NAME)
    print("[INIT] Modelli pronti.\n")

    for filepath in txt_files:
        book_name  = filepath.stem
        book_title = book_name.replace("_", " ").replace("-", " ").title()
        print(f"{'='*60}\nPROCESSO: {book_name}\n{'='*60}")

        book_out = out_dir / book_name
        book_out.mkdir(parents=True, exist_ok=True)

        mm_path = book_out / "mindmap.json"
        cs_path = book_out / "cheatsheet.json"

        if mm_path.exists() and cs_path.exists() and not force:
            print("  [SKIP] Entrambi i file esistono. Usa --force per rigenerare.\n")
            continue

        raw_text = filepath.read_text(encoding="utf-8")[:MAX_CHARS]

        # 1 — PREPROCESSING
        print("  [1/6] Preprocessing...")
        clean_text  = strip_support_sections(raw_text)
        removed_pct = round((1 - len(clean_text) / len(raw_text)) * 100, 1)
        print(f"        Rimosso {removed_pct}% come sezioni di supporto.")

        # 2 — SPLIT FRASI
        print("  [2/6] Split frasi...")
        sentences = split_sentences(clean_text)
        print(f"        {len(sentences)} frasi estratte.")
        if len(sentences) < 10:
            print("  [WARN] Testo troppo corto. Salto.")
            continue

        # 3 — ESTRAZIONE NOUN CHUNKS
        print("  [3/6] Estrazione noun chunks con spaCy...")
        keyphrases = extract_keyphrases_spacy(clean_text, nlp, N_KEYPHRASES)
        print(f"        {len(keyphrases)} keyphrases dopo filtraggio lessicale.")
        if len(keyphrases) < N_CLUSTERS_CHEAT:
            print(f"  [WARN] Solo {len(keyphrases)} keyphrases: cluster potrebbero essere poco distinti.")

        # 4 — EMBEDDINGS + DEDUP SEMANTICA
        print("  [4/6] Embeddings e deduplicazione semantica...")
        kp_embs_raw        = embed(st_model, keyphrases)
        sent_embs          = embed(st_model, sentences)
        keyphrases, kp_embs = deduplicate_by_embedding(keyphrases, kp_embs_raw)
        print(f"        {len(keyphrases)} keyphrases dopo dedup semantica. "
              f"Frasi: {sent_embs.shape[0]}.")

        # 5 — MINDMAP
        if not mm_path.exists() or force:
            print("  [5/6] Clustering mindmap...")
            mm_labels, mm_ctr = cluster_keyphrases(kp_embs, min(N_CLUSTERS_MINDMAP, len(keyphrases)))
            mm_path.write_text(
                json.dumps(build_mindmap(keyphrases, kp_embs, mm_labels, mm_ctr,
                                         sent_embs, sentences, book_title),
                           ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            print(f"  [OK] mindmap.json -> {mm_path}")
        else:
            print("  [5/6] mindmap.json gia' presente.")

        # 6 — CHEATSHEET
        if not cs_path.exists() or force:
            print("  [6/6] Clustering cheatsheet...")
            cs_labels, cs_ctr = cluster_keyphrases(kp_embs, min(N_CLUSTERS_CHEAT, len(keyphrases)))
            cs_path.write_text(
                json.dumps(build_cheatsheet(keyphrases, kp_embs, cs_labels, cs_ctr,
                                             sent_embs, sentences, book_title),
                           ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            print(f"  [OK] cheatsheet.json -> {cs_path}")
        else:
            print("  [6/6] cheatsheet.json gia' presente.")

        print()

    print("[DONE] Pipeline completata.")


if __name__ == "__main__":
    main()