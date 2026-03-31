import os
import pandas as pd
import re
import subprocess
import textwrap
from pathlib import Path

# --- CONFIGURAZIONE ---
INPUT_DIR = "excel_input"
OUTPUT_DIR = "_articoli"
MAX_CHARS_WIDTH = 80  # Leggermente più stretto per migliorare la leggibilità web

# Configurazione Tecnologica Avanzata
TECH_CONFIG = {
    "java": {"parser": "java", "plugin": "prettier-plugin-java"},
    "js": {"parser": "babel", "plugin": ""},
    "javascript": {"parser": "babel", "plugin": ""},
    "thymeleaf": {"parser": "html", "plugin": ""},
    "html": {"parser": "html", "plugin": ""},
    "db": {"parser": "sql", "plugin": ""},
    "sql": {"parser": "sql", "plugin": ""},
    "default": {"parser": "babel", "plugin": ""}
}

def smart_wrap_code(code_text, width=80):
    """Spezza le righe lunghe mantenendo indentazione e struttura dei commenti"""
    lines = code_text.splitlines()
    wrapped_lines = []
    for line in lines:
        if len(line) > width:
            indent = re.match(r"^\s*", line).group(0)
            # Gestione specifica per i blocchi di commenti
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
                # Wrap generico per codice normale
                wrapped_lines.extend(textwrap.wrap(line, width=width, break_long_words=False, replace_whitespace=False))
        else:
            wrapped_lines.append(line)
    return "\n".join(wrapped_lines)

def format_code_advanced(code_text, tech):
    """Formatta il codice con rilevamento automatico e smart wrapping"""
    # 1. Rilevamento dinamico della tecnologia (es. Java dentro Thymeleaf)
    actual_tech = tech.lower()
    if actual_tech == "thymeleaf" and any(re.search(p, str(code_text)) for p in [r"@Controller", r"package\s+", r"public\s+class"]):
        actual_tech = "java"
    
    cfg = TECH_CONFIG.get(actual_tech, TECH_CONFIG["default"])
    
    # 2. Pulizia iniziale ritorni a capo Excel
    code = str(code_text).replace("\\n", "\n").replace("\r", "").strip()
    code = re.sub(r"```[a-zA-Z]*\n?", "", code).replace("```", "")
    
    # 3. Tentativo di formattazione con Prettier
    try:
        cmd = ['npx', 'prettier', '--parser', cfg["parser"], '--tab-width', '4', '--print-width', str(MAX_CHARS_WIDTH)]
        if cfg["plugin"]:
            cmd.extend(['--plugin', cfg["plugin"]])

        process = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding='utf-8'
        )
        stdout, _ = process.communicate(input=code)
        
        if process.returncode == 0 and stdout.strip():
            # Applichiamo lo smart wrap sull'output di prettier per sicurezza estrema
            return smart_wrap_code(stdout, width=MAX_CHARS_WIDTH)
    except:
        pass
    
    # 4. Fallback: Se Prettier fallisce (Sad Panda), usiamo almeno lo Smart Wrap manuale
    return smart_wrap_code(code, width=MAX_CHARS_WIDTH)

def sanitize_filename(text):
    s = str(text).lower()
    s = re.sub(r'[^a-z0-9\s-]', '', s)
    return re.sub(r'[\s-]+', '-', s).strip('-')

def clean_excel_text(text):
    if pd.isna(text): return ""
    return str(text).replace("\\n", "\n").replace("\r", "")

def process_excels():
    input_path = Path(INPUT_DIR)
    out_path = Path(OUTPUT_DIR)
    if not input_path.exists(): return

    out_path.mkdir(parents=True, exist_ok=True)
    for old_file in out_path.glob("*.md"): old_file.unlink()

    for file in input_path.glob("*.xlsx"):
        tech_name = file.stem.lower()
        print(f"🚀 Elaborazione Avanzata: {tech_name.upper()}")
        
        try:
            xls = pd.ExcelFile(file)
            for sheet_name in xls.sheet_names:
                df = pd.read_excel(file, sheet_name=sheet_name)
                df.columns = [str(c).strip().upper() for c in df.columns]
                
                for idx, row in df.iterrows():
                    # Bonifica metadati
                    titolo = str(row.get('TITOLO', f'Topic-{idx}')).replace('"', '').replace("'", "")
                    date_now = pd.Timestamp.now()
                    filename = f"{date_now.strftime('%Y-%m-%d')}-{sanitize_filename(titolo)}.md"
                    
                    sintesi_raw = clean_excel_text(row.get('SINTESI DEL PROBLEMA', ''))
                    sintesi = sintesi_raw.replace("\n", " ").replace('"', '').strip()[:250]
                    
                    # Elaborazione Codice con Logica Avanzata
                    code_cols = [col for col in df.columns if 'ESEMPIO' in col and pd.notna(row[col])]
                    raw_code = "\n".join([str(row[col]) for col in code_cols])
                    formatted_code = format_code_advanced(raw_code, tech_name)
                    
                    # Scrittura MD
                    with open(out_path / filename, "w", encoding="utf-8") as f:
                        f.write("---\n")
                        f.write(f"layout: post\n")
                        f.write(f"title: \"{titolo}\"\n")
                        f.write(f"date: {date_now.strftime('%Y-%m-%d %H:%M:%S %z')}\n")
                        f.write(f"sintesi: \"{sintesi}\"\n")
                        f.write(f"tech: {tech_name}\n")
                        f.write(f"tags: [{tech_name}, \"{sheet_name.lower()}\"]\n")
                        f.write(f"pdf_file: \"{sanitize_filename(titolo)}.pdf\"\n")
                        f.write("---\n\n")
                        
                        esigenza = clean_excel_text(row.get('ESIGENZA REALE', ''))
                        if esigenza: f.write(f"## Esigenza Reale\n{esigenza}\n\n")
                        
                        analisi = clean_excel_text(row.get('ANALISI TECNICA', ''))
                        if analisi: f.write(f"## Analisi Tecnica\n{analisi}\n\n")
                        
                        if formatted_code:
                            f.write(f"## Esempio Implementativo\n\n")
                            # Se la tecnologia è stata rilevata come Java, usiamo java per il block
                            actual_block_tech = "java" if "public class" in formatted_code else tech_name
                            f.write(f"```{actual_block_tech}\n")
                            f.write(f"{formatted_code}\n")
                            f.write(f"```\n")
                    
                    print(f"  ✅ Generato: {filename}")
        except Exception as e:
            print(f"  ❌ Errore: {e}")

if __name__ == "__main__":
    process_excels()