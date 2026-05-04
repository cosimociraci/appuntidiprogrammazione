#!/usr/bin/env python3
"""
mind_map_generator.py  v5.0

Output:
  _output/<nome_json>/overview.png|html        -- mappa globale
  _output/<nome_json>/<01_nome_cat>.png|html   -- una per categoria

Utilizzo:
  python mind_map_generator.py <file.json>          # PNG (richiede matplotlib)
  python mind_map_generator.py <file.json> --html   # HTML div/CSS puri
"""

import argparse
import os
import json
import textwrap
import shutil

# Ho isolato matplotlib in un try/except cosi --html funziona anche
# su macchine senza matplotlib installato.
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch, Circle
    _HAS_MPL = True
except ImportError:
    _HAS_MPL = False

# =============================================================================
# STILE
# =============================================================================
BG_COLOR         = "#12122a"
ITEM_BG_COLOR    = "#1a1a38"
ITEM_LABEL_COLOR = "#9999bb"
CMD_TEXT_COLOR   = "#ffffff"
CONN_COLOR       = "#3a3a6a"
FONT             = "DejaVu Sans"
FONT_CSS         = "'DejaVu Sans', 'Segoe UI', Arial, sans-serif"

# =============================================================================
# METRICHE OVERVIEW (sistema coordinate W=30, H=20 unita)
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
# METRICHE FOCUS (sistema coordinate W=H=FO_LIMIT=30 unita -> 36px/unita)
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
FO_CENTER    = FO_LIMIT / 2   # 15.0

# =============================================================================
# UTILITY CONDIVISE (usate da entrambe le pipeline PNG e HTML)
# =============================================================================

def _darken(hex_color: str, factor: float = 0.65) -> str:
    """Scurisco un colore hex per ricavare il colore bordo dei box."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"#{int(r*factor):02x}{int(g*factor):02x}{int(b*factor):02x}"


def _wrap(text: str, width: int) -> list:
    return textwrap.wrap(text, width=width) or [text]


def _ov_item_h(key: str, desc: str) -> float:
    """Altezza di un singolo item in unita coordinate."""
    n = max(len(_wrap(key, OV_KEY_WRAP)), len(_wrap(desc, OV_DESC_WRAP)))
    return n * OV_LINE_H + OV_ROW_PAD


def _ov_cat_h(cat: dict) -> float:
    """Altezza totale di tutti gli item di una categoria."""
    return sum(_ov_item_h(k, d) for k, d in cat.get("items", []))


def _ov_scale(categories: list, canvas_h: float) -> float:
    """
    Calcolo la scala verticale che fa stare tutte le categorie nel canvas.
    Se il contenuto supera l'altezza disponibile, comprimo proporzionalmente.
    """
    total  = sum(_ov_cat_h(c) for c in categories)
    total += OV_CAT_GAP * max(0, len(categories) - 1)
    return min(1.0, (canvas_h * 0.95) / total) if total > 0 else 1.0


def _ov_layout_tops(categories: list, canvas_cy: float, scale: float) -> list:
    """
    Calcolo i bordi superiori di ogni categoria centrando il blocco totale
    rispetto al centro verticale canvas_cy.
    """
    total_scaled = (
        sum(_ov_cat_h(c) for c in categories) * scale
        + OV_CAT_GAP * scale * max(0, len(categories) - 1)
    )
    y    = canvas_cy + total_scaled / 2
    tops = []
    for cat in categories:
        tops.append(y)
        y -= _ov_cat_h(cat) * scale + OV_CAT_GAP * scale
    return tops


def _fo_item_h(key: str, desc: str) -> float:
    n = max(len(_wrap(key, FO_KEY_WRAP)), len(_wrap(desc, FO_DESC_WRAP)))
    return n * FO_LINE_H + FO_ROW_PAD


# =============================================================================
# HTML HELPERS
# =============================================================================

def _he(s: str) -> str:
    """Eseguo l'escape dei caratteri speciali HTML per evitare injection."""
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;"))


def _html_page(title: str, css: str, body_inner: str) -> str:
    """
    Assemblo la pagina HTML con CSS dedicato passato come parametro.

    Ho separato il CSS dal body_inner per permettere a ogni funzione render
    di definire le proprie classi senza inquinare uno stile globale condiviso.
    Il body usa flex-col centrato; padding:40px da respiro ai canvas stretti.
    """
    return f"""<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_he(title)}</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: {BG_COLOR};
      font-family: {FONT_CSS};
      min-height: 100vh;
      padding: 40px 16px;
      display: flex;
      flex-direction: column;
      align-items: center;
      overflow: auto;
    }}
{css}
  </style>
</head>
<body>
{body_inner}
</body>
</html>"""


# =============================================================================
# OVERVIEW PNG (matplotlib -- invariato rispetto a v4.0)
# =============================================================================

def _conn_mpl(ax, x1, y1, x2, y2, lw=0.75):
    ax.plot([x1, x2], [y1, y2],
            color=CONN_COLOR, linewidth=lw, linestyle="--", zorder=1)


def _ov_center_node_mpl(ax, cx, cy, title):
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


def _ov_cat_box_mpl(ax, cx, cy, label, color):
    ax.add_patch(FancyBboxPatch(
        (cx - OV_CAT_BOX_W/2, cy - OV_CAT_BOX_H/2), OV_CAT_BOX_W, OV_CAT_BOX_H,
        boxstyle="round,pad=0.08",
        facecolor=color, edgecolor=_darken(color), linewidth=1.5, zorder=3
    ))
    ax.text(cx, cy, "\n".join(_wrap(label, 11)),
            ha="center", va="center", fontsize=9.5,
            color="white", fontweight="bold",
            zorder=4, fontfamily=FONT, linespacing=1.3)


def _ov_item_row_mpl(ax, y_top, key, desc, color,
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
            ha="center", va="center", fontsize=8.0,
            color=CMD_TEXT_COLOR, fontfamily=FONT, zorder=4, linespacing=1.2)

    ha = "right" if side == "left" else "left"
    ax.text(x_desc, yc, "\n".join(desc_lines),
            ha=ha, va="center", fontsize=8.0,
            color=ITEM_LABEL_COLOR, fontfamily=FONT, zorder=4, linespacing=1.2)

    pill_edge = x_key + (OV_PILL_W/2 if side == "right" else -OV_PILL_W/2)
    cat_edge  = x_cat + (-OV_CAT_BOX_W/2 if side == "left" else OV_CAT_BOX_W/2)
    _conn_mpl(ax, cat_edge, yc, pill_edge, yc)
    return row_h


def _ov_render_side_mpl(ax, categories, tops, scale, side, cx, cy):
    sign   = -1 if side == "left" else 1
    x_cat  = cx + sign * 5.5
    x_key  = cx + sign * 8.8
    x_desc = cx + sign * 11.0

    for cat, y_top in zip(categories, tops):
        color        = cat["color"]
        cat_h_scaled = _ov_cat_h(cat) * scale
        cat_cy       = y_top - cat_h_scaled / 2

        center_edge = cx + sign * OV_CENTER_R
        cat_edge    = x_cat + (-OV_CAT_BOX_W/2 if side == "right" else OV_CAT_BOX_W/2)
        _conn_mpl(ax, center_edge, cy, cat_edge, cat_cy)
        _ov_cat_box_mpl(ax, x_cat, cat_cy, cat["name"], color)

        y_cursor = y_top
        for key, desc in cat.get("items", []):
            consumed = _ov_item_row_mpl(
                ax, y_cursor, key, desc, color,
                side, x_cat, x_key, x_desc, scale)
            y_cursor -= consumed


def render_overview(data: dict, output_path: str, dpi: int = 150):
    """Genera la mappa globale come PNG."""
    if not _HAS_MPL:
        raise RuntimeError("matplotlib non disponibile -- usa --html")

    fig_w, fig_h = 30, 20
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(BG_COLOR)
    ax.set_xlim(0, fig_w)
    ax.set_ylim(0, fig_h)
    ax.axis("off")

    cx, cy   = fig_w / 2, fig_h / 2
    canvas_h = fig_h - 1.6
    left_cats  = data.get("left",  [])
    right_cats = data.get("right", [])
    scale = min(_ov_scale(left_cats, canvas_h), _ov_scale(right_cats, canvas_h))

    _ov_center_node_mpl(ax, cx, cy, data["title"])
    _ov_render_side_mpl(ax, left_cats,
                        _ov_layout_tops(left_cats,  cy, scale), scale, "left",  cx, cy)
    _ov_render_side_mpl(ax, right_cats,
                        _ov_layout_tops(right_cats, cy, scale), scale, "right", cx, cy)
    ax.text(0.5, fig_h - 0.25, data["title"].replace("\n", " "),
            fontsize=14, color="white", fontweight="bold",
            va="top", fontfamily=FONT)

    plt.savefig(output_path, dpi=dpi, bbox_inches="tight",
                facecolor=BG_COLOR, pad_inches=0.2)
    plt.close()
    print(f"  ✓ overview: {output_path}")


# =============================================================================
# FOCUS PNG (matplotlib -- invariato rispetto a v4.0)
# =============================================================================

def render_focus(cat: dict, output_path: str, dpi: int = 100):
    """Genera il PNG 1080x1080 per una singola categoria."""
    if not _HAS_MPL:
        raise RuntimeError("matplotlib non disponibile -- usa --html")

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
            ha="center", va="center", fontsize=26,
            color="white", fontweight="bold",
            fontfamily=FONT, zorder=4, linespacing=1.3)

    if not items:
        plt.savefig(output_path, dpi=dpi, facecolor=BG_COLOR)
        plt.close()
        return

    x_pill = cx_cat + FO_CAT_BOX_W/2 + 1.4 + FO_PILL_W/2
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
                ha="center", va="center", fontsize=20,
                color=CMD_TEXT_COLOR, fontfamily=FONT, zorder=4, linespacing=1.2)

        desc_h = len(desc_lines) * FO_LINE_H * scale + 0.45
        ax.add_patch(FancyBboxPatch(
            (x_desc - FO_DESC_W/2, yc - desc_h/2), FO_DESC_W, desc_h,
            boxstyle="round,pad=0.12",
            facecolor=ITEM_BG_COLOR, edgecolor=_darken(color, 0.85),
            linewidth=1.0, zorder=3
        ))
        ax.text(x_desc, yc, "\n".join(desc_lines),
                ha="center", va="center", fontsize=17,
                color=ITEM_LABEL_COLOR, fontfamily=FONT, zorder=4, linespacing=1.2)

        _conn_mpl(ax, cx_cat + FO_CAT_BOX_W/2, yc, x_pill - FO_PILL_W/2, yc, lw=1.3)
        _conn_mpl(ax, x_pill + FO_PILL_W/2,    yc, x_desc - FO_DESC_W/2, yc, lw=1.0)
        y_cursor -= row_h

    plt.savefig(output_path, dpi=dpi, facecolor=BG_COLOR)
    plt.close()


# =============================================================================
# OVERVIEW HTML (div/CSS - layout flexbox a tre colonne)
#
# Struttura DOM:
#   [titolo]
#   [pannello-sx] | [cerchio-centrale] | [pannello-dx]
#
# Ogni pannello e una colonna flex di cat-group.
# Ogni cat-group e una riga flex: [cat-box][items-col].
# Il pannello sinistro usa flex-direction:row-reverse via classe CSS
# in modo che cat-box rimanga visivamente adiacente al cerchio centrale
# senza duplicare il markup.
#
# Il connettore elastico (flex-grow:1) tra cat-box e pill occupa tutto
# lo spazio disponibile, simulando la linea del PNG senza calcoli in Python.
# L'altezza di ogni riga e determinata dal browser: nessun testo viene
# mai troncato da un'altezza stimata errata.
# =============================================================================

_OV_CSS = """
    .ov-title {
      color: white; font-weight: bold; font-size: 26px;
      text-align: center; margin-bottom: 28px; line-height: 1.4;
      width: 100%; max-width: 1600px;
    }
    .ov-layout {
      display: flex; align-items: center;
      justify-content: center; width: 100%;
      max-width: 1600px; gap: 0;
    }
    .ov-panel {
      flex: 1; display: flex; flex-direction: column;
      gap: 20px; min-width: 0;
    }
    .ov-center {
      width: 180px; height: 180px; flex-shrink: 0;
      border-radius: 50%;
      background: #1e1e4a; border: 3px solid #7777ff;
      display: flex; align-items: center; justify-content: center;
      margin: 0 10px;
    }
    /* cat-group: cat-box + items-col in riga */
    .ov-cat-group {
      display: flex; align-items: center;
    }
    /* Il pannello sinistro specchia l'ordine visivo con row-reverse.
       cat-box finisce a destra (vicino al cerchio), desc a sinistra.
       Il DOM rimane identico per entrambi i lati. */
    .ov-left .ov-cat-group { flex-direction: row-reverse; }
    .ov-left .ov-item-row  { flex-direction: row-reverse; }
    .ov-left .ov-desc      { text-align: right; }
    .ov-cat-box {
      width: 180px; flex-shrink: 0;
      padding: 12px 10px; border-radius: 6px;
      font-size: 19px; font-weight: bold; color: white;
      text-align: center; line-height: 1.3;
    }
    .ov-items-col {
      flex: 1; display: flex; flex-direction: column;
      gap: 6px; min-width: 0;
    }
    .ov-item-row { display: flex; align-items: center; }
    /* Connettore elastico: cresce per colmare lo spazio tra pill e cat-box */
    .ov-conn {
      flex-grow: 1; height: 0;
      border-top: 1px dashed #3a3a6a;
      margin: 0 6px; min-width: 8px;
    }
    .ov-pill {
      width: 140px; flex-shrink: 0;
      padding: 7px 8px; border-radius: 5px;
      font-size: 16px; color: white;
      text-align: center; line-height: 1.25;
      background: #1a1a38;
    }
    /* Connettore corto fisso tra pill e desc */
    .ov-conn-short {
      width: 26px; flex-shrink: 0; height: 0;
      border-top: 1px dashed #3a3a6a; margin: 0 3px;
    }
    /* min-width:0 e cruciale: senza di esso flex ignora il testo lungo
       e il pannello sfora il viewport invece di andare a capo. */
    .ov-desc {
      flex: 1; min-width: 0;
      font-size: 16px; color: #9999bb;
      line-height: 1.3; padding: 3px 2px;
    }
"""


def render_overview_html(data: dict, output_path: str):
    """
    Genera la mappa globale come HTML con layout flexbox a tre colonne.

    Ho abbandonato position:absolute perche richiedeva di calcolare in Python
    le dimensioni di ogni box prima che il browser potesse renderizzarlo,
    portando a troncature quando il testo eccedeva l'altezza stimata.
    Con flexbox l'altezza di ogni riga e determinata dal browser sul contenuto
    reale: nessun calcolo di coordinate, nessun clip garantito.
    """

    def _render_panel(cats: list, side: str) -> str:
        """
        Costruisco il markup per un pannello laterale.
        La classe ov-left attiva i selettori CSS che specchiano
        visivamente il pannello sinistro senza toccare il DOM.
        """
        side_cls = "ov-left" if side == "left" else ""
        groups   = []

        for cat in cats:
            color  = cat["color"]
            border = _darken(color)

            cat_label = "<br>".join(_he(l) for l in _wrap(cat["name"], 11))
            cat_box   = (
                f'<div class="ov-cat-box" '
                f'style="background:{color};border:1.5px solid {border};">'
                f'{cat_label}</div>'
            )

            rows = []
            for key, desc in cat.get("items", []):
                key_html  = "<br>".join(_he(l) for l in _wrap(key,  OV_KEY_WRAP))
                desc_html = "<br>".join(_he(l) for l in _wrap(desc, OV_DESC_WRAP))
                pill = (
                    f'<div class="ov-pill" '
                    f'style="border:0.9px solid {color};">'
                    f'{key_html}</div>'
                )
                rows.append(
                    f'<div class="ov-item-row">'
                    f'<div class="ov-conn"></div>'
                    f'{pill}'
                    f'<div class="ov-conn-short"></div>'
                    f'<div class="ov-desc">{desc_html}</div>'
                    f'</div>'
                )

            items_col = (
                f'<div class="ov-items-col">'
                + "\n".join(rows)
                + '</div>'
            )
            groups.append(
                f'<div class="ov-cat-group">{cat_box}{items_col}</div>'
            )

        return (
            f'<div class="ov-panel {side_cls}">'
            + "\n".join(groups)
            + '</div>'
        )

    title      = data["title"]
    left_cats  = data.get("left",  [])
    right_cats = data.get("right", [])

    title_lines = "<br>".join(_he(l) for l in title.split("\n"))
    center = (
        f'<div class="ov-center">'
        f'<span style="color:white;font-weight:bold;font-size:21px;'
        f'text-align:center;line-height:1.35;">{title_lines}</span>'
        f'</div>'
    )
    title_div = (
        f'<div class="ov-title">'
        f'{_he(title.replace(chr(10), " "))}'
        f'</div>'
    )
    layout = (
        f'<div class="ov-layout">'
        + _render_panel(left_cats, "left")
        + center
        + _render_panel(right_cats, "right")
        + '</div>'
    )

    page = _html_page(title.replace("\n", " "), _OV_CSS, title_div + "\n" + layout)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"  ✓ overview html: {output_path}")


# =============================================================================
# FOCUS HTML (div/CSS - layout flexbox a righe)
#
# Struttura DOM per ogni pagina categoria:
#   [wrapper-centrato]
#     [cat-box] (fisso a sinistra, centrato verticalmente)
#     [items-col] (colonna di item-row, cresce a destra)
#       [item-row]: [conn][pill][conn-short][desc-box]
#
# Il wrapper usa display:flex align-items:center cosi cat-box e items-col
# sono allineati al centro verticale indipendentemente dall'altezza.
# Ogni item-row usa align-items:center: pill e desc-box si allineano
# al centro reciprocamente anche quando hanno altezze diverse.
# Nessuna coordinata calcolata in Python, nessun overflow:hidden.
# =============================================================================

_FO_CSS = """
    .fo-wrap {
      display: flex; align-items: center;
      width: 100%; max-width: 1080px;
      gap: 0; padding: 20px 0;
    }
    .fo-cat-box {
      width: 220px; flex-shrink: 0;
      padding: 20px 14px; border-radius: 8px;
      font-size: 32px; font-weight: bold; color: white;
      text-align: center; line-height: 1.3;
    }
    .fo-items-col {
      flex: 1; display: flex; flex-direction: column;
      gap: 12px; min-width: 0;
    }
    .fo-item-row { display: flex; align-items: center; }
    .fo-conn {
      width: 40px; flex-shrink: 0; height: 0;
      border-top: 1.8px dashed #3a3a6a; margin: 0 4px;
    }
    .fo-pill {
      width: 200px; flex-shrink: 0;
      padding: 10px 10px; border-radius: 5px;
      font-size: 22px; color: white;
      text-align: center; line-height: 1.25;
      background: #1a1a38;
    }
    .fo-conn-short {
      width: 26px; flex-shrink: 0; height: 0;
      border-top: 1.3px dashed #3a3a6a; margin: 0 4px;
    }
    /* min-width:0 impedisce al testo lungo di allargare il flex container */
    .fo-desc {
      flex: 1; min-width: 0;
      padding: 10px 10px; border-radius: 5px;
      font-size: 20px; color: #9999bb;
      line-height: 1.3; background: #1a1a38;
    }
"""


def render_focus_html(cat: dict, output_path: str):
    """
    Genera il file HTML per una singola categoria con layout flexbox.

    La struttura e identica al reference HTML fornito: una riga flex per
    ogni item con [conn][pill][conn-short][desc]. Il cat-box e affiancato
    a sinistra dell'intera colonna di item tramite il wrapper flex esterno.
    L'altezza di ogni box e decisa dal browser, mai da Python.
    """
    color = cat.get("color", "#555577")
    items = cat.get("items", [])
    name  = cat.get("name", "")
    border = _darken(color)

    # Cat box
    name_html = "<br>".join(_he(l) for l in _wrap(name, 10))
    cat_box   = (
        f'<div class="fo-cat-box" '
        f'style="background:{color};border:2.5px solid {border};">'
        f'{name_html}</div>'
    )

    # Item rows
    rows = []
    for key, desc in items:
        key_html  = "<br>".join(_he(l) for l in _wrap(key,  FO_KEY_WRAP))
        desc_html = "<br>".join(_he(l) for l in _wrap(desc, FO_DESC_WRAP))
        desc_border = _darken(color, 0.85)
        pill = (
            f'<div class="fo-pill" '
            f'style="border:1.8px solid {color};">'
            f'{key_html}</div>'
        )
        desc_box = (
            f'<div class="fo-desc" '
            f'style="border:1px solid {desc_border};">'
            f'{desc_html}</div>'
        )
        rows.append(
            f'<div class="fo-item-row">'
            f'<div class="fo-conn"></div>'
            f'{pill}'
            f'<div class="fo-conn-short"></div>'
            f'{desc_box}'
            f'</div>'
        )

    items_col = (
        '<div class="fo-items-col">'
        + "\n".join(rows)
        + '</div>'
    )
    wrap = (
        f'<div class="fo-wrap">'
        f'{cat_box}'
        f'{items_col}'
        f'</div>'
    )

    page = _html_page(name, _FO_CSS, wrap)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(page)


# =============================================================================
# MAIN
# =============================================================================

def main():
    # Ho sostituito sys.argv manuale con argparse per avere --help automatico,
    # validazione dei tipi e un'interfaccia facilmente estendibile.
    parser = argparse.ArgumentParser(
        description="Genera mind map da un file JSON (PNG o HTML).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Esempi:\n"
            "  python mind_map_generator.py mappa.json\n"
            "  python mind_map_generator.py mappa.json --html"
        )
    )
    parser.add_argument("input_file", help="File JSON di input")
    parser.add_argument(
        "--html",
        action="store_true",
        help=(
            "Genera HTML (div/CSS) invece di PNG. "
            "Non richiede matplotlib, apribile direttamente nel browser."
        )
    )
    args = parser.parse_args()

    if not args.html and not _HAS_MPL:
        print("ERRORE: matplotlib non installato. "
              "Usa --html oppure: pip install matplotlib")
        raise SystemExit(1)

    json_name = os.path.splitext(os.path.basename(args.input_file))[0]
    out_dir   = os.path.join("_output", json_name)
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir)

    with open(args.input_file, encoding="utf-8-sig") as f:
        data = json.load(f)

    mode = "HTML" if args.html else "PNG"
    print(f"Generazione {mode} in '{out_dir}/'")

    if args.html:
        render_overview_html(data, os.path.join(out_dir, "overview.html"))
    else:
        render_overview(data,      os.path.join(out_dir, "overview.png"))

    all_cats = data.get("left", []) + data.get("right", [])
    for i, cat in enumerate(all_cats, start=1):
        safe_name = cat["name"].lower().replace(" ", "_").replace("&", "e")
        if args.html:
            out_path = os.path.join(out_dir, f"{i:02d}_{safe_name}.html")
            render_focus_html(cat, out_path)
        else:
            out_path = os.path.join(out_dir, f"{i:02d}_{safe_name}.png")
            render_focus(cat, out_path)
        print(f"  ✓ focus {i:02d}: {cat['name']}")

    print(f"\nCompletato -- {1 + len(all_cats)} file in '{out_dir}/'")


if __name__ == "__main__":
    main()