#!/usr/bin/env python3
"""
cheat_sheet_generator.py

Ho scritto questo script per trasformare un JSON strutturato in un PNG
1080px-wide da usare come infografica o slide di carousel.

Pipeline:
  1. Parso il JSON di input (via --input o stdin)
  2. LayoutEngine calcola il density score di ogni card e le raggruppa
     in Row dict usando un algoritmo greedy (3col → 2col/1-2 → full)
  3. Jinja2 renderizza template.html.j2 iniettando meta + rows
  4. Playwright cattura il DOM come PNG full-page a 1080px di larghezza

Utilizzo:
  python3 table_generator.py --input my_data.json --output out.png
  python3 table_generator.py --input my_data.json --debug-html
"""

import json
import math
import argparse
import sys
from pathlib import Path

# ─── Dipendenze esterne ───────────────────────────────────────────────────────
try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
except ImportError:
    sys.exit("❌  Installa Jinja2:    pip install jinja2")

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("❌  Installa Playwright: pip install playwright && playwright install chromium")


# ─── Soglie di packing ────────────────────────────────────────────────────────
#
# Cosa:  Questi tre parametri governano la decisione del LayoutEngine su
#        quante card affiancare in una stessa riga logica.
#
# Come:  Ogni card riceve un "density score" (unità virtuali di altezza,
#        non pixel) calcolato sommando i contributi stimati dei suoi blocchi
#        di contenuto. Lo score viene confrontato con queste soglie.
#
# Perché questi valori specifici:
#
#   THRESH_3COL = 30
#     Una card tipica da 3col (colonna ~340px) ha al più:
#       • 6 voci di lista freccia:  5 (header) + 6×2.5 = 20
#       • 3-row table + text-box:   5 + 2.5 + 3×3 + 3.5 = ~20
#     Ho scelto 30 come tetto per dare margine a card con 8 voci o
#     una tabella da 5 righe (~27.5) senza rischiare overflow verticale
#     in una colonna stretta. Oltre 30 il testo inizia a strabordare
#     o la card diventa troppo alta rispetto alle sue vicine 3col.
#
#   THRESH_2COL = 58
#     Una card tipica da 2col (colonna ~530px) ha al più:
#       • 9 voci di lista + text-box:  5 + 22.5 + 7 = ~34.5
#       • 8-row table con header:      5 + 2.5 + 24 = ~31.5
#       • 5 items + divider + 4-row table: ~38
#     Ho fissato 58 per includere anche card con due sezioni separate
#     da un divider (es. Skills + Hooks del cheat sheet originale: ~38)
#     e lasciare margine fino a configurazioni dense ma non patologiche.
#     Oltre 58 la card è così alta che affiancarla ad un'altra creerebbe
#     uno spazio vuoto enorme nella colonna più corta.
#
#   RATIO_1_2 = 0.50
#     Uso il layout asimmetrico 1fr+2fr solo quando una card è meno della
#     metà della densità dell'altra. Questo replica il caso classico:
#     kv_list corta (score ~22) accanto a shot-grid (score ~19) non
#     attiva questo ratio. Il caso tipico è una kv_list brevissima
#     (score ~10-12) accanto a una card con tabella grande.
#     Ho preferito un valore conservativo (0.50) per non attivare
#     il layout asimmetrico per coppie leggermente sbilanciate dove
#     il 2col è comunque visivamente accettabile.

THRESH_3COL : float = 30.0
THRESH_2COL : float = 58.0
RATIO_1_2   : float = 0.50


# ─── LayoutEngine ─────────────────────────────────────────────────────────────

class LayoutEngine:
    """
    Ho isolato tutta la logica di layout in questa classe per tenerla
    separata dalla generazione HTML e dal rendering. Prende la lista
    raw delle card e restituisce una lista di Row dict:
        {"layout": "full" | "2col" | "3col" | "1-2", "cards": [...]}
    """

    # ── Stima dell'altezza di un blocco ─────────────────────────────────────

    def _score_block(self, block: dict) -> float:
        """
        Ho calibrato questi coefficienti empiricamente sui blocchi CSS del
        template (font-size 11-12px, padding card 8px 10px, gap: 6px).
        L'unità virtuale vale approssimativamente 2px di altezza reale,
        ma l'importante è la coerenza relativa tra tipi di blocco diversi,
        non la precisione assoluta.
        """
        btype = block.get("type", "")

        if btype == "table":
            # thead vale ~2.5 unità (padding 3px × 2 + font 11px)
            # Ogni riga dati: ~3.0 unità (padding 3px × 2 + line-height 1.4 × 11.5px)
            has_headers = bool(block.get("headers"))
            n_rows = len(block.get("rows", []))
            return (2.5 if has_headers else 0.0) + n_rows * 3.0

        elif btype in ("list", "kv_list"):
            # Ogni voce: font 11.5px × line-height 1.4 + gap 2px ≈ 2.5 unità
            return len(block.get("items", [])) * 2.5

        elif btype == "text_block":
            # Stimo i caratteri per riga nel corpo della card.
            # A font Nunito 11px in ~320px di larghezza (3col) entrano ~60 char.
            # Uso 60 come denominatore conservativo; un corpo 2col stima per eccesso.
            # Aggiungo 3.5 unità fisse per il padding del .text-box.
            text = block.get("content", "")
            lines = max(1, math.ceil(len(text) / 60)) + text.count("\n")
            return lines * 2.0 + 3.5

        elif btype == "tags":
            # I tag si dispongono in righe da 2 (flex: 1 1 calc(50% - 3px))
            # Ogni riga: ~2.8 unità (pill height ~32px/2 = ~2.8 unità)
            n = len(block.get("items", []))
            return math.ceil(n / 2) * 2.8 + 2.0

        elif btype == "check_grid":
            # .check-grid usa 3 colonne CSS interne; ogni riga vale ~2.5 unità
            n = len(block.get("items", []))
            return math.ceil(n / 3) * 2.5

        elif btype == "shot_grid":
            # I 3 shot-box sono affiancati in un'unica riga con padding 8px × 2
            # + label + testo su 2-3 righe ≈ 12 unità fisse
            return 12.0

        elif btype == "section_label":
            # Testo uppercase piccolo: ~2 unità
            return 2.0

        elif btype == "divider":
            # Linea sottile 1px + margin 4px × 2 = 1 unità
            return 1.0

        elif btype == "note":
            # Simile a text_block ma senza il box: stima più corta
            text = block.get("content", "")
            lines = max(1, math.ceil(len(text) / 70))
            return lines * 1.8

        return 0.0

    def compute_score(self, card: dict) -> float:
        """
        Ho strutturato il calcolo come somma dell'header fisso (5 unità)
        più il contributo di ciascun blocco del corpo. Il gap:6px del
        card__body aggiunge ~0.5 unità per ogni blocco aggiuntivo dopo il primo.
        """
        # Header sempre presente, contribuisce con un'altezza fissa
        score = 5.0

        blocks = card.get("content", [])
        for i, block in enumerate(blocks):
            score += self._score_block(block)
            # Ho aggiunto il gap dell'elemento body (gap:6px ≈ 0.5 unità)
            # solo dal secondo blocco in poi
            if i > 0:
                score += 0.5

        return score

    # ── Greedy row packing ───────────────────────────────────────────────────

    def pack_rows(self, cards: list) -> list:
        """
        Ho scelto un algoritmo greedy per il packing perché:
          1. La dimensione tipica di un cheat sheet (10-20 card) non
             giustifica la complessità di un approccio DP.
          2. Il greedy produce risultati prevedibili e facilmente debuggabili
             modificando le soglie.
          3. L'attributo force_layout permette override manuali per i casi
             borderline che l'algoritmo non riesce a gestire da solo.

        L'ordine di preferenza è: 3col → 2col/1-2 → full.
        Non provo mai a "guardare avanti" di più di 3 card; il greedy
        locale è sufficientemente buono per layout lineari top-down.
        """
        rows   = []
        # Ho una copia per non mutare la lista originale
        remaining = list(cards)

        while remaining:
            card0 = remaining[0]

            # ── Override manuale via force_layout ────────────────────────────
            # Cosa: Se la card dichiara esplicitamente il layout, lo rispetto
            #       senza passare per il calcolo dello score.
            # Perché: Alcuni layout (es. check_grid full-width, shot_grid 1-2)
            #         sono scelte di design non deducibili dallo score numerico.
            if "force_layout" in card0:
                forced = card0["force_layout"]
                n = len(remaining)
                if forced == "full" or n == 1:
                    rows.append({"layout": "full", "cards": [remaining.pop(0)]})
                elif forced in ("2col", "1-2") and n >= 2:
                    rows.append({"layout": forced, "cards": [remaining.pop(0), remaining.pop(0)]})
                elif forced == "3col" and n >= 3:
                    rows.append({"layout": "3col",
                                 "cards": [remaining.pop(0), remaining.pop(0), remaining.pop(0)]})
                else:
                    # Non ci sono abbastanza card: degrader a full
                    rows.append({"layout": "full", "cards": [remaining.pop(0)]})
                continue

            s0 = self.compute_score(card0)

            # ── Provo 3col ───────────────────────────────────────────────────
            # Condizione: almeno 3 card E tutte con score ≤ THRESH_3COL.
            # Ho aggiunto il controllo force_layout sulle card 1 e 2: se una
            # delle card successive vuole un layout specifico, non la trascino
            # in una riga multi-colonna che ignorerebbe quella sua esigenza.
            if len(remaining) >= 3:
                if (not remaining[1].get("force_layout") and
                        not remaining[2].get("force_layout")):
                    s1 = self.compute_score(remaining[1])
                    s2 = self.compute_score(remaining[2])
                    if max(s0, s1, s2) <= THRESH_3COL:
                        rows.append({
                            "layout": "3col",
                            "cards": [remaining.pop(0), remaining.pop(0), remaining.pop(0)]
                        })
                        continue

            # ── Provo 2col o 1-2 ────────────────────────────────────────────
            # Stesso principio: verifico che la card successiva non abbia
            # un force_layout prima di accoppiare.
            if len(remaining) >= 2:
                if not remaining[1].get("force_layout"):
                    s1 = self.compute_score(remaining[1])
                    if max(s0, s1) <= THRESH_2COL:
                        layout = "2col"
                        if s1 > 0 and s0 / s1 <= RATIO_1_2:
                            layout = "1-2"
                        elif s0 > 0 and s1 / s0 <= RATIO_1_2:
                            layout = "2col"
                        rows.append({
                            "layout": layout,
                            "cards": [remaining.pop(0), remaining.pop(0)]
                        })
                        continue

            # ── Fallback: full width ─────────────────────────────────────────
            # Arrivo qui se la card non entra in nessun layout multi-colonna.
            # Questo succede per card molto dense (score > THRESH_2COL) oppure
            # per l'ultima card rimasta (dispari dopo aver formato le righe precedenti).
            rows.append({"layout": "full", "cards": [remaining.pop(0)]})

        return rows


# ─── HTML Generation ──────────────────────────────────────────────────────────

def generate_html(meta: dict, rows: list, template_path: Path) -> str:
    """
    Ho usato Jinja2 con autoescape attivo per tutti i valori utente
    (titoli, testi, voci di lista). I blocchi con "html": true nel JSON
    usano il filtro | safe nel template: l'autore del JSON si assume la
    responsabilità di non iniettare HTML malevolo.
    """
    # Ho configurato autoescape per le estensioni html e j2 per sicurezza
    env = Environment(
        loader=FileSystemLoader(str(template_path.parent)),
        autoescape=select_autoescape(["html", "j2"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    # Ho aggiunto il metodo dict.get come filtro globale per usarlo nel template
    # senza dover fare workaround con default()
    env.globals["dict"] = dict

    template = env.get_template(template_path.name)
    return template.render(meta=meta, rows=rows)


# ─── PNG Rendering ────────────────────────────────────────────────────────────

def render_png(html: str, output_path: Path, width: int = 1080,
               font_wait_ms: int = 1800) -> None:
    """
    Ho scelto Playwright su Chromium piuttosto che wkhtmltoimage perché:
      • Supporta CSS Grid, flexbox e le proprietà CSS moderne del template.
      • Scarica i font Google direttamente (con wait_until="networkidle").
      • full_page=True cattura l'intera altezza del documento senza
        dover conoscere in anticipo l'altezza dell'output.
      • È installabile senza dipendenze di sistema via pip + playwright install.

    Perché font_wait_ms = 1800?
      "networkidle" attende che non ci siano richieste di rete per 500ms,
      ma il rendering effettivo dei font (font-display: swap) può arrivare
      qualche frame dopo. 1800ms è un margine sicuro senza rendere lo
      script notevolmente più lento.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox", "--disable-gpu"])
        # Ho impostato il viewport a 1080px di larghezza; l'altezza è
        # irrilevante perché uso full_page=True per lo screenshot
        page = browser.new_page(viewport={"width": width, "height": 1})

        # Imposto il contenuto HTML e attendo che la rete sia idle
        # (font Google scaricati, foglio di stile caricato)
        page.set_content(html, wait_until="networkidle")

        # Ho aggiunto un'attesa esplicita dopo networkidle per dare tempo
        # al browser di completare il font-display swap prima dello screenshot
        page.wait_for_timeout(font_wait_ms)

        page.screenshot(
            path=str(output_path),
            full_page=True,
            type="png",
        )
        browser.close()

    print(f"✅  PNG salvato in: {output_path}")


# ─── Entry Point ──────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Genera un PNG cheat sheet da un file JSON strutturato.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esempi:
  python3 cheat_sheet_generator.py --input example_input.json
  python3 cheat_sheet_generator.py --input data.json --output mio_sheet.png
  python3 cheat_sheet_generator.py --input data.json --debug-html
  python3 cheat_sheet_generator.py --input data.json --show-scores
        """,
    )
    parser.add_argument(
        "-i", "--input",
        default="example_input.json",
        help="Percorso del file JSON di input (default: example_input.json)",
    )
    parser.add_argument(
        "-o", "--output",
        default="output.png",
        help="Percorso del file PNG di output (default: output.png)",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=1080,
        help="Larghezza in pixel del PNG (default: 1080)",
    )
    parser.add_argument(
        "--debug-html",
        action="store_true",
        help="Salva l'HTML generato in output.html invece di renderizzare il PNG",
    )
    parser.add_argument(
        "--show-scores",
        action="store_true",
        help="Stampa i density score di ogni card e il layout assegnato",
    )
    parser.add_argument(
        "--template",
        default=None,
        help="Percorso alternativo del template Jinja2 (default: ./template.html.j2)",
    )
    args = parser.parse_args()

    # ── Carico il JSON ───────────────────────────────────────────────────────
    input_path = Path(args.input)
    if not input_path.exists():
        sys.exit(f"❌  File non trovato: {input_path}")

    try:
        with open(input_path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        sys.exit(f"❌  JSON non valido: {e}")

    meta  = data.get("meta", {})
    cards = data.get("cards", [])

    if not cards:
        sys.exit("❌  Il JSON non contiene card.")

    # ── Layout engine ────────────────────────────────────────────────────────
    engine = LayoutEngine()
    rows   = engine.pack_rows(cards)

    # Ho aggiunto --show-scores per debug: permette di vedere le decisioni
    # di layout senza dover renderizzare il PNG
    if args.show_scores:
        print("\n── Density scores e layout assegnato ──────────────────")
        for row in rows:
            scores = [f"{c['title'][:28]!r}: {engine.compute_score(c):.1f}" for c in row["cards"]]
            print(f"  [{row['layout']:6s}]  {' | '.join(scores)}")
        print()

    # ── Risolvo il percorso del template ────────────────────────────────────
    if args.template:
        template_path = Path(args.template)
    else:
        # Ho impostato il default nella stessa directory dello script
        template_path = Path(__file__).parent / "template.html.j2"

    if not template_path.exists():
        sys.exit(f"❌  Template non trovato: {template_path}")

    # ── Genero l'HTML ────────────────────────────────────────────────────────
    html = generate_html(meta, rows, template_path)

    # ── Debug HTML o PNG ─────────────────────────────────────────────────────
    if args.debug_html:
        html_out = Path(args.output).with_suffix(".html")
        html_out.write_text(html, encoding="utf-8")
        print(f"✅  HTML salvato in: {html_out}")
        return

    output_path = Path(args.output)
    render_png(html, output_path, width=args.width)


if __name__ == "__main__":
    main()