import os
import pandas as pd
import re
import subprocess
import textwrap
from pathlib import Path

# --- CONFIGURAZIONE ---
INPUT_DIR = "excel_input"
OUTPUT_DIR = "_articoli"
MAX_CHARS_WIDTH = 80 

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

def pre_format_cleanup(code):
    """Pulizia preventiva per far respirare i blocchi di codice."""
    code = re.sub(r'(?<!\n)//', r'\n//', code)
    code = re.sub(r'(?<!\n)/\*', r'\n/*', code)
    code = re.sub(r'\*/(?!\n)', r'*/\n', code)
    code = re.sub(r'(?<!\n)\{', r'\n{', code)
    code = re.sub(r'\}(?!\n)', r'}\n', code)
    code = re.sub(r'\n{3,}', '\n\n', code)
    return code.strip()

def smart_wrap_code(code_text, width=80):
    """Spezza le righe lunghe mantenendo indentazione."""
    lines = code_text.splitlines()
    wrapped_lines = []
    for line in lines:
        if len(line) > width:
            indent = re.match(r"^\s*", line).group(0)
            # Corretto il SyntaxWarning con raw string 'r'
            if line.strip().startswith('//') or line.strip().startswith('*') or line.strip().startswith('/*'):
                content = line.lstrip(r'/\* ').lstrip('* ')
                prefix = indent + ("// " if "//" in line else "* ")
                sub_wrapped = textwrap.wrap(content, width=width-len(prefix), break_long_words=False)
                for i, w_line in enumerate(sub_wrapped):
                    wrapped_lines.append(prefix + w_line)
            else:
                wrapped_lines.extend(textwrap.wrap(line, width=width, break_long_words=False, replace_whitespace=False))
        else:
            wrapped_lines.append(line)
    return "\n".join(wrapped_lines)

def format_code_pro(code_text, tech):
    """Pipeline di formattazione codice."""
    code = str(code_text).replace("\\n", "\n").replace("\r", "").strip()
    code = re.sub(r"```[a-zA-Z]*\n?", "", code).replace("```", "")
    code = pre_format_cleanup(code)
    
    actual_tech = tech.lower()
    if actual_tech == "thymeleaf" and any(re.search(p, code) for p in [r"@Controller", r"public\s+class"]):
        actual_tech = "java"
    
    cfg = TECH_CONFIG.get(actual_tech, TECH_CONFIG["default"])

    try:
        cmd = ['npx', 'prettier', '--parser', cfg["parser"], '--tab-width', '4', '--print-width', str(MAX_CHARS_WIDTH)]
        if cfg["plugin"]: cmd.extend(['--plugin', cfg["plugin"]])

        process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding='utf-8')
        stdout, _ = process.communicate(input=code)
        
        if process.returncode == 0 and stdout.strip():
            return smart_wrap_code(stdout, width=MAX_CHARS_WIDTH)
    except:
        pass
    
    return smart_wrap_code(code, width=MAX_CHARS_WIDTH)

def sanitize_filename(text):
    s = str(text).lower()
    s = re.sub(r'[^a-z0-9\s-]', '', s)
    return re.sub(r'[\s-]+', '-', s).strip('-')

def process_excels():
    input_path = Path(INPUT_DIR)
    out_path = Path(OUTPUT_DIR)
    if not input_path.exists(): return

    out_path.mkdir(parents=True, exist_ok=True)
    for old_file in out_path.glob("*.md"): old_file.unlink()

    for file in input_path.glob("*.xlsx"):
        tech_name = file.stem.lower()
        print(f"🚀 Processing: {tech_name.upper()}")
        
        try:
            xls = pd.ExcelFile(file)
            for sheet_name in xls.sheet_names:
                df = pd.read_excel(file, sheet_name=sheet_name)
                df.columns = [str(c).strip().upper() for c in df.columns]
                
                for idx, row in df.iterrows():
                    # --- PULIZIA TITOLO ---
                    titolo = str(row.get('TITOLO', f'Topic-{idx}')).replace('"', '').replace("'", "")
                    # Rimuoviamo caratteri non-ASCII solo per sicurezza, ma manteniamo la leggibilità
                    titolo_clean = titolo.encode('ascii', 'ignore').decode('ascii')
                    
                    filename = f"{pd.Timestamp.now().strftime('%Y-%m-%d')}-{sanitize_filename(titolo_clean)}.md"
                    
                    # --- PULIZIA SINTESI (USO LITERAL BLOCK PER SICUREZZA) ---
                    sintesi = str(row.get('SINTESI DEL PROBLEMA', '')).replace("\\n", " ").replace("\n", " ")
                    # Sostituiamo caratteri problematici per YAML
                    sintesi = sintesi.replace('"', "'").strip()[:250]

                    code_cols = [col for col in df.columns if 'ESEMPIO' in col and pd.notna(row[col])]
                    raw_code = "\n".join([str(row[col]) for col in code_cols])
                    
                    formatted_code = format_code_pro(raw_code, tech_name)
                    
                    # Determiniamo il linguaggio per il blocco Markdown (db -> sql)
                    code_lang = "sql" if tech_name == "db" else tech_name

                    with open(out_path / filename, "w", encoding="utf-8") as f:
                        f.write("---\n")
                        f.write(f"layout: post\n")
                        f.write(f"title: \"{titolo_clean}\"\n")
                        f.write(f"date: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                        # Usiamo '>' per permettere sintesi multi-riga o con caratteri speciali
                        f.write(f"sintesi: >\n  {sintesi}\n")
                        f.write(f"tech: \"{tech_name}\"\n")
                        f.write(f"tags: [\"{tech_name}\", \"{sheet_name.lower().strip()}\"]\n")
                        f.write(f"pdf_file: \"{sanitize_filename(titolo_clean)}.pdf\"\n")
                        f.write("---\n\n")
                        
                        for section in ['ESIGENZA REALE', 'ANALISI TECNICA']:
                            content = str(row.get(section, '')).replace("\\n", "\n")
                            if content and content != 'nan':
                                # Escaping per tag Liquid che mandano in crash Jekyll
                                content = content.replace("{{", "{ {").replace("}}", "} }")
                                f.write(f"## {section.title()}\n{content}\n\n")
                        
                        if formatted_code:
                            f.write(f"## Esempio Implementativo\n\n```{code_lang}\n{formatted_code}\n```\n")
                    
                    print(f"  ✅ {filename}")
        except Exception as e:
            print(f"  ❌ Error in {file.name}: {e}")

if __name__ == "__main__":
    process_excels()