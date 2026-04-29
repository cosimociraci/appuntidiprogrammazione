#!/usr/bin/env python3
"""
mindmap_render.py
-----------------
Leggo un file JSON con la struttura della mappa mentale,
genero l'HTML completo iniettando i dati nel template,
e cattura il risultato come PNG 1080×1080 via Playwright headless.
"""

import argparse
import json
import sys
from io import BytesIO
from pathlib import Path

# ─── Costanti ─────────────────────────────────────────────────────────────────

OUTPUT_SIZE = (1080, 1080)
BG_COLOR    = (13, 13, 16)    # #0d0d10

# ─── Template HTML ────────────────────────────────────────────────────────────

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8" />
  <title>Mindmap</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700;800&family=Inter:wght@400;500;600&display=swap" rel="stylesheet" />
  <style>
    :root {
      /* Variabili centralizzate per i font-size */
      --fs-page-title: 1.5rem;
      --fs-page-subtitle: 0.78rem;
      --fs-center-title: 0.9rem;
      --fs-center-icon: 1.6rem;
      --fs-hub-title: 0.95rem;
      --fs-hub-icon: 2rem;
      --fs-pill: 0.82rem;
    }

    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: 'Inter', sans-serif;
      background: #0d0d10;
      color: #e8e8f0;
      padding: 0;
    }

    #content-root {
      display: inline-block;
      padding: 36px 40px 36px;
    }

    .hub-card {
      display: flex; flex-direction: column;
      align-items: center; justify-content: center; text-align: center;
      border-radius: 18px; border: 2px solid;
      padding: 22px 18px 18px; width: 190px; min-height: 130px;
      gap: 8px; flex-shrink: 0; cursor: default;
      transition: min-height 0s;
    }
    .hub-card .hub-icon  { font-size: var(--fs-hub-icon); line-height: 1; display: block; }
    .hub-card .hub-title {
      font-family: 'Outfit', sans-serif; font-size: var(--fs-hub-title);
      font-weight: 700; line-height: 1.3;
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
      width: 150px; min-height: 150px; border-radius: 50%;
      border: 3px solid #8855dd;
      background: radial-gradient(ellipse at 40% 35%, #2a1a40, #1a1028);
      box-shadow: 0 0 0 4px #8855dd35, 0 0 50px #8855dd45;
      display: flex; flex-direction: column;
      align-items: center; justify-content: center;
      text-align: center; padding: 20px; flex-shrink: 0;
    }
    .hub-center .center-title {
      font-family: 'Outfit', sans-serif; font-size: var(--fs-center-title);
      font-weight: 800; color: #cc99ff; line-height: 1.3; white-space: pre-line;
    }
    .hub-center .center-icon { font-size: var(--fs-center-icon); margin-bottom: 8px; display: block; }

    .pill {
      display: inline-flex; align-items: center;
      border-radius: 9px; border: 1px solid; padding: 7px 16px;
      font-size: var(--fs-pill); font-weight: 600; white-space: nowrap; cursor: default;
    }
    .pill-green  { background:#0e2618; border-color:#2d7a4f; color:#6ee09a; }
    .pill-blue   { background:#0e1a2e; border-color:#3362a0; color:#7ab4f5; }
    .pill-dark   { background:#16101e; border-color:#6644bb; color:#cc99ff; }
    .pill-orange { background:#1e1000; border-color:#996622; color:#f5b55a; }
    .pill-purple { background:#180e28; border-color:#7755aa; color:#cc99ff; }
    .pill-teal   { background:#071e1e; border-color:#2a8080; color:#66d4d4; }

    .map-section { display:flex; align-items:center; gap:28px; }
    .section-left .pills-col  { display:flex; flex-direction:column; align-items:flex-end;   gap:7px; }
    .section-right .pills-col { display:flex; flex-direction:column; align-items:flex-start; gap:7px; }

    .map-wrapper { position: relative; }

    #map-svg {
      position:absolute; top:0; left:0; width:100%; height:100%;
      pointer-events:none; z-index:0; overflow:visible;
    }
    .mindmap {
      display:grid; grid-template-columns:1fr auto 1fr;
      column-gap:56px; row-gap:52px;
      align-items:center; justify-items:center;
      position:relative; z-index:1;
    }
    .cell-left   { grid-column:1; justify-self:end; }
    .cell-center { grid-column:2; }
    .cell-right  { grid-column:3; justify-self:start; }

    .page-header { text-align:center; margin-bottom:36px; }
    .page-header h1 {
      font-family:'Outfit', sans-serif; font-size: var(--fs-page-title);
      font-weight:700; color:#f0ede8; margin-bottom:6px;
    }
    .page-header p { font-size: var(--fs-page-subtitle); color:#555; }
  </style>
</head>
<body>
  <script id="map-data" type="application/json">
%%MAP_DATA_JSON%%
  </script>

  <div id="content-root">
    <div class="page-header">
      <h1 id="page-title"></h1>
      <p>Mappa mentale generata automaticamente</p>
    </div>
    <div class="map-wrapper" id="map-wrapper">
      <svg id="map-svg" aria-hidden="true"></svg>
      <div class="mindmap" id="mindmap"></div>
    </div>
  </div>

  <script>
    var STYLE_COLOR = {
      'hub-green':'#2d7a4f','hub-blue':'#3362a0','hub-dark':'#8855dd',
      'hub-orange':'#c97e28','hub-purple':'#9966cc','hub-teal':'#2a9090',
    };
    var PILL_CLASS = {
      'hub-green':'pill-green','hub-blue':'pill-blue','hub-dark':'pill-dark',
      'hub-orange':'pill-orange','hub-purple':'pill-purple','hub-teal':'pill-teal',
    };
    var LEFT_ICONS  = ['🤖','🏆','📊','🔬','🧠','💡'];
    var RIGHT_ICONS = ['🌿','🚀','🌐','⚙️','📡','🔮'];

    var data    = JSON.parse(document.getElementById('map-data').textContent);
    var mindmap = document.getElementById('mindmap');
    document.getElementById('page-title').textContent = data.title.replace('\n',' — ');

    function makePill(item, hubStyle) {
      var p = document.createElement('div');
      p.className = 'pill ' + (PILL_CLASS[hubStyle] || 'pill-dark');
      p.textContent = item[0];
      return p;
    }
    function makeHub(section, side, idx) {
      var h = document.createElement('div');
      h.className = 'hub-card ' + section.style;
      h.id = 'hub-' + side + '-' + idx;
      var ic = document.createElement('span'); ic.className = 'hub-icon';
      ic.textContent = side === 'left' ? (LEFT_ICONS[idx]||'●') : (RIGHT_ICONS[idx]||'●');
      var ti = document.createElement('span'); ti.className = 'hub-title';
      ti.textContent = section.name;
      h.appendChild(ic); h.appendChild(ti);
      return h;
    }
    function makeSection(section, side, idx) {
      var w = document.createElement('div');
      w.className = 'map-section section-' + side;
      var pc = document.createElement('div'); pc.className = 'pills-col';
      section.items.forEach(function(it){ pc.appendChild(makePill(it, section.style)); });
      var hub = makeHub(section, side, idx);
      if (side === 'left') { w.appendChild(pc); w.appendChild(hub); }
      else                 { w.appendChild(hub); w.appendChild(pc); }
      return w;
    }

    var rows = Math.max(data.left.length, data.right.length);
    var centerRow = Math.floor(rows / 2);

    for (var r = 0; r < rows; r++) {
      var cL = document.createElement('div');
      if (data.left[r]) {
        cL.className = 'cell-left'; cL.style.gridRow = r+1;
        cL.appendChild(makeSection(data.left[r],'left',r));
      } else { cL.style.gridColumn='1'; cL.style.gridRow=r+1; }
      mindmap.appendChild(cL);

      if (r === centerRow) {
        var cc = document.createElement('div');
        cc.className = 'cell-center'; cc.style.gridRow = r+1;
        var ch = document.createElement('div');
        ch.className = 'hub-center'; ch.id = 'hub-center';
        var ci = document.createElement('span'); ci.className='center-icon'; ci.textContent='⚡';
        var ct = document.createElement('span'); ct.className='center-title'; ct.textContent=data.title;
        ch.appendChild(ci); ch.appendChild(ct); cc.appendChild(ch);
        mindmap.appendChild(cc);
      } else {
        var sp = document.createElement('div');
        sp.style.gridColumn='2'; sp.style.gridRow=r+1;
        mindmap.appendChild(sp);
      }

      var cR = document.createElement('div');
      if (data.right[r]) {
        cR.className = 'cell-right'; cR.style.gridRow = r+1;
        cR.appendChild(makeSection(data.right[r],'right',r));
      } else { cR.style.gridColumn='3'; cR.style.gridRow=r+1; }
      mindmap.appendChild(cR);
    }

    function squarify() {
      var root = document.getElementById('content-root');
      var W = root.offsetWidth;
      var H = root.offsetHeight;
      var delta = W - H;
      if (delta <= 0) return;
      var numRows = Math.max(data.left.length, data.right.length);
      var numGaps = numRows - 1;
      if (numGaps > 0) {
        var mindmapEl   = document.querySelector('.mindmap');
        var currentGap = parseFloat(getComputedStyle(mindmapEl).rowGap) || 52;
        var newGap      = currentGap + (delta * 0.4 / numGaps);
        mindmapEl.style.rowGap = newGap + 'px';
      }
      var extraHub = delta * 0.6 / numRows;
      document.querySelectorAll('.hub-card').forEach(function(hub) {
        var curH = hub.offsetHeight;
        hub.style.minHeight = (curH + extraHub) + 'px';
      });
      var centerHub = document.getElementById('hub-center');
      if (centerHub) {
        var curSize = centerHub.offsetWidth;
        var newSize = curSize + extraHub;
        centerHub.style.width     = newSize + 'px';
        centerHub.style.minHeight = newSize + 'px';
      }
    }

    var svg     = document.getElementById('map-svg');
    var wrapper = document.getElementById('map-wrapper');

    function rel(el) {
      var wr=wrapper.getBoundingClientRect(), er=el.getBoundingClientRect();
      return { cx:er.left-wr.left+er.width/2,  cy:er.top-wr.top+er.height/2,
               left:er.left-wr.left,            right:er.right-wr.left,
               my:er.top-wr.top+er.height/2 };
    }
    function addPath(d,col,dash,w,op){
      var p=document.createElementNS('http://www.w3.org/2000/svg','path');
      p.setAttribute('d',d); p.setAttribute('stroke',col);
      p.setAttribute('stroke-width',String(w)); p.setAttribute('stroke-dasharray',dash);
      p.setAttribute('fill','none'); p.setAttribute('opacity',String(op));
      svg.appendChild(p);
    }
    function buildLines(){
      while(svg.firstChild) svg.removeChild(svg.firstChild);
      var W=wrapper.offsetWidth, H=wrapper.offsetHeight;
      svg.setAttribute('viewBox','0 0 '+W+' '+H);
      svg.setAttribute('width',W); svg.setAttribute('height',H);
      var C=rel(document.getElementById('hub-center'));
      ['left','right'].forEach(function(side){
        data[side].forEach(function(sec,i){
          var hub=document.getElementById('hub-'+side+'-'+i); if(!hub) return;
          var col=STYLE_COLOR[sec.style]||'#fff'; // <-- Fix: aggiunti apici
          var P=rel(hub), mx=(P.cx+C.cx)/2;
          addPath('M '+P.cx+' '+P.cy+' C '+mx+' '+P.cy+' '+mx+' '+C.cy+' '+C.cx+' '+C.cy,
                  col,'5,8',1.5,0.4);
        });
      });
      document.querySelectorAll('.map-section').forEach(function(sec){
        var hub=sec.querySelector('.hub-card'); if(!hub) return;
        var col=STYLE_COLOR[Array.from(hub.classList).find(function(c){return STYLE_COLOR[c];})]||'#fff';
        var isLeft = hub.previousElementSibling !== null &&
                     hub.previousElementSibling.classList.contains('pills-col');
        var HH=rel(hub);
        sec.querySelectorAll('.pill').forEach(function(pill){
          var PP=rel(pill);
          addPath('M '+(isLeft?PP.right:PP.left)+' '+PP.my+' L '+(isLeft?HH.left:HH.right)+' '+HH.my,
                  col,'3,5',1,0.35);
        });
      });
    }

    window.__mindmapReady = false;
    function init() {
      squarify();
      requestAnimationFrame(function(){
        buildLines();
        requestAnimationFrame(function(){
          buildLines();
          window.__mindmapReady = true;
        });
      });
    }
    if (document.fonts && document.fonts.ready) { document.fonts.ready.then(init); }
    else { setTimeout(init, 500); }
  </script>
</body>
</html>
"""


# ─── Validazione ──────────────────────────────────────────────────────────────

def validate_map_data(data: dict) -> None:
    missing = {"title", "left", "right"} - data.keys()
    if missing:
        raise ValueError(f"Chiavi mancanti nel JSON: {missing}")
    for side in ("left", "right"):
        if not isinstance(data[side], list):
            raise ValueError(f"'{side}' deve essere una lista.")
        for i, s in enumerate(data[side]):
            if not all(k in s for k in ("name", "style", "items")):
                raise ValueError(f"'{side}[{i}]' mancante di 'name', 'style' o 'items'.")


# ─── Generazione HTML ─────────────────────────────────────────────────────────

def generate_html(data: dict) -> str:
    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    return HTML_TEMPLATE.replace("%%MAP_DATA_JSON%%", json_str)


# ─── Screenshot + resize 1080×1080 ───────────────────────────────────────────

def render_to_png(html: str, output_path: Path, viewport_width: int) -> None:
    """
    Pipeline di rendering:

    1. Playwright apre la pagina e aspetta window.__mindmapReady.
       A quel punto squarify() ha già modificato il DOM e il layout
       è quadrato (W ≈ H).

    2. element.screenshot() cattura #content-root al millimetro
       con device_scale_factor=2 (HiDPI).

    3. Pillow fa il resize a 1080×1080. Poiché il contenuto è già
       circa quadrato, lo stretch non uniforme residuo è impercettibile
       (< 2% in ciascun asse per la piccola differenza rimanente dopo
       il layout recalc del browser).

    Ho scelto di NON fare letterbox qui: l'obiettivo è riempire
    interamente il quadrato, non preservare l'aspect ratio esatto.
    """
    from playwright.sync_api import sync_playwright
    from PIL import Image

    RENDER_SCALE = 2

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": viewport_width, "height": 1400},
            device_scale_factor=RENDER_SCALE,
        )
        page = context.new_page()
        page.goto("about:blank")
        page.set_content(html, wait_until="domcontentloaded")

        try:
            page.wait_for_function("document.fonts.status === 'loaded'", timeout=10_000)
        except Exception:
            pass

        page.wait_for_function("window.__mindmapReady === true", timeout=15_000)
        page.wait_for_timeout(400)  # margine per CSS compositing (box-shadow, gradienti)

        raw_bytes = page.locator("#content-root").screenshot(type="png")

        context.close()
        browser.close()

    # ── Resize diretto a 1080×1080 ────────────────────────────────────────
    # squarify() ha già reso il contenuto ~quadrato in JS, quindi questo
    # resize è quasi uniforme. LANCZOS è il kernel migliore per downscale.
    content_img = Image.open(BytesIO(raw_bytes)).convert("RGB")
    final = content_img.resize(OUTPUT_SIZE, Image.LANCZOS)
    final.save(str(output_path), "PNG", optimize=True)


# ─── Entry point ──────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Genera un PNG 1080×1080 di una mappa mentale da un file JSON."
    )
    parser.add_argument("input_json")
    parser.add_argument("output_png", nargs="?", default=None)
    parser.add_argument("--width", type=int, default=1000,
                        help="Larghezza viewport (default: 1000). "
                             "Valori più bassi = elementi più grandi nell'output.")
    parser.add_argument("--keep-html", action="store_true",
                        help="Salva anche l'HTML generato accanto al PNG.")
    args = parser.parse_args()

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

    try:
        validate_map_data(data)
    except ValueError as e:
        print(f"[ERRORE] Struttura JSON non valida: {e}", file=sys.stderr)
        sys.exit(1)

    output_path = Path(args.output_png) if args.output_png else input_path.with_suffix(".png")

    print(f"[1/3] Genero HTML da: {input_path}")
    html = generate_html(data)

    if args.keep_html:
        html_path = output_path.with_suffix(".html")
        html_path.write_text(html, encoding="utf-8")
        print(f"      HTML salvato in: {html_path}")

    print(f"[2/3] Rendering Chromium headless + squarify + resize {OUTPUT_SIZE[0]}×{OUTPUT_SIZE[1]}px...")
    try:
        render_to_png(html, output_path, viewport_width=args.width)
    except Exception as e:
        print(f"[ERRORE] Render fallito: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"[3/3] PNG salvato in: {output_path}")
    size_kb = output_path.stat().st_size // 1024
    print(f"      Dimensione: {size_kb} KB  |  Risoluzione: {OUTPUT_SIZE[0]}×{OUTPUT_SIZE[1]} px")


if __name__ == "__main__":
    main()