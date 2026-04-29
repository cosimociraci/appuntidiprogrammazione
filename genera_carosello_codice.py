#!/usr/bin/env python3
"""
genera_carosello.py
-------------------
Scansiona _articoli/*.md, seleziona solo quelli con layout: code,
estrae il primo blocco ```java e genera un carosello di max 10 slide
1080x1080 renderizzate con Playwright.

Logica chiave:
- Max 15 righe visive per slide (le righe lunghe che vanno a capo contano di più)
- Slide 1: mostra il titolo del front matter in testa al codice
- Slide N (ultima): mostra il footer "continua su ..."
- Se il codice non entra in 10 slide, viene troncato e l'ultima mostra il footer
- Output: _articoli/<nome_file_senza_estensione>/slide_01.png, ...
"""

import os
import re
from typing import List, Tuple
import math
import textwrap
from pathlib import Path

import yaml  # pip install pyyaml
from playwright.sync_api import sync_playwright  # pip install playwright + playwright install chromium

# ---------------------------------------------------------------------------
# Costanti di configurazione
# ---------------------------------------------------------------------------

ARTICOLI_DIR   = Path("_articoli")
SLIDES_MAX     = 10
LINES_PER_SLIDE = 20
IMG_SIZE       = 1080          # px, larghezza e altezza della slide quadrata

# Ho scelto 26px come compromesso tra leggibilità e densità di contenuto:
# caratteri Courier New a larghezza fissa ~0.601em → 26*0.601 ≈ 15.6px/char.
# Con un'area utile di ~980px (1080 - 2*50px padding) entrano ~63 caratteri
# per riga prima del wrap. Più grande di così e le righe lunghe di Java
# andrebbero a capo troppo presto riducendo il contenuto per slide.
FONT_SIZE_PX   = 26
PADDING_H      = 50            # padding orizzontale (sinistra/destra) in px
PADDING_V      = 44            # padding verticale (sopra/sotto) in px
LINE_HEIGHT    = 1.55          # moltiplicatore line-height CSS

# Stima empirica: Courier New monospace, 1 carattere ≈ 0.601 * font_size px
# Uso questo valore per calcolare il numero di righe visive di una riga di codice.
CHAR_WIDTH_EM  = 0.601
USABLE_WIDTH   = IMG_SIZE - 2 * PADDING_H   # ~980px
CHARS_PER_LINE = int(USABLE_WIDTH / (FONT_SIZE_PX * CHAR_WIDTH_EM))  # ~62-63

CONTINUA_URL   = "https://icarocomix.github.io/appuntidiprogrammazione/"

# ---------------------------------------------------------------------------
# Palette colori (ispirata a GitHub Dark)
# ---------------------------------------------------------------------------
COLORS = {
    "bg":        "#0d1117",
    "code_fg":   "#e6edf3",
    "title_fg":  "#58a6ff",
    "footer_fg": "#8b949e",
    "counter_fg":"#484f58",
    "border":    "#21262d",
    "kw":        "#ff7b72",   # keyword Java
    "type":      "#ffa657",   # tipo/classe
    "string":    "#a5d6ff",   # stringhe
    "comment":   "#6e7681",   # commenti
    "number":    "#79c0ff",   # numeri
    "annotation":"#d2a8ff",   # @Annotation
}

# ---------------------------------------------------------------------------
# Parsing front matter YAML
# ---------------------------------------------------------------------------

def parse_frontmatter(text: str) -> tuple[dict, str]:
    """
    Ho separato il parsing del front matter dal corpo del file in modo
    da poter estrarre i metadati (title, layout, ...) indipendentemente
    dal contenuto markdown sottostante.
    Utilizzo un'espressione regolare per trovare il blocco --- ... --- iniziale,
    poi passo il contenuto interno a yaml.safe_load per evitare esecuzione
    arbitraria di codice (sicurezza: mai yaml.load senza Loader).
    """
    match = re.match(r'^---[ \t]*\r?\n(.*?)\r?\n---[ \t]*\r?\n', text, re.DOTALL)
    if not match:
        return {}, text
    try:
        fm = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        fm = {}
    body = text[match.end():]
    return fm, body


def extract_code_blocks(body: str) -> List[Tuple[str, str]]:
    """
    Estrae tutti i blocchi di codice markdown per i linguaggi:
    - java
    - sql
    - javascript

    Restituisce una lista di tuple (linguaggio, contenuto).
    Se non trova nulla, restituisce una lista vuota.
    """
    pattern = r'```(java|sql|javascript)[ \t]*\r?\n(.*?)```'
    matches = re.findall(pattern, body, re.DOTALL)

    # Ripulisce i contenuti rimuovendo newline finali inutili
    return [(lang, code.rstrip('\n')) for lang, code in matches]

# ---------------------------------------------------------------------------
# Suddivisione in slide rispettando le righe visive
# ---------------------------------------------------------------------------

def visual_line_count(line: str, chars_per_line: int) -> int:
    """
    Calcolo quante righe visive occupa una singola riga di codice dopo il wrap.
    Una riga vuota conta comunque 1 (occupa spazio verticale nel pre).
    Ho usato math.ceil invece di divisione intera per non sottostimare mai
    le righe lunghe che vanno esattamente a capo sul limite.
    """
    if chars_per_line <= 0:
        return 1
    raw = len(line)
    if raw == 0:
        return 1
    return math.ceil(raw / chars_per_line)


def split_code_into_slides(
    code_lines: list[str],
    lines_per_slide: int,
    chars_per_line: int,
    first_slide_reserved: int = 0,
) -> list[list[str]]:
    """
    Distribuisce le righe di codice in gruppi rispettando il budget di righe
    visive per slide.

    first_slide_reserved: righe visive già "consumate" dalla prima slide
    (es. dal blocco titolo). La prima slide parte con un budget ridotto.

    Strategia: scorro le righe e accumulo finché il contatore visivo non
    supera il budget; a quel punto chiudo la slide e ne apro una nuova.
    """
    slides: list[list[str]] = []
    current: list[str] = []
    visual_count = 0
    # Ho ridotto il budget della prima slide per il blocco titolo
    budget = lines_per_slide - first_slide_reserved

    for line in code_lines:
        v = visual_line_count(line, chars_per_line)
        if visual_count + v > budget and current:
            slides.append(current)
            current = [line]
            visual_count = v
            # Dalla seconda slide in poi il budget è pieno
            budget = lines_per_slide
        else:
            current.append(line)
            visual_count += v

    if current:
        slides.append(current)

    return slides

# ---------------------------------------------------------------------------
# Syntax highlighting Java (regex su testo già HTML-escaped)
# ---------------------------------------------------------------------------

# Ho costruito queste regex operando sull'HTML già escaped per sicurezza:
# prima eseguo l'escape, poi inserisco i tag <span>.
# L'ordine delle sostituzioni è importante: i commenti e le stringhe
# devono essere processati prima delle keyword per non colorare
# keyword dentro stringhe o commenti.

_KW = (
    r'\b(abstract|assert|boolean|break|byte|case|catch|char|class|const|'
    r'continue|default|do|double|else|enum|extends|final|finally|float|for|'
    r'goto|if|implements|import|instanceof|int|interface|long|native|new|'
    r'package|private|protected|public|record|return|sealed|short|static|'
    r'strictfp|super|switch|synchronized|this|throw|throws|transient|try|'
    r'var|void|volatile|while|true|false|null|yield|permits)\b'
)

def _html_escape(s: str) -> str:
    """Escape HTML minimale (solo i caratteri critici per <pre>)."""
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def highlight_java_line(raw_line: str) -> str:
    """
    Applica highlighting sintattico a una singola riga Java già escaped.
    Processo nell'ordine: commenti → stringhe/char → annotazioni → keyword → numeri.
    Non uso un vero parser: è un'approssimazione sufficiente per slide visuali.
    """
    escaped = _html_escape(raw_line)

    # Commenti di riga  //...
    escaped = re.sub(
        r'(//.*?)$',
        lambda m: f'<span style="color:{COLORS["comment"]}">{m.group(1)}</span>',
        escaped, flags=re.MULTILINE
    )
    # Commenti di blocco  /* ... */  (su riga singola, non multi-line per semplicità)
    escaped = re.sub(
        r'(/\*.*?\*/)',
        lambda m: f'<span style="color:{COLORS["comment"]}">{m.group(1)}</span>',
        escaped
    )
    # Stringhe  "..."  e char  '.'
    escaped = re.sub(
        r'(&quot;.*?&quot;|&#x27;.&#x27;|\'[^\']{0,1}\'|"[^"]*")',
        lambda m: f'<span style="color:{COLORS["string"]}">{m.group(1)}</span>',
        escaped
    )
    # Annotazioni  @Xxx
    escaped = re.sub(
        r'(@[\w]+)',
        lambda m: f'<span style="color:{COLORS["annotation"]}">{m.group(1)}</span>',
        escaped
    )
    # Keyword
    escaped = re.sub(
        _KW,
        lambda m: f'<span style="color:{COLORS["kw"]}">{m.group(1)}</span>',
        escaped
    )
    # Numeri (interi, float, hex, long)
    escaped = re.sub(
        r'\b(0[xX][0-9a-fA-F]+[lL]?|[0-9]+\.?[0-9]*[fFdDlL]?)\b',
        lambda m: f'<span style="color:{COLORS["number"]}">{m.group(1)}</span>',
        escaped
    )
    return escaped

# ---------------------------------------------------------------------------
# Generazione HTML della slide
# ---------------------------------------------------------------------------

def build_slide_html(
    lines: list[str],
    slide_num: int,
    total_slides: int,
    title: str,
    is_first: bool,
    is_last: bool,
    is_truncated: bool,
) -> str:
    """
    Costruisce l'HTML completo per una slide 1080x1080.
    Ho scelto un layout a colonna flex per posizionare:
      - (opzionale) blocco titolo in testa
      - blocco <pre> con il codice, che occupa lo spazio residuo
      - (opzionale) footer nell'ultima slide
      - contatore slide in basso a destra (position: absolute)
    Uso CSS custom properties per i colori in modo da facilitare future
    modifiche al tema senza toccare la logica Python.
    """
    c = COLORS

    # --- Header (solo prima slide) ---
    safe_title = _html_escape(title)
    header_html = (
        f'<div class="slide-title">{safe_title}</div>'
        if is_first else ''
    )

    # --- Footer (solo ultima slide) ---
    if is_last:
        label = f'continua su {CONTINUA_URL}' if is_truncated else CONTINUA_URL
        footer_html = f'<div class="slide-footer">{_html_escape(label)}</div>'
    else:
        footer_html = ''

    # --- Codice con highlighting riga per riga ---
    highlighted_lines = [highlight_java_line(line) for line in lines]
    code_html = '\n'.join(highlighted_lines)

    # --- Contatore ---
    counter_html = (
        f'<div class="slide-counter">{slide_num}/{total_slides}</div>'
    )

    lh_px = FONT_SIZE_PX * LINE_HEIGHT

    return f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

  html, body {{
    width:  {IMG_SIZE}px;
    height: {IMG_SIZE}px;
    background: {c['bg']};
    overflow: hidden;
  }}

  /* Layout principale a colonna; ho usato flex per distribuire
     automaticamente lo spazio tra header, codice e footer. */
  body {{
    display: flex;
    flex-direction: column;
    padding: {PADDING_V}px {PADDING_H}px;
    position: relative;
  }}

  .slide-title {{
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    font-size: 30px;
    font-weight: 700;
    color: {c['title_fg']};
    line-height: 1.3;
    margin-bottom: 22px;
    padding-bottom: 18px;
    border-bottom: 2px solid {c['border']};
    /* Ho preferito un font sans-serif per il titolo per creare
       contrasto visivo con il codice monospace sottostante */
    flex-shrink: 0;
  }}

  .code-block {{
    flex: 1;
    overflow: hidden;
    display: flex;
    align-items: flex-start;
  }}

  pre {{
    font-family: 'Courier New', Courier, monospace;
    font-size: {FONT_SIZE_PX}px;
    line-height: {LINE_HEIGHT};
    color: {c['code_fg']};
    /* pre-wrap: rispetto gli a-capo originali MA consento il wrap
       del browser per le righe molto lunghe, in modo che l'HTML
       rifletta esattamente il comportamento stimato in Python. */
    white-space: pre-wrap;
    word-break: break-all;
    tab-size: 2;
    width: 100%;
  }}

  .slide-footer {{
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    font-size: 21px;
    color: {c['footer_fg']};
    margin-top: 18px;
    padding-top: 14px;
    border-top: 1px solid {c['border']};
    text-align: center;
    flex-shrink: 0;
  }}

  /* Ho usato position: absolute per il contatore in modo che non
     interferisca con il layout flex del contenuto principale. */
  .slide-counter {{
    position: absolute;
    bottom: 18px;
    right: {PADDING_H}px;
    font-family: 'Courier New', Courier, monospace;
    font-size: 17px;
    color: {c['counter_fg']};
    letter-spacing: 0.05em;
  }}
</style>
</head>
<body>
  {header_html}
  <div class="code-block"><pre>{code_html}</pre></div>
  {footer_html}
  {counter_html}
</body>
</html>"""

# ---------------------------------------------------------------------------
# Pipeline principale per un singolo file markdown
# ---------------------------------------------------------------------------

def process_markdown(md_path: Path, page) -> None:
    """
    Gestisce l'intera pipeline per un file:
      1. Leggo e parso front matter
      2. Verifico layout: code
      3. Estraggo il blocco Java
      4. Suddivido in slide
      5. Renderizzo con Playwright (pagina già aperta, la riuso)
    Ho passato la page di Playwright come parametro per evitare di
    aprire/chiudere browser per ogni file: il costo di launch è alto.
    """
    text = md_path.read_text(encoding='utf-8')
    fm, body = parse_frontmatter(text)

    if fm.get('layout') != 'code':
        print(f"  [SKIP] layout != code → {md_path.name}")
        return

    title = fm.get('title', md_path.stem)
    blocks = extract_code_blocks(body)
    if not blocks:
        print(f"  [SKIP] nessun blocco di codice trovato → {md_path.name}")
        return

    # Concatena tutti i blocchi in ordine
    all_code = "\n\n".join(code for lang, code in blocks)
    code_lines = all_code.split('\n')

    # Ho stimato le righe visive riservate dal titolo nella prima slide:
    # il titolo occupa ~2 righe visive equivalenti (font più grande + margin).
    # Ho usato 3 come valore conservativo per non sforare il layout.
    FIRST_SLIDE_TITLE_ROWS = 3

    all_slides = split_code_into_slides(
        code_lines,
        lines_per_slide=LINES_PER_SLIDE,
        chars_per_line=CHARS_PER_LINE,
        first_slide_reserved=FIRST_SLIDE_TITLE_ROWS,
    )

    is_truncated = len(all_slides) > SLIDES_MAX
    slides = all_slides[:SLIDES_MAX]
    total_slides = len(slides)

    print(f"  Titolo   : {title}")
    print(f"  Slide    : {total_slides} (troncato: {is_truncated})")
    print(f"  Chars/riga stimati: {CHARS_PER_LINE}")

    out_dir = ARTICOLI_DIR / md_path.stem
    out_dir.mkdir(parents=True, exist_ok=True)

    for i, lines in enumerate(slides):
        html = build_slide_html(
            lines=lines,
            slide_num=i + 1,
            total_slides=total_slides,
            title=title,
            is_first=(i == 0),
            is_last=(i == total_slides - 1),
            is_truncated=is_truncated,
        )

        # Ho impostato set_content + wait_for_load_state per assicurarmi
        # che il DOM sia completamente renderizzato prima dello screenshot,
        # evitando artefatti di font non ancora caricati.
        page.set_content(html, wait_until='domcontentloaded')
        page.wait_for_timeout(80)  # piccola pausa per il rendering CSS

        out_path = out_dir / f"slide_{i + 1:02d}.png"
        page.screenshot(
            path=str(out_path),
            clip={"x": 0, "y": 0, "width": IMG_SIZE, "height": IMG_SIZE},
        )
        print(f"  [OK] {out_path}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    if not ARTICOLI_DIR.exists():
        print(f"[ERRORE] Cartella '{ARTICOLI_DIR}' non trovata. "
              f"Esegui lo script dalla root del progetto.")
        return

    md_files = sorted(ARTICOLI_DIR.glob("*.md"))
    if not md_files:
        print(f"[ERRORE] Nessun file .md trovato in {ARTICOLI_DIR}/")
        return

    print(f"Trovati {len(md_files)} file markdown in {ARTICOLI_DIR}/\n")
    print(f"Parametri: {IMG_SIZE}x{IMG_SIZE}px | font {FONT_SIZE_PX}px | "
          f"{LINES_PER_SLIDE} righe/slide | max {SLIDES_MAX} slide | "
          f"~{CHARS_PER_LINE} char/riga\n")

    # Ho aperto il browser una sola volta prima del loop per ottimizzare
    # i tempi: il launch di Chromium è la parte più lenta (~1-2s).
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        # Ho impostato le dimensioni del viewport esattamente a 1080x1080
        # in modo che page.screenshot() catturi esattamente la slide senza
        # dover ritagliare o scalare.
        page = browser.new_page(
            viewport={"width": IMG_SIZE, "height": IMG_SIZE},
            device_scale_factor=1,
        )

        for md_path in md_files:
            print(f"→ {md_path.name}")
            try:
                process_markdown(md_path, page)
            except Exception as exc:
                print(f"  [ERRORE] {exc}")
            print()

        browser.close()

    print("Completato.")


if __name__ == "__main__":
    main()