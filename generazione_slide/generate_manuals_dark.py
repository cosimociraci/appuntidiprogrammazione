# --- ESEMPIO DI UTILIZZO ---
# Generazione Totale (PDF):
# python generate_manuals_dark.py
# 
# Generazione Mirata (Java in PDF):
# python generate_manuals_dark.py --tech java
# 
# Generazione Sorgenti HTML (per debug o modifiche):
# python generate_manuals_dark.py --tech db --format source
#
# Generazione Carosello Instagram (PNG):
# python generate_manuals_dark.py --tech java --format insta

import os
import re
import asyncio
import subprocess
import argparse
import html
import textwrap
import pandas as pd
from pathlib import Path
from playwright.async_api import async_playwright

# --- CONFIGURAZIONE TECNOLOGICA ---
TECH_CONFIG = {
    "java": {"color": "#f89820", "parser": "java", "plugins": ["prettier-plugin-java"]},
    "js": {"color": "#f7df1e", "parser": "espree", "plugins": []},
    "db": {"color": "#336791", "parser": "sql", "plugins": []},
    "thymeleaf": {"color": "#005f00", "parser": "html", "plugins": []},
    "default": {"color": "#FF4081", "parser": "babel", "plugins": []}
}

SQUARE_SIZE = 1080 
MAX_CHARS_WIDTH = 70 
MAX_CODE_LINES_PER_SLIDE = 18 
MAX_TOTAL_SLIDES = 10 

def smart_wrap_code(code_text, width=70):
    code_text = str(code_text).replace("\\n", "\n")
    lines = code_text.splitlines()
    wrapped_lines = []
    for line in lines:
        if len(line) > width:
            indent = re.match(r"^\s*", line).group(0)
            if line.strip().startswith('/*') or line.strip().startswith('*'):
                prefix = indent + "* "
                content = line.lstrip('/* ').lstrip('* ')
                sub_wrapped = textwrap.wrap(content, width=width-len(prefix))
                for i, w_line in enumerate(sub_wrapped):
                    if i == 0 and line.strip().startswith('/*'):
                        wrapped_lines.append(indent + "/* " + w_line)
                    else:
                        wrapped_lines.append(prefix + w_line)
            else:
                wrapped_lines.extend(textwrap.wrap(line, width=width, break_long_words=False, replace_whitespace=False))
        else:
            wrapped_lines.append(line)
    return "\n".join(wrapped_lines)

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

def format_code(code_text, tech):
    actual_tech = "java" if tech=="thymeleaf" and any(re.search(p, str(code_text)) for p in [r"@Controller", r"package\s+"]) else tech
    cfg = TECH_CONFIG.get(actual_tech, TECH_CONFIG["default"])
    code = str(code_text).replace("\\n", "\n").strip()
    code = re.sub(r"```[a-zA-Z]*\n?", "", code).replace("```", "")
    code = re.sub(r'(?<!\n)/\*', r'\n/*', code)
    code = smart_wrap_code(code, width=MAX_CHARS_WIDTH)

    if actual_tech == "db":
        try:
            cmd = ['npx', 'sql-formatter', '-l', 'postgresql', '--config', '{"keywordCase": "upper"}']
            p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
            stdout, _ = p.communicate(input=code)
            if p.returncode == 0: return smart_wrap_code(stdout.replace("/*", "\n/*").replace("*/", "*/\n"), MAX_CHARS_WIDTH)
        except: pass
    try:
        cmd = ['npx', 'prettier', '--parser', cfg["parser"], '--tab-width', '4', '--print-width', str(MAX_CHARS_WIDTH)]
        for pl in cfg.get("plugins", []): cmd.extend(['--plugin', pl])
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        stdout, _ = p.communicate(input=code)
        if p.returncode == 0: return smart_wrap_code(stdout, MAX_CHARS_WIDTH)
    except: pass
    return code

def get_css(color, is_insta=False):
    w, h = (SQUARE_SIZE, SQUARE_SIZE) if is_insta else (1920, 1080)
    return f"""
    @import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500&family=Montserrat:wght@700;900&family=Poppins:wght@300;400;600&display=swap');
    :root {{ --tech-accent: {color}; --neon-green: #4AF626; }}
    body {{ margin: 0; background: #000; color: white; font-family: 'Poppins', sans-serif; }}
    .slide {{ width: {w}px; height: {h}px; padding: 70px; box-sizing: border-box; display: flex; flex-direction: column; position: relative; background: #0a0a0a; }}
    .cover-slide {{ justify-content: center; text-align: center; border: 20px solid var(--tech-accent); }}
    .cover-badge {{ background: var(--tech-accent); color: #000; font-family: 'Montserrat'; font-weight: 900; font-size: 28px; padding: 12px 30px; display: inline-block; margin-bottom: 25px; }}
    .cover-title {{ font-family: 'Montserrat'; font-weight: 900; font-size: 65px; line-height: 1.1; margin: 0; text-transform: uppercase; }}
    .header {{ border-left: 12px solid var(--tech-accent); padding-left: 25px; margin-bottom: 30px; }}
    .section-label {{ font-family: 'Montserrat'; font-weight: 700; color: var(--tech-accent); text-transform: uppercase; font-size: 20px; margin-bottom: 10px; display: block; }}
    .code-container {{ background: #121212; padding: 35px; border-radius: 6px; border: 1px solid #222; flex-grow: 1; }}
    pre {{ font-family: 'Fira Code', monospace; font-size: 19px; color: #E0E0E0; line-height: 1.5; margin: 0; white-space: pre-wrap; }}
    .footer-page {{ position: absolute; bottom: 30px; right: 60px; font-size: 18px; color: #333; font-weight: 900; }}
    
    .cta-debug {{ justify-content: center; font-family: 'Fira Code', monospace; padding: 100px; background: #0a0a0a; }}
    .console-title {{ font-family: 'Montserrat'; font-weight: 900; font-size: 45px; color: white; margin-bottom: 60px; text-transform: uppercase; text-align: center; letter-spacing: 2px; }}
    .console-line {{ font-size: 32px; margin-bottom: 25px; line-height: 1.4; }}
    .console-prompt {{ color: white; margin-right: 15px; opacity: 0.5; }}
    .console-key {{ color: white; }}
    .console-val-green {{ color: var(--neon-green); text-shadow: 0 0 10px var(--neon-green); }}
    .console-val-accent {{ color: var(--tech-accent); text-shadow: 0 0 10px var(--tech-accent); }}
    .cursor {{ display: inline-block; width: 15px; height: 35px; background: white; margin-left: 5px; animation: blink 1s infinite; vertical-align: middle; }}
    @keyframes blink {{ 50% {{ opacity: 0; }} }}
    .cta-footer {{ position: absolute; bottom: 50px; width: 100%; left: 0; text-align: center; font-size: 20px; color: #444; font-weight: bold; }}
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
                    # Slug standard per cartelle
                    topic_slug = re.sub(r'[^a-zA-Z0-9]+', '_', titolo)
                    
                    # Nome file PDF: minuscolo e con trattini "-"
                    pdf_filename = re.sub(r'[^a-zA-Z0-9]+', '-', titolo).lower()

                    out_dir = Path(f"output/{tech}/{sheet_slug}") / (topic_slug if is_insta else "")
                    out_dir.mkdir(parents=True, exist_ok=True)

                    lines = full_code.splitlines()
                    chunks = [lines[i:i + MAX_CODE_LINES_PER_SLIDE] for i in range(0, len(lines), MAX_CODE_LINES_PER_SLIDE)]
                    
                    slides = []
                    # 1. Cover
                    slides.append(f'<div class="slide cover-slide"><div class="cover-badge">{tech.upper()}</div><h1 class="cover-title">{titolo}</h1><div style="margin-top:40px; color:var(--tech-accent); font-weight:900; font-size:24px;">https://icarocomix.github.io/appuntidiprogrammazione</div></div>')
                    # 2. Analisi
                    analisi = process_text_formatting(row.get('ANALISI TECNICA', row.get('SINTESI DEL PROBLEMA', '')))
                    slides.append(f'<div class="slide content-slide"><div class="header"><h1>{titolo}</h1></div><span class="section-label">Analisi Tecnica</span><div class="section-content">{analisi}</div></div>')
                    # 3. Codice
                    truncated = False
                    for c_idx, chunk in enumerate(chunks):
                        if (c_idx + 3) >= MAX_TOTAL_SLIDES:
                            truncated = True; break
                        slides.append(f'<div class="slide"><div class="header"><span class="section-label">Codice Part {c_idx+1}</span></div><div class="code-container"><pre><code>{html.escape("\\n".join(chunk))}</code></pre></div><div class="footer-page">{c_idx+3}/{len(chunks)+2}</div></div>')

                    # 4. CTA DEBUG CONSOLE
                    final_msg = "scopri_di_più()" if truncated else "salva_post_ora()"
                    slides.append(f"""
                    <div class="slide cta-debug">
                        <div class="console-title">Console di Debug</div>
                        <div class="console-line"><span class="console-prompt">></span><span class="console-key">Stato post:</span> <span class="console-val-accent">[utile]</span></div>
                        <div class="console-line"><span class="console-prompt">></span><span class="console-key">Azione:</span> <span class="console-val-green">{final_msg}</span><span class="cursor"></span></div>
                        <div class="console-line" style="margin-top:40px;">
                            <span class="console-prompt">></span><span class="console-key">Requisito:</span><br>
                            <span class="console-val-accent" style="margin-left:45px;">Click sull'icona Segnalibro</span>
                        </div>
                        <div class="cta-footer">https://icarocomix.github.io/appuntidiprogrammazione</div>
                    </div>
                    """)

                    for s_idx, s_html in enumerate(slides):
                        await page.set_content(f"<!DOCTYPE html><html><head><style>{get_css(cfg['color'], is_insta)}</style></head><body>{s_html}</body></html>")
                        if is_insta: 
                            await page.screenshot(path=str(out_dir / f"{s_idx+1}.png"))
                        elif output_format == "pdf": 
                            await page.pdf(path=str(out_dir / f"{pdf_filename}.pdf"), print_background=True, width=f"{w}px", height=f"{h}px")

                    print(f"✅ [{tech.upper()}] {topic_slug} ({len(slides)} slide)")
        await browser.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--tech", default="all")
    parser.add_argument("--format", default="insta", choices=["pdf", "source", "insta"])
    args = parser.parse_args()
    
    if args.tech == "all":
        available_xlsx = [f.replace('.xlsx', '') for f in os.listdir('.') if f.endswith('.xlsx')]
        techs_to_run = available_xlsx if available_xlsx else ["java", "js", "thymeleaf", "db"]
    else:
        techs_to_run = [args.tech.lower()]

    asyncio.run(run_gen(techs_to_run, args.format))