#!/usr/bin/env python3
"""
mind_map_generator.py  v4.1

Output:
  _output/<nome_json>/overview.png|html          — mappa globale completa
  _output/<nome_json>/<01_nome_cat>.png|html     — un file per ogni categoria

Utilizzo:
  python mind_map_generator.py <file.json>          # genera PNG (default)
  python mind_map_generator.py <file.json> --html   # genera HTML/SVG
"""

# Ho aggiunto argparse per gestire i parametri CLI in modo robusto,
# ottenendo --help automatico e validazione dei tipi senza if/sys.argv manuali.
import argparse
import sys
import os
import json
import textwrap
import shutil

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle

# =============================================================================
# STILE
# =============================================================================
BG_COLOR         = "#12122a"
ITEM_BG_COLOR    = "#1a1a38"
ITEM_LABEL_COLOR = "#9999bb"
CMD_TEXT_COLOR   = "#ffffff"
CONN_COLOR       = "#3a3a6a"
FONT             = "DejaVu Sans"

# =============================================================================
# METRICHE OVERVIEW
# =============================================================================
OV_LINE_H    = 0.35
OV_ROW_PAD   = 0.30
OV_CAT_GAP   = 0.80
OV_KEY_WRAP  = 14
OV_DESC_WRAP = 35
OV_CAT_BOX_W = 3.2
OV_CAT_BOX_H = 1.1
OV_PILL_W    = 2.5
OV_CENTER_R  = 1.6

# =============================================================================
# METRICHE FOCUS (canvas quadrato 1080×1080)
# =============================================================================
FO_LINE_H    = 1.20
FO_ROW_PAD   = 1.30
FO_KEY_WRAP  = 10
FO_DESC_WRAP = 18
FO_CAT_BOX_W = 9.0
FO_CAT_BOX_H = 4.0
FO_PILL_W    = 6.5
FO_DESC_W    = 9.5
FO_LIMIT     = 30.0
FO_CENTER    = FO_LIMIT / 2  # 15.0

# =============================================================================
# UTILITY CONDIVISE (matplotlib + HTML)
# =============================================================================

def _darken(hex_color: str, factor: float = 0.65) -> str:
    """Scurisco un colore hex per ricavare il colore bordo dei box."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"#{int(r*factor):02x}{int(g*factor):02x}{int(b*factor):02x}"


def _wrap(text: str, width: int) -> list:
    return textwrap.wrap(text, width=width) or [text]


def _conn(ax, x1, y1, x2, y2, lw=0.75):
    """Disegno una linea tratteggiata di connessione (matplotlib)."""
    ax.plot([x1, x2], [y1, y2],
            color=CONN_COLOR, linewidth=lw, linestyle="--", zorder=1)


# =============================================================================
# SVG / HTML HELPERS
#
# Ho scelto SVG inline nell'HTML perché:
# - è scalabile senza perdita di qualità a qualsiasi risoluzione schermo
# - non richiede librerie JS esterne per il rendering
# - le coordinate sono esattamente le stesse del sistema matplotlib,
#   semplificando la traduzione 1:1 della logica di layout
# =============================================================================

def _svg_escape(s: str) -> str:
    """
    Eseguo l'escape dei caratteri speciali XML nel testo SVG.
    Necessario per evitare HTML injection e SVG malformato.
    """
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;"))


def _svg_flip_y(y: float, H: float) -> float:
    """
    Converto le coordinate matplotlib (origine in basso, y cresce verso l'alto)
    in coordinate SVG (origine in alto, y cresce verso il basso).
    La formula è semplicemente una riflessione rispetto alla mezzeria: H - y.
    """
    return H - y


def _svg_rect(x: float, y: float, w: float, h: float,
              rx: float = 0.1, fill: str = BG_COLOR,
              stroke: str = "#000000", stroke_width: float = 0.05) -> str:
    """
    Genero un <rect> SVG con angoli arrotondati.
    y è già in coordinate SVG (origine in alto).
    rx/ry in unità coordinate del viewBox (equivalente al pad di FancyBboxPatch).
    stroke_width è anch'esso in unità coordinate: ho convertito i pt matplotlib
    usando il fattore px/unit del rispettivo canvas (60px/u overview, 36px/u focus).
    """
    return (
        f'<rect x="{x:.4f}" y="{y:.4f}" width="{w:.4f}" height="{h:.4f}" '
        f'rx="{rx:.4f}" ry="{rx:.4f}" fill="{fill}" '
        f'stroke="{stroke}" stroke-width="{stroke_width:.4f}"/>'
    )


def _svg_circle(cx: float, cy: float, r: float,
                fill: str, stroke: str, stroke_width: float = 0.0) -> str:
    """
    Genero un <circle> SVG. cy è già in coordinate SVG.
    stroke_width=0 equivale a nessun bordo visibile.
    """
    return (
        f'<circle cx="{cx:.4f}" cy="{cy:.4f}" r="{r:.4f}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width:.4f}"/>'
    )


def _svg_line(x1: float, y1: float, x2: float, y2: float,
              stroke: str = CONN_COLOR, stroke_width: float = 0.03,
              dash: str = "0.2,0.1") -> str:
    """
    Genero una linea tratteggiata SVG equivalente al linestyle="--" di matplotlib.
    Tutti i valori numerici (incluso dash) sono in unità coordinate del viewBox.
    """
    return (
        f'<line x1="{x1:.4f}" y1="{y1:.4f}" x2="{x2:.4f}" y2="{y2:.4f}" '
        f'stroke="{stroke}" stroke-width="{stroke_width:.4f}" '
        f'stroke-dasharray="{dash}"/>'
    )


def _svg_text_block(x: float, y_center: float, lines: list,
                    font_size: float, fill: str,
                    font_weight: str = "normal",
                    text_anchor: str = "middle",
                    line_spacing: float = 1.25) -> str:
    """
    Genero un blocco di testo SVG centrato verticalmente su y_center.

    Ho scelto <text> separati per ogni riga invece di <tspan dy=...>:
    il posizionamento è esplicito riga per riga e non accumula errori di offset.

    font_size è in unità coordinate del viewBox (non in pt).
    Ho calcolato la conversione da pt matplotlib a unità SVG con:
      overview (60px/unit a 150dpi): pt * (150/72) / 60
      focus    (36px/unit a 100dpi): pt * (100/72) / 36
    dominant-baseline="middle" centra ogni riga rispetto alla y specificata.
    """
    lh = font_size * line_spacing
    total_h = lh * (len(lines) - 1)
    y_start = y_center - total_h / 2

    parts = []
    for i, line in enumerate(lines):
        y = y_start + i * lh
        parts.append(
            f'<text x="{x:.4f}" y="{y:.4f}" '
            f'text-anchor="{text_anchor}" dominant-baseline="middle" '
            f'font-size="{font_size:.4f}" font-family="{FONT}" '
            f'font-weight="{font_weight}" fill="{fill}">'
            f'{_svg_escape(line)}</text>'
        )
    return "\n".join(parts)


def _svg_html_page(title: str, svg_tag: str, body_style: str = "") -> str:
    """
    Assemblo la pagina HTML completa con SVG inline.
    Ho incluso viewport meta tag e box-sizing per compatibilità mobile.
    """
    return f"""<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_svg_escape(title)}</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: {BG_COLOR};
      display: flex;
      justify-content: center;
      align-items: flex-start;
      min-height: 100vh;
      padding: 16px;
      {body_style}
    }}
  </style>
</head>
<body>
{svg_tag}
</body>
</html>"""


# =============================================================================
# OVERVIEW — misuratori di altezza (condivisi matplotlib + HTML)
# =============================================================================

def _ov_item_h(key: str, desc: str) -> float:
    n = max(len(_wrap(key, OV_KEY_WRAP)), len(_wrap(desc, OV_DESC_WRAP)))
    return n * OV_LINE_H + OV_ROW_PAD


def _ov_cat_h(cat: dict) -> float:
    return sum(_ov_item_h(k, d) for k, d in cat.get("items", []))


# =============================================================================
# OVERVIEW — motore di layout (condiviso matplotlib + HTML)
# =============================================================================

def _ov_scale(categories: list, canvas_h: float) -> float:
    """Calcolo la scala che fa stare tutte le categorie nel canvas."""
    total = sum(_ov_cat_h(c) for c in categories)
    total += OV_CAT_GAP * max(0, len(categories) - 1)
    return min(1.0, (canvas_h * 0.95) / total) if total > 0 else 1.0


def _ov_layout_tops(categories: list, canvas_cy: float, scale: float) -> list:
    """
    Calcolo i bordi superiori di ogni categoria centrando il blocco
    rispetto a canvas_cy.
    """
    total_scaled = (
        sum(_ov_cat_h(c) for c in categories) * scale
        + OV_CAT_GAP * scale * max(0, len(categories) - 1)
    )
    y = canvas_cy + total_scaled / 2
    tops = []
    for cat in categories:
        tops.append(y)
        y -= _ov_cat_h(cat) * scale + OV_CAT_GAP * scale
    return tops


# =============================================================================
# OVERVIEW — disegno (matplotlib / PNG)
# =============================================================================

def _ov_center_node(ax, cx, cy, title):
    ax.add_patch(Circle((cx, cy), OV_CENTER_R, color="#1e1e4a", zorder=4))
    ax.add_patch(Circle((cx, cy), OV_CENTER_R, fill=False,
                         edgecolor="#7777ff", linewidth=2.5, zorder=5))
    lines = title.split("\n")
    lh    = 0.42
    y0    = cy + lh * (len(lines) - 1) / 2
    for i, line in enumerate(lines):
        ax.text(cx, y0 - i * lh, line, ha="center", va="center",
                fontsize=12, color="white", fontweight="bold",
                zorder=6, fontfamily=FONT)


def _ov_cat_box(ax, cx, cy, label, color):
    ax.add_patch(FancyBboxPatch(
        (cx - OV_CAT_BOX_W/2, cy - OV_CAT_BOX_H/2), OV_CAT_BOX_W, OV_CAT_BOX_H,
        boxstyle="round,pad=0.08",
        facecolor=color, edgecolor=_darken(color), linewidth=1.5, zorder=3
    ))
    ax.text(cx, cy, "\n".join(_wrap(label, 11)),
            ha="center", va="center",
            fontsize=9.5, color="white", fontweight="bold",
            zorder=4, fontfamily=FONT, linespacing=1.3)


def _ov_item_row(ax, y_top, key, desc, color,
                 side, x_cat, x_key, x_desc, scale) -> float:
    key_lines  = _wrap(key,  OV_KEY_WRAP)
    desc_lines = _wrap(desc, OV_DESC_WRAP)
    n_lines    = max(len(key_lines), len(desc_lines))
    row_h      = (n_lines * OV_LINE_H + OV_ROW_PAD) * scale
    yc         = y_top - row_h / 2

    pill_h = len(key_lines) * OV_LINE_H * scale + 0.12
    ax.add_patch(FancyBboxPatch(
        (x_key - OV_PILL_W/2, yc - pill_h/2), OV_PILL_W, pill_h,
        boxstyle="round,pad=0.04",
        facecolor=ITEM_BG_COLOR, edgecolor=color, linewidth=0.9, zorder=3
    ))
    ax.text(x_key, yc, "\n".join(key_lines),
            ha="center", va="center",
            fontsize=8.0, color=CMD_TEXT_COLOR, fontfamily=FONT, zorder=4, linespacing=1.2)

    ha = "right" if side == "left" else "left"
    ax.text(x_desc, yc, "\n".join(desc_lines),
            ha=ha, va="center",
            fontsize=8.0, color=ITEM_LABEL_COLOR, fontfamily=FONT, zorder=4, linespacing=1.2)

    pill_edge_x = x_key + (OV_PILL_W/2 if side == "right" else -OV_PILL_W/2)
    cat_edge_x  = x_cat + (-OV_CAT_BOX_W/2 if side == "left" else OV_CAT_BOX_W/2)
    _conn(ax, cat_edge_x, yc, pill_edge_x, yc)
    return row_h


def _ov_render_side(ax, categories, tops, scale, side, cx, cy):
    sign   = -1 if side == "left" else 1
    x_cat  = cx + sign * 5.5
    x_key  = cx + sign * 8.8
    x_desc = cx + sign * 11.0

    for cat, y_top in zip(categories, tops):
        color        = cat["color"]
        cat_h_scaled = _ov_cat_h(cat) * scale
        cat_cy       = y_top - cat_h_scaled / 2

        center_edge  = cx + sign * OV_CENTER_R
        cat_edge     = x_cat + (-OV_CAT_BOX_W/2 if side == "right" else OV_CAT_BOX_W/2)
        _conn(ax, center_edge, cy, cat_edge, cat_cy)

        _ov_cat_box(ax, x_cat, cat_cy, cat["name"], color)

        y_cursor = y_top
        for key, desc in cat.get("items", []):
            consumed = _ov_item_row(
                ax, y_cursor, key, desc, color,
                side, x_cat, x_key, x_desc, scale
            )
            y_cursor -= consumed


def render_overview(data: dict, output_path: str, dpi: int = 150):
    fig_w, fig_h = 30, 20
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(BG_COLOR)
    ax.set_xlim(0, fig_w)
    ax.set_ylim(0, fig_h)
    ax.axis("off")

    cx, cy    = fig_w / 2, fig_h / 2
    canvas_h  = fig_h - 1.6
    left_cats  = data.get("left",  [])
    right_cats = data.get("right", [])

    scale = min(_ov_scale(left_cats,  canvas_h),
                _ov_scale(right_cats, canvas_h))

    _ov_center_node(ax, cx, cy, data["title"])
    _ov_render_side(ax, left_cats,  _ov_layout_tops(left_cats,  cy, scale), scale, "left",  cx, cy)
    _ov_render_side(ax, right_cats, _ov_layout_tops(right_cats, cy, scale), scale, "right", cx, cy)

    ax.text(0.5, fig_h - 0.25, data["title"].replace("\n", " "),
            fontsize=14, color="white", fontweight="bold",
            va="top", fontfamily=FONT)

    plt.savefig(output_path, dpi=dpi, bbox_inches="tight",
                facecolor=BG_COLOR, pad_inches=0.2)
    plt.close()
    print(f"  ✓ overview: {output_path}")


# =============================================================================
# OVERVIEW — disegno HTML/SVG
#
# Ho replicato esattamente la stessa logica di layout di render_overview().
# L'unica differenza è che le primitive matplotlib (Circle, FancyBboxPatch,
# ax.text, ax.plot) vengono tradotte 1:1 in elementi SVG.
#
# Conversione coordinate: matplotlib usa y=0 in basso; SVG usa y=0 in alto.
# Applico _svg_flip_y() su tutti i punti y prima di emetterli.
#
# Conversione stroke-width: matplotlib linewidth è in display-pt (pt @ fig DPI).
# Per overview (150dpi, 60px per unità coordinate):
#   lw_svg = lw_pt * (150/72) / 60
# =============================================================================

def render_overview_html(data: dict, output_path: str):
    """
    Genero la mappa globale come file HTML con SVG inline.
    Ho scelto viewBox="0 0 30 20" (stesse unità di matplotlib) per riutilizzare
    direttamente tutte le costanti di posizione già calibrate.
    """
    W, H = 30.0, 20.0
    elems = []

    # Sfondo esplicito: il rect copre tutto il viewBox
    elems.append(f'<rect width="{W}" height="{H}" fill="{BG_COLOR}"/>')

    cx, cy   = W / 2, H / 2
    canvas_h = H - 1.6
    left_cats  = data.get("left",  [])
    right_cats = data.get("right", [])
    scale = min(_ov_scale(left_cats, canvas_h), _ov_scale(right_cats, canvas_h))

    # --- Nodo centrale ---
    # Ho separato il cerchio pieno dal bordo perché SVG non ha fill=False;
    # uso due <circle>: uno senza stroke e uno senza fill.
    cy_svg = _svg_flip_y(cy, H)
    elems.append(_svg_circle(cx, cy_svg, OV_CENTER_R, "#1e1e4a", "none"))
    # stroke-width: 2.5pt @ 150dpi = 5.2px / 60px/u = 0.087u
    elems.append(_svg_circle(cx, cy_svg, OV_CENTER_R, "none", "#7777ff", stroke_width=0.09))
    # font-size: 12pt @ 150dpi = 25px / 60px/u = 0.42u
    elems.append(_svg_text_block(
        cx, cy_svg, data["title"].split("\n"), 0.42, "white", font_weight="bold"
    ))

    # --- Lato sinistro e destro ---
    for side in ("left", "right"):
        cats = left_cats if side == "left" else right_cats
        tops = _ov_layout_tops(cats, cy, scale)
        sign   = -1 if side == "left" else 1
        x_cat  = cx + sign * 5.5
        x_key  = cx + sign * 8.8
        x_desc = cx + sign * 11.0

        for cat, y_top in zip(cats, tops):
            color        = cat["color"]
            cat_h_scaled = _ov_cat_h(cat) * scale
            cat_cy       = y_top - cat_h_scaled / 2
            cat_cy_svg   = _svg_flip_y(cat_cy, H)

            # Connettore centro → cat box
            center_edge = cx + sign * OV_CENTER_R
            cat_edge    = x_cat + (-OV_CAT_BOX_W/2 if side == "right" else OV_CAT_BOX_W/2)
            elems.append(_svg_line(
                center_edge, cy_svg,
                cat_edge,    cat_cy_svg,
                stroke_width=0.03, dash="0.18,0.09"
            ))

            # Cat box: FancyBboxPatch(bottom-left, w, h) → rect(top-left, w, h) in SVG
            # top-left SVG y = flip(bottom-left mpl y + h) = flip(cat_cy - h/2 + h)
            bx  = x_cat - OV_CAT_BOX_W/2
            bym = cat_cy - OV_CAT_BOX_H/2          # bottom-left y in matplotlib
            elems.append(_svg_rect(
                bx,
                _svg_flip_y(bym + OV_CAT_BOX_H, H),  # top-left y in SVG
                OV_CAT_BOX_W, OV_CAT_BOX_H,
                rx=0.08,
                fill=color, stroke=_darken(color),
                # 1.5pt @ 150dpi = 3.1px / 60px/u = 0.052u
                stroke_width=0.055
            ))
            # font-size: 9.5pt @ 150dpi = 19.8px / 60px/u = 0.33u
            elems.append(_svg_text_block(
                x_cat, cat_cy_svg, _wrap(cat["name"], 11), 0.33, "white",
                font_weight="bold"
            ))

            # Item rows
            y_cursor = y_top
            for key, desc in cat.get("items", []):
                key_lines  = _wrap(key,  OV_KEY_WRAP)
                desc_lines = _wrap(desc, OV_DESC_WRAP)
                n_lines    = max(len(key_lines), len(desc_lines))
                row_h      = (n_lines * OV_LINE_H + OV_ROW_PAD) * scale
                yc         = y_cursor - row_h / 2
                yc_svg     = _svg_flip_y(yc, H)

                # Pill chiave
                pill_h = len(key_lines) * OV_LINE_H * scale + 0.12
                px  = x_key - OV_PILL_W/2
                pym = yc - pill_h/2
                elems.append(_svg_rect(
                    px,
                    _svg_flip_y(pym + pill_h, H),
                    OV_PILL_W, pill_h,
                    rx=0.04,
                    fill=ITEM_BG_COLOR, stroke=color,
                    # 0.9pt @ 150dpi = 1.9px / 60px/u = 0.031u
                    stroke_width=0.03
                ))
                # font-size: 8.0pt @ 150dpi = 16.7px / 60px/u = 0.28u
                elems.append(_svg_text_block(
                    x_key, yc_svg, key_lines, 0.28, CMD_TEXT_COLOR
                ))

                # Testo descrizione (allineamento dipende dal lato)
                ta = "end" if side == "left" else "start"
                elems.append(_svg_text_block(
                    x_desc, yc_svg, desc_lines, 0.28, ITEM_LABEL_COLOR,
                    text_anchor=ta
                ))

                # Connettore cat → pill
                pill_edge_x = x_key + (OV_PILL_W/2 if side == "right" else -OV_PILL_W/2)
                cat_edge_x  = x_cat + (-OV_CAT_BOX_W/2 if side == "left" else OV_CAT_BOX_W/2)
                elems.append(_svg_line(
                    cat_edge_x, yc_svg,
                    pill_edge_x, yc_svg,
                    stroke_width=0.025, dash="0.15,0.08"
                ))

                y_cursor -= row_h

    # Titolo in alto a sinistra (va="top" in matplotlib → dominant-baseline="hanging" in SVG)
    # y matplotlib = fig_h - 0.25 = 19.75 → y SVG = H - 19.75 = 0.25
    title_str = _svg_escape(data["title"].replace("\n", " "))
    # font-size: 14pt @ 150dpi = 29.2px / 60px/u = 0.487u
    elems.append(
        f'<text x="0.5" y="0.35" dominant-baseline="hanging" '
        f'font-size="0.49" font-family="{FONT}" font-weight="bold" '
        f'fill="white">{title_str}</text>'
    )

    svg_body = "\n".join(elems)
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'style="width:100%;max-width:1800px;height:auto;display:block;margin:auto;">'
        f'\n{svg_body}\n</svg>'
    )

    page_title = data["title"].replace("\n", " ")
    html = _svg_html_page(page_title, svg)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  ✓ overview html: {output_path}")


# =============================================================================
# FOCUS — misuratori di altezza (condivisi matplotlib + HTML)
# =============================================================================

def _fo_item_h(key: str, desc: str) -> float:
    n = max(len(_wrap(key, FO_KEY_WRAP)), len(_wrap(desc, FO_DESC_WRAP)))
    return n * FO_LINE_H + FO_ROW_PAD


# =============================================================================
# FOCUS — disegno (matplotlib / PNG)
# =============================================================================

def render_focus(cat: dict, output_path: str, dpi: int = 100):
    IMG = 10.8
    fig, ax = plt.subplots(figsize=(IMG, IMG))
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(BG_COLOR)
    ax.set_xlim(0, FO_LIMIT)
    ax.set_ylim(0, FO_LIMIT)
    ax.axis("off")

    color = cat.get("color", "#555577")
    items = cat.get("items", [])
    name  = cat.get("name", "")

    total_items_h = sum(_fo_item_h(k, d) for k, d in items)
    available_h   = FO_LIMIT - 4.0
    scale = min(1.0, available_h / total_items_h) if total_items_h > 0 else 1.0

    cx_cat = 5.5
    cy_cat = FO_CENTER

    ax.add_patch(FancyBboxPatch(
        (cx_cat - FO_CAT_BOX_W/2, cy_cat - FO_CAT_BOX_H/2),
        FO_CAT_BOX_W, FO_CAT_BOX_H,
        boxstyle="round,pad=0.20",
        facecolor=color, edgecolor=_darken(color), linewidth=2.5, zorder=3
    ))
    ax.text(cx_cat, cy_cat, "\n".join(_wrap(name, 12)),
            ha="center", va="center",
            fontsize=26, color="white", fontweight="bold",
            fontfamily=FONT, zorder=4, linespacing=1.3)

    if not items:
        plt.savefig(output_path, dpi=dpi, facecolor=BG_COLOR)
        plt.close()
        return

    x_pill = cx_cat + FO_CAT_BOX_W/2 + 1.4  + FO_PILL_W/2
    x_desc = x_pill + FO_PILL_W/2    + 0.75 + FO_DESC_W/2

    y_cursor = cy_cat + (total_items_h * scale) / 2

    for key, desc in items:
        key_lines  = _wrap(key,  FO_KEY_WRAP)
        desc_lines = _wrap(desc, FO_DESC_WRAP)
        n_lines    = max(len(key_lines), len(desc_lines))
        row_h      = (n_lines * FO_LINE_H + FO_ROW_PAD) * scale
        yc         = y_cursor - row_h / 2

        pill_h = len(key_lines) * FO_LINE_H * scale + 0.45
        ax.add_patch(FancyBboxPatch(
            (x_pill - FO_PILL_W/2, yc - pill_h/2), FO_PILL_W, pill_h,
            boxstyle="round,pad=0.12",
            facecolor=ITEM_BG_COLOR, edgecolor=color, linewidth=1.8, zorder=3
        ))
        ax.text(x_pill, yc, "\n".join(key_lines),
                ha="center", va="center",
                fontsize=20, color=CMD_TEXT_COLOR, fontfamily=FONT, zorder=4, linespacing=1.2)

        desc_h = len(desc_lines) * FO_LINE_H * scale + 0.45
        ax.add_patch(FancyBboxPatch(
            (x_desc - FO_DESC_W/2, yc - desc_h/2), FO_DESC_W, desc_h,
            boxstyle="round,pad=0.12",
            facecolor=ITEM_BG_COLOR, edgecolor=_darken(color, 0.85),
            linewidth=1.0, zorder=3
        ))
        ax.text(x_desc, yc, "\n".join(desc_lines),
                ha="center", va="center",
                fontsize=17, color=ITEM_LABEL_COLOR, fontfamily=FONT, zorder=4, linespacing=1.2)

        _conn(ax, cx_cat + FO_CAT_BOX_W/2, yc, x_pill - FO_PILL_W/2, yc, lw=1.3)
        _conn(ax, x_pill + FO_PILL_W/2,    yc, x_desc - FO_DESC_W/2, yc, lw=1.0)

        y_cursor -= row_h

    plt.savefig(output_path, dpi=dpi, facecolor=BG_COLOR)
    plt.close()


# =============================================================================
# FOCUS — disegno HTML/SVG
#
# Stesso approccio di render_overview_html: replico la logica di render_focus()
# traducendo ogni primitiva matplotlib nel corrispondente elemento SVG.
#
# Conversione stroke-width per focus (100dpi, 36px per unità coordinate):
#   lw_svg = lw_pt * (100/72) / 36
# =============================================================================

def render_focus_html(cat: dict, output_path: str):
    """
    Genero il file HTML 1080×1080 per una singola categoria.
    Ho usato viewBox="0 0 30 30" (FO_LIMIT×FO_LIMIT) così tutte le costanti
    FO_* si applicano direttamente senza alcuna conversione di scala.
    """
    L = FO_LIMIT  # 30.0
    elems = []
    elems.append(f'<rect width="{L}" height="{L}" fill="{BG_COLOR}"/>')

    color = cat.get("color", "#555577")
    items = cat.get("items", [])
    name  = cat.get("name", "")

    total_items_h = sum(_fo_item_h(k, d) for k, d in items)
    available_h   = L - 4.0
    scale = min(1.0, available_h / total_items_h) if total_items_h > 0 else 1.0

    cx_cat = 5.5
    cy_cat = FO_CENTER  # 15.0

    # Cat box
    # FancyBboxPatch(bottom-left, w, h) → in SVG il top-left è flip(bottom-left + h)
    bx  = cx_cat - FO_CAT_BOX_W/2
    bym = cy_cat - FO_CAT_BOX_H/2
    elems.append(_svg_rect(
        bx,
        _svg_flip_y(bym + FO_CAT_BOX_H, L),
        FO_CAT_BOX_W, FO_CAT_BOX_H,
        rx=0.20,
        fill=color, stroke=_darken(color),
        # 2.5pt @ 100dpi = 3.47px / 36px/u = 0.096u
        stroke_width=0.10
    ))
    # font-size: 26pt @ 100dpi = 36.1px / 36px/u ≈ 1.0u
    elems.append(_svg_text_block(
        cx_cat, _svg_flip_y(cy_cat, L), _wrap(name, 12), 1.0, "white",
        font_weight="bold"
    ))

    if items:
        x_pill = cx_cat + FO_CAT_BOX_W/2 + 1.4 + FO_PILL_W/2
        x_desc = x_pill + FO_PILL_W/2 + 0.75 + FO_DESC_W/2

        y_cursor = cy_cat + (total_items_h * scale) / 2

        for key, desc in items:
            key_lines  = _wrap(key,  FO_KEY_WRAP)
            desc_lines = _wrap(desc, FO_DESC_WRAP)
            n_lines    = max(len(key_lines), len(desc_lines))
            row_h      = (n_lines * FO_LINE_H + FO_ROW_PAD) * scale
            yc         = y_cursor - row_h / 2
            yc_svg     = _svg_flip_y(yc, L)

            # Pill chiave
            pill_h = len(key_lines) * FO_LINE_H * scale + 0.45
            px  = x_pill - FO_PILL_W/2
            pym = yc - pill_h/2
            elems.append(_svg_rect(
                px,
                _svg_flip_y(pym + pill_h, L),
                FO_PILL_W, pill_h,
                rx=0.12,
                fill=ITEM_BG_COLOR, stroke=color,
                # 1.8pt @ 100dpi = 2.5px / 36px/u = 0.069u
                stroke_width=0.07
            ))
            # font-size: 20pt @ 100dpi = 27.8px / 36px/u = 0.77u
            elems.append(_svg_text_block(
                x_pill, yc_svg, key_lines, 0.77, CMD_TEXT_COLOR
            ))

            # Box descrizione
            desc_h = len(desc_lines) * FO_LINE_H * scale + 0.45
            dx  = x_desc - FO_DESC_W/2
            dym = yc - desc_h/2
            elems.append(_svg_rect(
                dx,
                _svg_flip_y(dym + desc_h, L),
                FO_DESC_W, desc_h,
                rx=0.12,
                fill=ITEM_BG_COLOR, stroke=_darken(color, 0.85),
                # 1.0pt @ 100dpi = 1.39px / 36px/u = 0.039u
                stroke_width=0.04
            ))
            # font-size: 17pt @ 100dpi = 23.6px / 36px/u = 0.66u
            elems.append(_svg_text_block(
                x_desc, yc_svg, desc_lines, 0.66, ITEM_LABEL_COLOR
            ))

            # Connettore cat → pill
            elems.append(_svg_line(
                cx_cat + FO_CAT_BOX_W/2, yc_svg,
                x_pill - FO_PILL_W/2,    yc_svg,
                stroke_width=0.05, dash="0.35,0.18"
            ))
            # Connettore pill → desc
            elems.append(_svg_line(
                x_pill + FO_PILL_W/2, yc_svg,
                x_desc - FO_DESC_W/2, yc_svg,
                stroke_width=0.04, dash="0.28,0.14"
            ))

            y_cursor -= row_h

    svg_body = "\n".join(elems)
    # Ho fissato width/height CSS a 1080px per replicare le proporzioni del PNG;
    # max-width:100% garantisce che non vada fuori schermo su mobile.
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {L} {L}" '
        f'style="width:1080px;height:1080px;max-width:100%;display:block;margin:auto;">'
        f'\n{svg_body}\n</svg>'
    )

    html = _svg_html_page(name, svg, body_style="align-items:center;")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)


# =============================================================================
# MAIN
# =============================================================================

def main():
    # Ho sostituito sys.argv con argparse per avere --help automatico,
    # validazione dei tipi e un'interfaccia estendibile per futuri parametri.
    parser = argparse.ArgumentParser(
        description="Genera mind map da un file JSON (PNG o HTML/SVG).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Esempi:\n"
            "  python mind_map_generator.py mappa.json\n"
            "  python mind_map_generator.py mappa.json --html"
        )
    )
    parser.add_argument(
        "input_file",
        help="File JSON di input"
    )
    parser.add_argument(
        "--html",
        action="store_true",
        help=(
            "Genera file HTML con SVG inline invece di immagini PNG. "
            "I file sono apribili direttamente nel browser, "
            "scalano a qualsiasi risoluzione e non richiedono matplotlib per essere visualizzati."
        )
    )
    args = parser.parse_args()

    input_file = args.input_file
    json_name  = os.path.splitext(os.path.basename(input_file))[0]

    # Ho costruito il percorso di output come _output/<nome_json>/
    out_dir = os.path.join("_output", json_name)
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir)

    with open(input_file, encoding="utf-8-sig") as f:
        data = json.load(f)

    mode = "HTML" if args.html else "PNG"
    print(f"🚀 Generazione {mode} in '{out_dir}/'")

    # 1. Mappa globale
    if args.html:
        render_overview_html(data, os.path.join(out_dir, "overview.html"))
    else:
        render_overview(data, os.path.join(out_dir, "overview.png"))

    # 2. Un file per ogni categoria (left + right in ordine)
    all_cats = data.get("left", []) + data.get("right", [])
    for i, cat in enumerate(all_cats, start=1):
        safe_name = cat["name"].lower().replace(" ", "_").replace("&", "e")
        if args.html:
            filename = f"{i:02d}_{safe_name}.html"
            out_path = os.path.join(out_dir, filename)
            render_focus_html(cat, out_path)
        else:
            filename = f"{i:02d}_{safe_name}.png"
            out_path = os.path.join(out_dir, filename)
            render_focus(cat, out_path)
        print(f"  ✓ focus {i:02d}: {cat['name']}")

    print(f"\n✨ Completato — {1 + len(all_cats)} file in '{out_dir}/'")


if __name__ == "__main__":
    main()