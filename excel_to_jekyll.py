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
    """
    Svolgo una pulizia manuale preventiva del codice estratto da Excel.
    L'obiettivo è 'far respirare' i blocchi critici (graffe e commenti) 
    prima di darli in pasto al formatter automatico, evitando l'effetto muro di testo.
    """

    # Voglio che ogni commento a riga singola inizi su una nuova riga.
    # Cerco '//' e, se non è già preceduto da un ritorno a capo, ne aggiungo uno.
    code = re.sub(r'(?<!\n)//', r'\n//', code)
    
    # Stessa logica per l'apertura dei commenti multi-riga.
    # Mi assicuro che '/*' non resti attaccato al codice precedente.
    code = re.sub(r'(?<!\n)/\*', r'\n/*', code)
    
    # Per la chiusura del commento '*/', voglio l'effetto opposto:
    # deve esserci un ritorno a capo subito dopo, così il codice seguente scende sotto.
    code = re.sub(r'\*/(?!\n)', r'*/\n', code)
    
    # Le parentesi graffe sono il cuore della struttura.
    # Spingo ogni apertura '{' a riga nuova se è compressa sulla riga precedente.
    code = re.sub(r'(?<!\n)\{', r'\n{', code)
    
    # Dopo la chiusura '}', forzo un a capo. 
    # Questo aiuta a separare nettamente i blocchi di logica o i metodi.
    code = re.sub(r'\}(?!\n)', r'}\n', code)
    
    # Dopo tutte queste sostituzioni, potrebbero essersi creati troppi spazi vuoti.
    # Riduco ogni sequenza di 3 o più ritorni a capo in un doppio a capo pulito.
    code = re.sub(r'\n{3,}', '\n\n', code)
    
    # Restituisco il codice rifilato dagli spazi bianchi inutili agli estremi.
    return code.strip()

def smart_wrap_code(code_text, width=80):
    """Spezza le righe lunghe mantenendo indentazione e struttura"""
    lines = code_text.splitlines()
    wrapped_lines = []
    for line in lines:
        if len(line) > width:
            indent = re.match(r"^\s*", line).group(0)
            if line.strip().startswith('//') or line.strip().startswith('*') or line.strip().startswith('/*'):
                content = line.lstrip('/\* ').lstrip('* ')
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
    """Pipeline completa: Pulizia Manuale -> Prettier -> Smart Wrap"""
    # 1. Pulizia iniziale stringhe Excel
    code = str(code_text).replace("\\n", "\n").replace("\r", "").strip()
    code = re.sub(r"```[a-zA-Z]*\n?", "", code).replace("```", "")

    # 2. APPLICAZIONE REGOLE RICHIESTE (Pre-formatting)
    code = pre_format_cleanup(code)
    
    # 3. Rilevamento Tecnologia
    actual_tech = tech.lower()
    if actual_tech == "thymeleaf" and any(re.search(p, code) for p in [r"@Controller", r"public\s+class"]):
        actual_tech = "java"
    
    cfg = TECH_CONFIG.get(actual_tech, TECH_CONFIG["default"])

    # 4. Tentativo Formattazione Esterna
    try:
        cmd = ['npx', 'prettier', '--parser', cfg["parser"], '--tab-width', '4', '--print-width', str(MAX_CHARS_WIDTH)]
        if cfg["plugin"]: cmd.extend(['--plugin', cfg["plugin"]])

        process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding='utf-8')
        stdout, _ = process.communicate(input=code)
        
        if process.returncode == 0 and stdout.strip():
            return smart_wrap_code(stdout, width=MAX_CHARS_WIDTH)
    except:
        pass
    
    # 5. Fallback con solo Smart Wrap se Prettier fallisce
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
                    # --- PULIZIA TITOLO E SINTESI ---
                    # Normalizziamo i caratteri speciali che Excel inserisce a tradimento
                    titolo = str(row.get('TITOLO', f'Topic-{idx}')).replace('"', '').replace("'", "")
                    titolo = titolo.encode('ascii', 'ignore').decode('ascii') # Rimuove emoji o char strani
                    
                    filename = f"{pd.Timestamp.now().strftime('%Y-%m-%d')}-{sanitize_filename(titolo)}.md"
                    
                    # Pulizia profonda della sintesi per evitare che rompa il layout YAML
                    sintesi = str(row.get('SINTESI DEL PROBLEMA', '')).replace("\\n", " ").replace("\n", " ")
                    sintesi = sintesi.replace('"', '').replace(":", "-").strip()[:250]
                    sintesi = sintesi.encode('ascii', 'ignore').decode('ascii')

                    code_cols = [col for col in df.columns if 'ESEMPIO' in col and pd.notna(row[col])]
                    raw_code = "\n".join([str(row[col]) for col in code_cols])
                    
                    formatted_code = format_code_pro(raw_code, tech_name)
                    
                    with open(out_path / filename, "w", encoding="utf-8") as f:
                        f.write("---\n")
                        f.write(f"layout: post\n")
                        f.write(f"title: \"{titolo}\"\n")
                        # Data in formato standard Jekyll per evitare errori di parsing
                        f.write(f"date: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                        f.write(f"sintesi: \"{sintesi}\"\n")
                        f.write(f"tech: \"{tech_name}\"\n") # Virgolette per sicurezza
                        f.write(f"tags: [\"{tech_name}\", \"{sheet_name.lower().strip()}\"]\n")
                        f.write(f"pdf_file: \"{sanitize_filename(titolo)}.pdf\"\n")
                        f.write("---\n\n")
                        
                        for section in ['ESIGENZA REALE', 'ANALISI TECNICA']:
                            content = str(row.get(section, '')).replace("\\n", "\n")
                            if content and content != 'nan':
                                # Rimuoviamo eventuali caratteri che simulano tag Liquid {{ }}
                                content = content.replace("{{", "{ {").replace("}}", "} }")
                                f.write(f"## {section.title()}\n{content}\n\n")
                        
                        if formatted_code:
                            # Proteggiamo il blocco di codice
                            f.write(f"## Esempio Implementativo\n\n```{tech_name}\n{formatted_code}\n```\n")
                    
                    print(f"  ✅ {filename}")
        except Exception as e:
            print(f"  ❌ Error in {file.name}: {e}")

if __name__ == "__main__":
    process_excels()