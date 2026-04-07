import os
import sys
import re
import asyncio
import argparse
import html
import textwrap
import pandas as pd
from pathlib import Path
from playwright.async_api import async_playwright

# --- LOGICA DI IMPORTAZIONE DALLA CARTELLA SUPERIORE ---
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

try:
    import code_formatter as cf
except ImportError:
    print(f"❌ Errore: code_formatter.py non trovato in {parent_dir}")
    sys.exit(1)

# --- CONFIGURAZIONE TECNOLOGICA ---
TECH_CONFIG = {
    "java": {"color": "#f89820"},
    "js": {"color": "#f7df1e"},
    "db": {"color": "#336791"},
    "thymeleaf": {"color": "#005f00"},
    "default": {"color": "#FF4081"}
}

SQUARE_SIZE = 1080 
MAX_CHARS_WIDTH = 65
MAX_CODE_LINES_PER_SLIDE = 20
MAX_TOTAL_SLIDES = 15

def highlight_code(code_html):
    """Evidenzia le parole chiave avvolgendole in uno span arancione."""
    # Lista estesa di keyword per i vari linguaggi supportati
    keywords = [
        "public", "private", "protected", "class", "interface", "extends", "implements",
        "static", "final", "void", "return", "new", "if", "else", "for", "while", "do",
        "switch", "case", "break", "continue", "try", "catch", "finally", "throw", "throws",
        "package", "import", "instanceof", "volatile", "transient", "synchronized",
        "SELECT", "FROM", "WHERE", "INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER",
        "TABLE", "INTO", "VALUES", "SET", "JOIN", "ON", "GROUP", "BY", "ORDER", "HAVING",
        "const", "let", "var", "function", "async", "await", "export", "default"
    ]
    
    # Regex per trovare le keyword come parole intere (case insensitive per SQL)
    pattern = r'\b(' + '|'.join(keywords) + r')\b'
    
    # Sostituiamo le keyword con lo span colorato. 
    # Nota: usiamo una funzione di replace per gestire il case originale
    def replacer(match):
        return f'<span class="keyword">{match.group(0)}</span>'
    
    return re.sub(pattern, replacer, code_html, flags=re.IGNORECASE)

def format_code(code_text, tech):
    """Utilizza code_formatter.py con pre-correzione e wrapping logico."""
    if not code_text or str(code_text).strip() == 'nan':
        return ""

    code = str(code_text).replace("\\n", "\n").replace("\r", "").strip()
    
    # 1. Pulizia strutturale pre-formattazione
    code = re.sub(r'\s+;', ';', code)
    code = re.sub(r'\*/(?!\n)', '*/\n', code)

    lang = "db" if tech.lower() == "db" else tech.lower()
    
    try:
        lines = cf.normalize_to_lines(code, lang)
        indented_lines = cf.indent_lines(lines, lang)
        
        final_lines = []
        for line in indented_lines:
            clean_line = line.rstrip()
            if not clean_line: continue
                
            if len(clean_line) <= MAX_CHARS_WIDTH:
                final_lines.append(clean_line)
            else:
                indent_match = re.match(r"^\s*", clean_line)
                indent = indent_match.group(0) if indent_match else ""
                wrapped = textwrap.fill(
                    clean_line,
                    width=MAX_CHARS_WIDTH,
                    subsequent_indent=indent + "    ",
                    expand_tabs=False,
                    replace_whitespace=False,
                    drop_whitespace=False
                )
                final_lines.append(wrapped)
        return "\n".join(final_lines)
    except Exception as e:
        print(f"⚠️ Errore nel formattatore: {e}")
        return code

def process_text_formatting(text):
    if pd.isna(text): return ""
    text = str(text).replace("\\n", "\n")
    lines = text.splitlines()
    processed_lines = []
    in_list = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('*'):
            if not in_list:
                processed_lines.append('<ul style="margin: 10px 0; padding-left: 20px;">')
                in_list = True
            processed_lines.append(f'<li style="margin-bottom: 8px;">{html.escape(stripped[1:].strip())}</li>')
        else:
            if in_list:
                processed_lines.append('</ul>')
                in_list = False
            processed_lines.append(html.escape(line) + "<br>")
    if in_list: processed_lines.append('</ul>')
    return "".join(processed_lines)

def get_css(color, is_insta=False):
    w, h = (SQUARE_SIZE, SQUARE_SIZE) if is_insta else (1920, 1080)
    fs_body = "28px" if is_insta else "22px"
    fs_code = "18px" if is_insta else "19px"  # Font leggermente più piccolo
    padding_slide = "60px 50px" if is_insta else "70px" # Padding verticale ridotto

    return f"""
    @import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500&family=Montserrat:wght@700;900&family=Poppins:wght@300;400;600&display=swap');
    :root {{ --tech-accent: {color}; --neon-green: #4AF626; --keyword-color: #FF9800; }}
    body {{ margin: 0; background: #000; color: white; font-family: 'Poppins', sans-serif; overflow: hidden; }}
    .slide {{ 
        width: {w}px; 
        height: {h}px; 
        padding: {padding_slide}; 
        box-sizing: border-box; 
        display: flex; 
        flex-direction: column; 
        position: relative; 
        background: #0a0a0a; 
    }}
    .header {{ 
        border-left: 10px solid var(--tech-accent); 
        padding-left: 20px; 
        margin-bottom: 20px; # Margine ridotto
    }}
    .code-container {{ 
        background: #121212; 
        padding: 25px; # Padding interno ridotto
        border-radius: 6px; 
        border: 1px solid #222; 
        flex-grow: 1; 
        overflow: hidden; 
        display: flex; # Centra il codice verticalmente se poco
        flex-direction: column;
    }}
    pre {{ 
        font-family: 'Fira Code', monospace; 
        font-size: {fs_code}; 
        line-height: 1.4; # Interlinea più compatta
        margin: 0; 
        white-space: pre-wrap; 
    }}
    .keyword {{ color: var(--keyword-color); font-weight: 500; }}
    .footer-page {{ position: absolute; bottom: 30px; right: 60px; font-size: 18px; color: #333; font-weight: 900; }}
    .cta-debug {{ justify-content: center; font-family: 'Fira Code', monospace; padding: 100px; }}
    .console-title {{ font-family: 'Montserrat'; font-weight: 900; font-size: 45px; color: white; margin-bottom: 60px; text-transform: uppercase; text-align: center; }}
    .console-line {{ font-size: 32px; margin-bottom: 25px; }}
    .console-prompt {{ color: white; opacity: 0.5; margin-right: 15px; }}
    .console-val-green {{ color: var(--neon-green); }}
    .console-val-accent {{ color: var(--tech-accent); }}
    .cursor {{ display: inline-block; width: 15px; height: 35px; background: white; animation: blink 1s infinite; vertical-align: middle; }}
    @keyframes blink {{ 50% {{ opacity: 0; }} }}
    .cta-footer {{ position: absolute; bottom: 50px; width: 100%; left: 0; text-align: center; font-size: 20px; color: #444; }}
    """

async def run_gen(selected_techs, output_format):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        is_insta = (output_format == "insta")
        w, h = (SQUARE_SIZE, SQUARE_SIZE) if is_insta else (1920, 1080)
        page = await browser.new_page(viewport={'width': w, 'height': h})

        for tech in selected_techs:
            file_path = f"{tech}.xlsx"
            if not os.path.exists(file_path): 
                print(f"⚠️ Saltato: {file_path} non trovato.")
                continue
                
            cfg = TECH_CONFIG.get(tech.lower(), TECH_CONFIG["default"])
            xls = pd.ExcelFile(file_path)
            
            for sheet_name in xls.sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                df.columns = [str(c).strip().upper() for c in df.columns]
                sheet_slug = re.sub(r'[^a-zA-Z0-9]+', '_', sheet_name)

                for idx, row in df.iterrows():
                    code_parts = [str(row.get(col)) for col in df.columns if 'ESEMPIO' in col and pd.notna(row.get(col))]
                    full_code = format_code("\n".join(code_parts), tech)
                    
                    titolo = str(row.get('TITOLO', f'Topic {idx+1}')).replace('_', ' ')
                    topic_slug = re.sub(r'[^a-zA-Z0-9]+', '_', titolo)
                    pdf_filename = re.sub(r'[^a-zA-Z0-9]+', '-', titolo).lower()

                    out_dir = Path(f"output/{tech}/{sheet_slug}") / (topic_slug if is_insta else "")
                    out_dir.mkdir(parents=True, exist_ok=True)

                    lines = full_code.splitlines()
                    chunks = [lines[i:i + MAX_CODE_LINES_PER_SLIDE] for i in range(0, len(lines), MAX_CODE_LINES_PER_SLIDE)]
                    
                    slides = []
                    slides.append(f'<div class="slide cover-slide"><div class="cover-badge">{tech.upper()}</div><h1 class="cover-title">{titolo}</h1><div style="margin-top:40px; color:var(--tech-accent); font-weight:900; font-size:24px;">https://icarocomix.github.io/appuntidiprogrammazione</div></div>')
                    
                    analisi = process_text_formatting(row.get('ANALISI TECNICA', row.get('SINTESI DEL PROBLEMA', '')))
                    slides.append(f'<div class="slide"><div class="header"><h1>{titolo}</h1></div><span class="section-label">Analisi Tecnica</span><div class="section-content">{analisi}</div></div>')
                    
                    truncated = False
                    for c_idx, chunk in enumerate(chunks):
                        if (c_idx + 3) >= MAX_TOTAL_SLIDES:
                            truncated = True; break
                        # Escape HTML per sicurezza, poi applichiamo l'evidenziazione
                        code_html = html.escape("\n".join(chunk))
                        code_highlighted = highlight_code(code_html)
                        
                        slides.append(f'<div class="slide"><div class="header"><span class="section-label">Esempio Implementativo - Part {c_idx+1}</span></div><div class="code-container"><pre><code>{code_highlighted}</code></pre></div><div class="footer-page">{c_idx+3}/{len(chunks)+2}</div></div>')
                    
                    final_msg = "scopri_di_più()" if truncated else "salva_post_ora()"
                    slides.append(f"""
                    <div class="slide cta-debug">
                        <div class="console-title">Console di Debug</div>
                        <div class="console-line"><span class="console-prompt">></span>Stato post: <span class="console-val-accent">[utile]</span></div>
                        <div class="console-line"><span class="console-prompt">></span>Azione: <span class="console-val-green">{final_msg}</span><span class="cursor"></span></div>
                        <div class="console-line" style="margin-top:40px;"><span class="console-prompt">></span>Requisito:<br><span class="console-val-accent" style="margin-left:45px;">Click sull'icona Segnalibro</span></div>
                        <div class="cta-footer">https://icarocomix.github.io/appuntidiprogrammazione</div>
                    </div>
                    """)

                    for s_idx, s_html in enumerate(slides):
                        await page.set_content(f"<!DOCTYPE html><html><head><style>{get_css(cfg['color'], is_insta)}</style></head><body>{s_html}</body></html>")
                        if is_insta:
                            # Modalità Instagram: un file per ogni slide
                            for s_idx, s_html in enumerate(slides):
                                html_content = f"<!DOCTYPE html><html><head><style>{get_css(cfg['color'], is_insta)}</style></head><body>{s_html}</body></html>"
                                await page.set_content(html_content)
                                await page.screenshot(path=str(out_dir / f"{s_idx+1}.png"))
                        
                        elif output_format == "pdf":
                            # MODALITÀ PDF: Una sola operazione per riga Excel
                            page_break_css = "<style>.slide { page-break-after: always; break-after: page; }</style>"
                            full_pdf_html = "".join(slides)
                            
                            combined_content = f"""
                            <!DOCTYPE html>
                            <html>
                            <head>
                                <style>
                                    {get_css(cfg['color'], is_insta)}
                                    {page_break_css}
                                </style>
                            </head>
                            <body>
                                {full_pdf_html}
                            </body>
                            </html>
                            """
                            
                            await page.set_content(combined_content)
                            await page.wait_for_load_state("networkidle")
                            
                            pdf_path = out_dir / f"{pdf_filename}.pdf"
                            await page.pdf(
                                path=str(pdf_path),
                                print_background=True,
                                width=f"{w}px",
                                height=f"{h}px",
                                # FIX: Uso stringhe "0px" invece di numeri
                                margin={"top": "0px", "right": "0px", "bottom": "0px", "left": "0px"},
                                display_header_footer=False
                            )

                    print(f"✅ [{tech.upper()}] {topic_slug} ({len(slides)} slide)")
        await browser.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--tech", default="all")
    parser.add_argument("--format", default="insta", choices=["pdf", "insta"])
    args = parser.parse_args()
    
    if args.tech == "all":
        available_xlsx = [f.replace('.xlsx', '') for f in os.listdir('.') if f.endswith('.xlsx')]
        techs_to_run = available_xlsx if available_xlsx else ["java", "js", "thymeleaf", "db"]
    else:
        techs_to_run = [args.tech.lower()]

    asyncio.run(run_gen(techs_to_run, args.format))