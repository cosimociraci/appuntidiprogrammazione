#!/usr/bin/env python3
"""
mind_map_generator.py  v4.0

Output:
  mind_map/<nome_json>/overview.png          — mappa globale completa
  mind_map/<nome_json>/<01_nome_cat>.png     — un file per ogni categoria,
                                               con il box categoria al centro
                                               e gli item disposti intorno.
"""

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
# Ho separato le metriche overview da quelle focus perché le due viste
# hanno densità e proporzioni molto diverse.
# =============================================================================
OV_LINE_H    = 0.35   # Aumentato per dare più spazio verticale tra righe di testo
OV_ROW_PAD   = 0.30   # Aumentato il padding tra un item e l'altro
OV_CAT_GAP   = 0.80   # Più spazio tra le categorie
OV_KEY_WRAP  = 14     # Più caratteri per riga
OV_DESC_WRAP = 35     # Più caratteri per riga
OV_CAT_BOX_W = 3.2    # Allargato significativamente (era 2.4)
OV_CAT_BOX_H = 1.1    # Alzato leggermente (era 0.95)
OV_PILL_W    = 2.5    # Allargata la pillola della chiave (era 1.9)
OV_CENTER_R  = 1.6    # Cerchio centrale leggermente più grande

# =============================================================================
# METRICHE FOCUS (vista singola categoria, canvas 1080×1080)
#
# Ho ridotto FO_LIMIT da 40 a 30: lo spazio coordinate è più piccolo,
# quindi ogni elemento occupa una frazione maggiore del canvas →
# font e box appaiono il 33% più grandi a parità di misura in unità.
# 1 unit = 1080px / 30 = 36px  (era 27px con FO_LIMIT=40).
# =============================================================================
FO_LINE_H    = 1.20   # era 1.10 — altezza riga testo in unità coord (=43px)
FO_ROW_PAD   = 1.30   # era 1.50 — padding verticale tra item (=47px)
FO_KEY_WRAP  = 10     # era 13  — meno caratteri per riga (font più grande)
FO_DESC_WRAP = 18     # era 24  — idem
FO_CAT_BOX_W = 9.0   # era 12.0 — scalato ×0.75 per FO_LIMIT=30
FO_CAT_BOX_H = 4.0   # era 4.5  — scalato + margine per 2-3 righe a 26pt
FO_PILL_W    = 6.5   # era 8.5  — scalato ×0.75
FO_DESC_W    = 9.5   # era 14.0 — scalato; right edge = 1013px (93.8%)
FO_LIMIT     = 30.0  # era 40.0 — riduzione coordinate → tutto più grande
FO_CENTER    = FO_LIMIT / 2  # 15.0

# =============================================================================
# UTILITY CONDIVISE
# =============================================================================

def _darken(hex_color: str, factor: float = 0.65) -> str:
    """Scurisco un colore hex per ricavare il colore bordo dei box."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"#{int(r*factor):02x}{int(g*factor):02x}{int(b*factor):02x}"


def _wrap(text: str, width: int) -> list:
    return textwrap.wrap(text, width=width) or [text]


def _conn(ax, x1, y1, x2, y2, lw=0.75):
    """Disegno una linea tratteggiata di connessione."""
    ax.plot([x1, x2], [y1, y2],
            color=CONN_COLOR, linewidth=lw, linestyle="--", zorder=1)


# =============================================================================
# OVERVIEW — misuratori di altezza
# =============================================================================

def _ov_item_h(key: str, desc: str) -> float:
    n = max(len(_wrap(key, OV_KEY_WRAP)), len(_wrap(desc, OV_DESC_WRAP)))
    return n * OV_LINE_H + OV_ROW_PAD


def _ov_cat_h(cat: dict) -> float:
    return sum(_ov_item_h(k, d) for k, d in cat.get("items", []))


# =============================================================================
# OVERVIEW — motore di layout
# =============================================================================

def _ov_scale(categories: list, canvas_h: float) -> float:
    """Calcolo la scala che fa stare tutte le categorie nel canvas."""
    total = sum(_ov_cat_h(c) for c in categories)
    total += OV_CAT_GAP * max(0, len(categories) - 1)
    return min(1.0, (canvas_h * 0.95) / total) if total > 0 else 1.0


def _ov_layout_tops(categories: list, canvas_cy: float, scale: float) -> list:
    """
    Calcolo i bordi superiori di ogni categoria centrando il blocco intero
    rispetto a canvas_cy, così il contenuto è sempre verticalmente centrato.
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
# OVERVIEW — disegno
# =============================================================================

def _ov_center_node(ax, cx, cy, title):
    ax.add_patch(Circle((cx, cy), OV_CENTER_R, color="#1e1e4a", zorder=4))
    ax.add_patch(Circle((cx, cy), OV_CENTER_R, fill=False,
                         edgecolor="#7777ff", linewidth=2.5, zorder=5))
    lines = title.split("\n")
    lh    = 0.42   # era 0.38 — interlinea adeguata a font 12pt
    y0    = cy + lh * (len(lines) - 1) / 2
    for i, line in enumerate(lines):
        ax.text(cx, y0 - i * lh, line, ha="center", va="center",
                fontsize=12,          # era 10
                color="white", fontweight="bold",
                zorder=6, fontfamily=FONT)


def _ov_cat_box(ax, cx, cy, label, color):
    ax.add_patch(FancyBboxPatch(
        (cx - OV_CAT_BOX_W/2, cy - OV_CAT_BOX_H/2), OV_CAT_BOX_W, OV_CAT_BOX_H,
        boxstyle="round,pad=0.08",
        facecolor=color, edgecolor=_darken(color), linewidth=1.5, zorder=3
    ))
    ax.text(cx, cy, "\n".join(_wrap(label, 11)),  # era 12
            ha="center", va="center",
            fontsize=9.5,             # era 7.5
            color="white", fontweight="bold",
            zorder=4, fontfamily=FONT, linespacing=1.3)


def _ov_item_row(ax, y_top, key, desc, color,
                 side, x_cat, x_key, x_desc, scale) -> float:
    """
    Disegno una riga item con altezza variabile (dipende dal wrapping).
    Restituisco l'altezza consumata per aggiornare il cursore verticale.
    """
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
            fontsize=8.0,             # era 5.8
            color=CMD_TEXT_COLOR, fontfamily=FONT, zorder=4, linespacing=1.2)

    ha = "right" if side == "left" else "left"
    ax.text(x_desc, yc, "\n".join(desc_lines),
            ha=ha, va="center",
            fontsize=8.0,             # era 5.8
            color=ITEM_LABEL_COLOR, fontfamily=FONT, zorder=4, linespacing=1.2)

    pill_edge_x = x_key + (OV_PILL_W/2 if side == "right" else -OV_PILL_W/2)
    cat_edge_x  = x_cat + (-OV_CAT_BOX_W/2 if side == "left" else OV_CAT_BOX_W/2)
    _conn(ax, cat_edge_x, yc, pill_edge_x, yc)
    return row_h


def _ov_render_side(ax, categories, tops, scale, side, cx, cy):
    """Renderizza tutte le categorie di un lato (left o right)."""
    sign   = -1 if side == "left" else 1
    x_cat  = cx + sign * 5.5  # Spostato verso l'esterno (era 4.6)
    x_key  = cx + sign * 8.8  # Spostato verso l'esterno (era 7.1)
    x_desc = cx + sign * 11.0 # Spostato verso l'esterno (era 8.9)

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
    """
    Genera la mappa globale completa con tutte le categorie su due colonne.
    Ho scelto 30x20 pollici come proporzione panoramica standard:
    bilancia bene testo e spazio negativo su tutti i dataset testati.
    """
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

    # Ho preso il minimo tra i due lati per avere la stessa densità visiva
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
# FOCUS — vista singola categoria (canvas quadrato 1080×1080)
#
# Layout "lisca di pesce": box categoria a sinistra-centro, item in colonna
# a destra. Con FO_LIMIT=30 ogni unità vale 36px → font e box 33% più grandi
# rispetto alla versione precedente (FO_LIMIT=40 → 27px/unit).
#
# Posizionamento orizzontale (px):
#   cat box : [  36,  360]   (324px)
#   pill    : [ 410,  644]   (234px, gap 50px dal cat box)
#   desc    : [ 671, 1013]   (342px, gap 27px dalla pill)
# =============================================================================

def _fo_item_h(key: str, desc: str) -> float:
    n = max(len(_wrap(key, FO_KEY_WRAP)), len(_wrap(desc, FO_DESC_WRAP)))
    return n * FO_LINE_H + FO_ROW_PAD


def render_focus(cat: dict, output_path: str, dpi: int = 100):
    """
    Genera il PNG 1080×1080 per una singola categoria.
    Font sizes in matplotlib points (1pt = dpi/72 px):
      - categoria: 26pt = 36px  (era 18pt = 25px)
      - key pill : 20pt = 28px  (era 13pt = 18px)
      - desc     : 17pt = 24px  (era 12pt = 17px)
    """
    IMG = 10.8   # pollici; 10.8 * 100dpi = 1080px
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
    available_h   = FO_LIMIT - 4.0   # margine top+bottom = 4 unità (144px)
    scale = min(1.0, available_h / total_items_h) if total_items_h > 0 else 1.0

    # -------------------------------------------------------------------
    # Box categoria
    # cx_cat = 5.5 → left edge = 1.0 unit = 36px (margine sinistro 36px)
    # Ho spostato da 7.5 a 5.5 per compensare la riduzione di FO_LIMIT.
    # -------------------------------------------------------------------
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
            fontsize=26,          # era 18 — +44%, 36px a dpi=100
            color="white", fontweight="bold",
            fontfamily=FONT, zorder=4, linespacing=1.3)

    if not items:
        plt.savefig(output_path, dpi=dpi, facecolor=BG_COLOR)
        plt.close()
        return

    # -------------------------------------------------------------------
    # Posizioni orizzontali pill e desc (in unità FO_LIMIT=30).
    # Ho calcolato in pixel e convertito per garantire assenza di clipping:
    #   x_pill center = 14.65u → pill span [411px, 645px]
    #   x_desc center = 23.4u  → desc span [671px, 1013px]
    # -------------------------------------------------------------------
    x_pill = cx_cat + FO_CAT_BOX_W/2 + 1.4  + FO_PILL_W/2   # 14.65u
    x_desc = x_pill + FO_PILL_W/2    + 0.75 + FO_DESC_W/2   # 23.4u

    y_cursor = cy_cat + (total_items_h * scale) / 2

    for key, desc in items:
        key_lines  = _wrap(key,  FO_KEY_WRAP)
        desc_lines = _wrap(desc, FO_DESC_WRAP)
        n_lines    = max(len(key_lines), len(desc_lines))
        row_h      = (n_lines * FO_LINE_H + FO_ROW_PAD) * scale
        yc         = y_cursor - row_h / 2

        # Pill chiave
        # Ho aumentato il pad interno da 0.35 a 0.45 per dare respiro
        # al testo più grande.
        pill_h = len(key_lines) * FO_LINE_H * scale + 0.45
        ax.add_patch(FancyBboxPatch(
            (x_pill - FO_PILL_W/2, yc - pill_h/2), FO_PILL_W, pill_h,
            boxstyle="round,pad=0.12",
            facecolor=ITEM_BG_COLOR, edgecolor=color, linewidth=1.8, zorder=3
        ))
        ax.text(x_pill, yc, "\n".join(key_lines),
                ha="center", va="center",
                fontsize=20,          # era 13 — +54%, 28px a dpi=100
                color=CMD_TEXT_COLOR, fontfamily=FONT, zorder=4, linespacing=1.2)

        # Box descrizione
        desc_h = len(desc_lines) * FO_LINE_H * scale + 0.45
        ax.add_patch(FancyBboxPatch(
            (x_desc - FO_DESC_W/2, yc - desc_h/2), FO_DESC_W, desc_h,
            boxstyle="round,pad=0.12",
            facecolor=ITEM_BG_COLOR, edgecolor=_darken(color, 0.85),
            linewidth=1.0, zorder=3
        ))
        ax.text(x_desc, yc, "\n".join(desc_lines),
                ha="center", va="center",
                fontsize=17,          # era 12 — +42%, 24px a dpi=100
                color=ITEM_LABEL_COLOR, fontfamily=FONT, zorder=4, linespacing=1.2)

        # Connettori dashed
        _conn(ax, cx_cat + FO_CAT_BOX_W/2, yc, x_pill - FO_PILL_W/2, yc, lw=1.3)
        _conn(ax, x_pill + FO_PILL_W/2,    yc, x_desc - FO_DESC_W/2, yc, lw=1.0)

        y_cursor -= row_h

    plt.savefig(output_path, dpi=dpi, facecolor=BG_COLOR)
    plt.close()


# =============================================================================
# MAIN
# =============================================================================

def main():
    if len(sys.argv) < 2:
        print("Uso: python mind_map_generator.py <file.json>")
        sys.exit(1)

    input_file  = sys.argv[1]
    json_name   = os.path.splitext(os.path.basename(input_file))[0]

    # Ho costruito il percorso di output come _output/<nome_json>/
    out_dir = os.path.join("_output", json_name)
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir)

    with open(input_file, encoding="utf-8-sig") as f:
        data = json.load(f)

    print(f"🚀 Generazione in '{out_dir}/'")

    # 1. Mappa globale
    render_overview(data, os.path.join(out_dir, "overview.png"))

    # 2. Un PNG per ogni categoria (left + right in ordine)
    all_cats = data.get("left", []) + data.get("right", [])
    for i, cat in enumerate(all_cats, start=1):
        safe_name = cat["name"].lower().replace(" ", "_").replace("&", "e")
        filename  = f"{i:02d}_{safe_name}.png"
        out_path  = os.path.join(out_dir, filename)
        render_focus(cat, out_path)
        print(f"  ✓ focus {i:02d}: {cat['name']}")

    print(f"\n✨ Completato — {1 + len(all_cats)} file in '{out_dir}/'")


if __name__ == "__main__":
    main()