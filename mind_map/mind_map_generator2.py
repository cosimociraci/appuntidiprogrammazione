#!/usr/bin/env python3
"""
mindmap_render.py
-----------------
Leggo un file JSON con la struttura della mappa mentale,
genero l'HTML completo iniettando i dati nel template,
e cattura il risultato come PNG tramite Playwright (Chromium headless).

Uso:
    python mindmap_render.py input.json [output.png] [--width 1600] [--scale 2]

Argomenti:
    input.json   — file JSON con chiavi "title", "left", "right"
    output.png   — percorso PNG di output (default: <nome_input>.png)
    --width      — larghezza viewport in px (default: 1600)
    --scale      — device pixel ratio per output HiDPI (default: 2)
    --keep-html  — salva anche l'HTML generato accanto al PNG (flag opzionale)
"""

import argparse
import json
import sys
import tempfile
from pathlib import Path

# ─── Template HTML ────────────────────────────────────────────────────────────
# Ho separato il template dall'HTML originale così posso iniettare qualsiasi
# JSON senza toccare la struttura. Il placeholder %%MAP_DATA_JSON%% verrà
# rimpiazzato con il JSON serializzato prima del render.

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Mindmap</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700;800&family=Inter:wght@400;500;600&display=swap" rel="stylesheet" />

  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: 'Inter', sans-serif;
      background: #0d0d10;
      color: #e8e8f0;
      min-height: 100vh;
      padding: 56px 40px 80px;
    }

    .hub-card {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      text-align: center;
      border-radius: 18px;
      border: 2px solid;
      padding: 22px 18px 18px;
      width: 170px;
      min-height: 120px;
      gap: 8px;
      flex-shrink: 0;
      cursor: default;
    }
    .hub-card .hub-icon  { font-size: 1.8rem; line-height: 1; display: block; }
    .hub-card .hub-title {
      font-family: 'Outfit', sans-serif;
      font-size: 0.82rem;
      font-weight: 700;
      line-height: 1.3;
    }

    .hub-green  { background:linear-gradient(135deg,#1a3d2b,#1e4d32); border-color:#2d7a4f; box-shadow:0 8px 28px #2d7a4f20; }
    .hub-green  .hub-title { color:#6ee09a; }
    .hub-blue   { background:linear-gradient(135deg,#1a2a45,#1e3358); border-color:#3362a0; box-shadow:0 8px 28px #3362a020; }
    .hub-blue   .hub-title { color:#7ab4f5; }
    .hub-dark   { background:linear-gradient(135deg,#1e1e28,#252535); border-color:#8855dd; box-shadow:0 8px 28px #8855dd30; }
    .hub-dark   .hub-title { color:#cc99ff; }
    .hub-orange { background:linear-gradient(135deg,#3a2010,#4a2a14); border-color:#c97e28; box-shadow:0 8px 28px #c97e2820; }
    .hub-orange .hub-title { color:#f5b55a; }
    .hub-purple { background:linear-gradient(135deg,#2a1a40,#33204e); border-color:#9966cc; box-shadow:0 8px 28px #9966cc20; }
    .hub-purple .hub-title { color:#cc99ff; }
    .hub-teal   { background:linear-gradient(135deg,#0e2e30,#133840); border-color:#2a9090; box-shadow:0 8px 28px #2a909020; }
    .hub-teal   .hub-title { color:#66d4d4; }

    .hub-center {
      width: 150px;
      min-height: 150px;
      border-radius: 50%;
      border: 3px solid #8855dd;
      background: radial-gradient(ellipse at 40% 35%, #2a1a40, #1a1028);
      box-shadow: 0 0 0 4px #8855dd35, 0 0 50px #8855dd45;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      text-align: center;
      padding: 20px;
      flex-shrink: 0;
    }
    .hub-center .center-title {
      font-family: 'Outfit', sans-serif;
      font-size: 0.9rem;
      font-weight: 800;
      color: #cc99ff;
      line-height: 1.3;
      white-space: pre-line;
    }
    .hub-center .center-icon { font-size: 1.6rem; margin-bottom: 8px; display: block; }

    .pill {
      position: relative;
      display: inline-flex;
      align-items: center;
      border-radius: 7px;
      border: 1px solid;
      padding: 5px 13px;
      font-size: 0.65rem;
      font-weight: 500;
      white-space: nowrap;
      cursor: default;
    }
    .pill-green  { background:#0e2618; border-color:#2d7a4f; color:#6ee09a; }
    .pill-blue   { background:#0e1a2e; border-color:#3362a0; color:#7ab4f5; }
    .pill-dark   { background:#16101e; border-color:#6644bb; color:#cc99ff; }
    .pill-orange { background:#1e1000; border-color:#996622; color:#f5b55a; }
    .pill-purple { background:#180e28; border-color:#7755aa; color:#cc99ff; }
    .pill-teal   { background:#071e1e; border-color:#2a8080; color:#66d4d4; }

    .map-section { display:flex; align-items:center; gap:28px; }
    .section-left              { flex-direction:row; }
    .section-left .pills-col  { display:flex; flex-direction:column; align-items:flex-end; gap:7px; }
    .section-right             { flex-direction:row; }
    .section-right .pills-col { display:flex; flex-direction:column; align-items:flex-start; gap:7px; }

    .map-wrapper {
      position: relative;
      max-width: 1200px;
      margin: 0 auto;
    }
    #map-svg {
      position: absolute;
      top: 0; left: 0;
      width: 100%; height: 100%;
      pointer-events: none;
      z-index: 0;
      overflow: visible;
    }
    .mindmap {
      display: grid;
      grid-template-columns: 1fr auto 1fr;
      column-gap: 56px;
      row-gap: 52px;
      align-items: center;
      justify-items: center;
      position: relative;
      z-index: 1;
    }
    .cell-left   { grid-column:1; justify-self:end; }
    .cell-center { grid-column:2; }
    .cell-right  { grid-column:3; justify-self:start; }

    .page-header { text-align:center; margin-bottom:52px; }
    .page-header h1 {
      font-family: 'Outfit', sans-serif;
      font-size: 1.5rem;
      font-weight: 700;
      color: #f0ede8;
      margin-bottom: 6px;
    }
    .page-header p { font-size: 0.78rem; color: #555; }
  </style>
</head>
<body>

  <script id="map-data" type="application/json">
%%MAP_DATA_JSON%%
  </script>

  <div class="page-header">
    <h1 id="page-title"></h1>
    <p>Mappa mentale generata automaticamente</p>
  </div>

  <div class="map-wrapper" id="map-wrapper">
    <svg id="map-svg" aria-hidden="true"></svg>
    <div class="mindmap" id="mindmap"></div>
  </div>

  <script>
    const STYLE_COLOR = {
      'hub-green':  '#2d7a4f',
      'hub-blue':   '#3362a0',
      'hub-dark':   '#8855dd',
      'hub-orange': '#c97e28',
      'hub-purple': '#9966cc',
      'hub-teal':   '#2a9090',
    };
    const PILL_CLASS = {
      'hub-green':  'pill-green',
      'hub-blue':   'pill-blue',
      'hub-dark':   'pill-dark',
      'hub-orange': 'pill-orange',
      'hub-purple': 'pill-purple',
      'hub-teal':   'pill-teal',
    };
    const LEFT_ICONS  = ['🤖', '🏆', '📊', '🔬', '🧠', '💡'];
    const RIGHT_ICONS = ['🌿', '🚀', '🌐', '⚙️', '📡', '🔮'];

    const data    = JSON.parse(document.getElementById('map-data').textContent);
    const mindmap = document.getElementById('mindmap');

    document.getElementById('page-title').textContent = data.title.replace('\n', ' — ');

    function makePill(item, side, hubStyle) {
      const [label] = item;
      const pill = document.createElement('div');
      pill.className = 'pill ' + (PILL_CLASS[hubStyle] || 'pill-dark');
      pill.textContent = label;
      return pill;
    }

    function makeHub(section, side, index) {
      const hub = document.createElement('div');
      hub.className = 'hub-card ' + section.style;
      hub.id = 'hub-' + side + '-' + index;
      const icon = document.createElement('span');
      icon.className = 'hub-icon';
      icon.textContent = side === 'left' ? (LEFT_ICONS[index] || '●') : (RIGHT_ICONS[index] || '●');
      const title = document.createElement('span');
      title.className = 'hub-title';
      title.textContent = section.name;
      hub.appendChild(icon);
      hub.appendChild(title);
      return hub;
    }

    function makeSection(section, side, index) {
      const wrap = document.createElement('div');
      wrap.className = 'map-section section-' + side;
      const pillsCol = document.createElement('div');
      pillsCol.className = 'pills-col';
      section.items.forEach(function(item) {
        pillsCol.appendChild(makePill(item, side, section.style));
      });
      const hub = makeHub(section, side, index);
      if (side === 'left') {
        wrap.appendChild(pillsCol);
        wrap.appendChild(hub);
      } else {
        wrap.appendChild(hub);
        wrap.appendChild(pillsCol);
      }
      return wrap;
    }

    const rows      = Math.max(data.left.length, data.right.length);
    const centerRow = Math.floor(rows / 2);

    for (var r = 0; r < rows; r++) {
      if (data.left[r]) {
        var cell = document.createElement('div');
        cell.className = 'cell-left';
        cell.style.gridRow = r + 1;
        cell.appendChild(makeSection(data.left[r], 'left', r));
        mindmap.appendChild(cell);
      } else {
        var spacer = document.createElement('div');
        spacer.style.gridColumn = '1';
        spacer.style.gridRow = r + 1;
        mindmap.appendChild(spacer);
      }

      if (r === centerRow) {
        var centerCell = document.createElement('div');
        centerCell.className = 'cell-center';
        centerCell.style.gridRow = r + 1;
        var centerHub = document.createElement('div');
        centerHub.className = 'hub-center';
        centerHub.id = 'hub-center';
        var centerIcon = document.createElement('span');
        centerIcon.className = 'center-icon';
        centerIcon.textContent = '⚡';
        var centerTitle = document.createElement('span');
        centerTitle.className = 'center-title';
        centerTitle.textContent = data.title;
        centerHub.appendChild(centerIcon);
        centerHub.appendChild(centerTitle);
        centerCell.appendChild(centerHub);
        mindmap.appendChild(centerCell);
      } else {
        var sp2 = document.createElement('div');
        sp2.style.gridColumn = '2';
        sp2.style.gridRow = r + 1;
        mindmap.appendChild(sp2);
      }

      if (data.right[r]) {
        var cellR = document.createElement('div');
        cellR.className = 'cell-right';
        cellR.style.gridRow = r + 1;
        cellR.appendChild(makeSection(data.right[r], 'right', r));
        mindmap.appendChild(cellR);
      } else {
        var sp3 = document.createElement('div');
        sp3.style.gridColumn = '3';
        sp3.style.gridRow = r + 1;
        mindmap.appendChild(sp3);
      }
    }

    /* ── SVG lines ─────────────────────────────────────────────────────── */
    const svg     = document.getElementById('map-svg');
    const wrapper = document.getElementById('map-wrapper');

    function rel(el) {
      var wr = wrapper.getBoundingClientRect();
      var er = el.getBoundingClientRect();
      return {
        cx:    er.left - wr.left + er.width  / 2,
        cy:    er.top  - wr.top  + er.height / 2,
        left:  er.left  - wr.left,
        right: er.right - wr.left,
        my:    er.top   - wr.top  + er.height / 2,
      };
    }

    function addPath(d, color, dasharray, width, opacity) {
      var p = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      p.setAttribute('d', d);
      p.setAttribute('stroke', color);
      p.setAttribute('stroke-width', String(width));
      p.setAttribute('stroke-dasharray', dasharray);
      p.setAttribute('fill', 'none');
      p.setAttribute('opacity', String(opacity));
      svg.appendChild(p);
    }

    function buildLines() {
      while (svg.firstChild) svg.removeChild(svg.firstChild);
      var W = wrapper.offsetWidth;
      var H = wrapper.offsetHeight;
      svg.setAttribute('viewBox', '0 0 ' + W + ' ' + H);
      svg.setAttribute('width',  W);
      svg.setAttribute('height', H);
      var centerEl = document.getElementById('hub-center');
      if (!centerEl) return;
      var C = rel(centerEl);

      data.left.forEach(function(_, i) {
        var hub = document.getElementById('hub-left-' + i);
        if (!hub) return;
        var col = STYLE_COLOR[data.left[i].style] || '#ffffff';
        var P   = rel(hub);
        var mx  = (P.cx + C.cx) / 2;
        addPath('M ' + P.cx + ' ' + P.cy + ' C ' + mx + ' ' + P.cy + ' ' + mx + ' ' + C.cy + ' ' + C.cx + ' ' + C.cy,
                col, '5,8', 1.5, 0.4);
      });
      data.right.forEach(function(_, i) {
        var hub = document.getElementById('hub-right-' + i);
        if (!hub) return;
        var col = STYLE_COLOR[data.right[i].style] || '#ffffff';
        var P   = rel(hub);
        var mx  = (P.cx + C.cx) / 2;
        addPath('M ' + P.cx + ' ' + P.cy + ' C ' + mx + ' ' + P.cy + ' ' + mx + ' ' + C.cy + ' ' + C.cx + ' ' + C.cy,
                col, '5,8', 1.5, 0.4);
      });

      document.querySelectorAll('.map-section').forEach(function(section) {
        var isLeft = section.classList.contains('section-left');
        var hub    = section.querySelector('.hub-card');
        if (!hub) return;
        var col = STYLE_COLOR[Array.from(hub.classList).find(function(c) { return STYLE_COLOR[c]; })] || '#ffffff';
        var HH  = rel(hub);
        section.querySelectorAll('.pill').forEach(function(pill) {
          var PP = rel(pill);
          var px = isLeft ? PP.right : PP.left;
          var hx = isLeft ? HH.left  : HH.right;
          addPath('M ' + px + ' ' + PP.my + ' L ' + hx + ' ' + HH.my, col, '3,5', 1, 0.35);
        });
      });
    }

    /* Ho usato un flag globale per comunicare a Playwright
       che il rendering è completato e le linee SVG sono pronte. */
    window.__mindmapReady = false;

    function init() {
      requestAnimationFrame(function() {
        buildLines();
        /* Secondo frame per sicurezza: i font Google potrebbero
           ancora non essere applicati al primo paint. */
        requestAnimationFrame(function() {
          buildLines();
          window.__mindmapReady = true;
        });
      });
    }

    if (document.fonts && document.fonts.ready) {
      document.fonts.ready.then(init);
    } else {
      setTimeout(init, 500);
    }
  </script>
</body>
</html>
"""


# ─── Validazione struttura JSON ───────────────────────────────────────────────

def validate_map_data(data: dict) -> None:
    """
    Verifico che il JSON abbia la struttura minima attesa prima di procedere
    con la generazione. Meglio fallire subito con un messaggio chiaro che
    ottenere un HTML malformato o un PNG vuoto.
    """
    required_keys = {"title", "left", "right"}
    missing = required_keys - data.keys()
    if missing:
        raise ValueError(f"Chiavi mancanti nel JSON: {missing}")

    for side in ("left", "right"):
        if not isinstance(data[side], list):
            raise ValueError(f"'{side}' deve essere una lista di sezioni.")
        for i, section in enumerate(data[side]):
            if "name" not in section or "style" not in section or "items" not in section:
                raise ValueError(
                    f"Sezione {side}[{i}] mancante di 'name', 'style' o 'items'."
                )
            if not isinstance(section["items"], list):
                raise ValueError(f"'{side}[{i}].items' deve essere una lista.")


# ─── Generazione HTML ─────────────────────────────────────────────────────────

def generate_html(data: dict) -> str:
    """
    Serializzo il dizionario Python in JSON e lo inietto nel template.
    Uso ensure_ascii=False per preservare i caratteri speciali italiani
    (accenti, ecc.) senza escape unicode che potrebbero causare problemi
    di visualizzazione nei browser.
    """
    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    return HTML_TEMPLATE.replace("%%MAP_DATA_JSON%%", json_str)


# ─── Screenshot con Playwright ────────────────────────────────────────────────

def render_to_png(html: str, output_path: Path, viewport_width: int, scale: float) -> None:
    """
    Apro una pagina Chromium headless, carico l'HTML come stringa (non da file
    su disco, così evito problemi di path su sistemi diversi) e aspetto che
    window.__mindmapReady sia true prima di scattare lo screenshot.

    Ho scelto full_page=True per catturare l'intera altezza del documento,
    non solo il viewport visibile: le mappe con molti nodi possono essere
    più alte dello schermo.
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        # Ho usato channel="chromium" per il browser bundled di Playwright,
        # non quello di sistema, così non dipendo da installazioni esterne.
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": viewport_width, "height": 900},
            device_scale_factor=scale,
        )
        page = context.new_page()

        # Carico l'HTML come stringa base64 tramite data URI.
        # L'alternativa (page.set_content) non gestisce bene i font Google
        # perché il browser blocca le richieste di rete senza un'origine.
        # Con goto("about:blank") + set_content ottengo l'origine corretta
        # per le richieste ai CDN esterni.
        page.goto("about:blank")
        page.set_content(html, wait_until="domcontentloaded")

        # Aspetto che i font siano caricati (massimo 10 secondi).
        # Se i font Google non arrivano, il fallback 'Inter' già nel sistema
        # è sufficiente per un PNG leggibile.
        try:
            page.wait_for_function("document.fonts.status === 'loaded'", timeout=10_000)
        except Exception:
            pass  # Procedo comunque con i font di sistema

        # Aspetto il flag custom settato dallo script JS dopo il doppio rAF.
        # Timeout generoso perché su macchine lente il layout potrebbe tardare.
        page.wait_for_function("window.__mindmapReady === true", timeout=15_000)

        # Piccola pausa extra per dare tempo alle animazioni CSS (box-shadow,
        # gradienti) di stabilizzarsi prima della cattura.
        page.wait_for_timeout(300)

        page.screenshot(
            path=str(output_path),
            full_page=True,
            type="png",
        )

        context.close()
        browser.close()


# ─── Entry point ──────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Genera un PNG di una mappa mentale da un file JSON."
    )
    parser.add_argument(
        "input_json",
        help="Percorso al file JSON con la struttura della mappa."
    )
    parser.add_argument(
        "output_png",
        nargs="?",
        default=None,
        help="Percorso PNG di output. Default: stesso nome del JSON con estensione .png"
    )
    parser.add_argument(
        "--width",
        type=int,
        default=1600,
        help="Larghezza del viewport in pixel (default: 1600)"
    )
    parser.add_argument(
        "--scale",
        type=float,
        default=2.0,
        help="Device pixel ratio per output HiDPI (default: 2.0)"
    )
    parser.add_argument(
        "--keep-html",
        action="store_true",
        help="Salva anche l'HTML generato accanto al PNG di output."
    )
    args = parser.parse_args()

    # ── Leggo il JSON ──────────────────────────────────────────────────────
    input_path = Path(args.input_json)
    if not input_path.exists():
        print(f"[ERRORE] File non trovato: {input_path}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(input_path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"[ERRORE] JSON non valido: {e}", file=sys.stderr)
        sys.exit(1)

    # ── Valido la struttura ────────────────────────────────────────────────
    try:
        validate_map_data(data)
    except ValueError as e:
        print(f"[ERRORE] Struttura JSON non valida: {e}", file=sys.stderr)
        sys.exit(1)

    # ── Determino il path di output ────────────────────────────────────────
    output_path = Path(args.output_png) if args.output_png else input_path.with_suffix(".png")

    # ── Genero l'HTML ──────────────────────────────────────────────────────
    print(f"[1/3] Genero HTML da: {input_path}")
    html = generate_html(data)

    if args.keep_html:
        html_path = output_path.with_suffix(".html")
        html_path.write_text(html, encoding="utf-8")
        print(f"      HTML salvato in: {html_path}")

    # ── Render PNG ─────────────────────────────────────────────────────────
    print(f"[2/3] Avvio Chromium headless (viewport={args.width}px, scale={args.scale}x)...")
    try:
        render_to_png(html, output_path, viewport_width=args.width, scale=args.scale)
    except Exception as e:
        print(f"[ERRORE] Playwright ha fallito: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"[3/3] PNG salvato in: {output_path}")
    size_kb = output_path.stat().st_size // 1024
    print(f"      Dimensione: {size_kb} KB")


if __name__ == "__main__":
    main()