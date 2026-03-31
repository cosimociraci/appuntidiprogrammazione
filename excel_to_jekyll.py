import os
import pandas as pd
import re
import subprocess
from pathlib import Path

# --- CONFIGURAZIONE ---
INPUT_DIR = "excel_input"
OUTPUT_DIR = "_articoli"
MAX_CHARS_WIDTH = 100

# Mappa per i linguaggi supportati da Prettier/SQL
TECH_CONFIG = {
    "java": {"parser": "java", "plugins": ["prettier-plugin-java"]},
    "js": {"parser": "espree", "plugins": []},
    "db": {"parser": "sql", "plugins": []},
    "thymeleaf": {"parser": "html", "plugins": []},
    "default": {"parser": "babel", "plugins": []}
}

def format_code_tech(code_text, tech):
    """Formatta il codice tramite npx per preservare indentazione e invii"""
    code = str(code_text).replace("\\n", "\n").strip()
    # Pulisce eventuali rimasugli di markdown dall'excel
    code = re.sub(r"```[a-zA-Z]*\n?", "", code).replace("```", "")
    
    cfg = TECH_CONFIG.get(tech.lower(), TECH_CONFIG["default"])
    
    if tech.lower() == "db":
        try:
            cmd = ['npx', 'sql-formatter', '-l', 'postgresql', '--config', '{"keywordCase": "upper"}']
            p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
            stdout, _ = p.communicate(input=code)
            if p.returncode == 0: return stdout.strip()
        except: pass

    try:
        cmd = ['npx', 'prettier', '--parser', cfg["parser"], '--tab-width', '4', '--print-width', str(MAX_CHARS_WIDTH)]
        if cfg.get("plugins"):
            for pl in cfg["plugins"]: cmd.extend(['--plugin', pl])
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        stdout, _ = p.communicate(input=code)
        if p.returncode == 0: return stdout.strip()
    except: pass
    
    return code

def sanitize_filename(text):
    """Genera lo slug per il nome del file"""
    s = str(text).lower()
    s = re.sub(r'[^a-z0-9\s-]', '', s)
    return re.sub(r'[\s-]+', '-', s).strip('-')

def clean_excel_text(text):
    if pd.isna(text): return ""
    return str(text).replace("\\n", "\n").replace("\r", "")

def process_excels():
    input_path = Path(INPUT_DIR)
    out_path = Path(OUTPUT_DIR)
    
    if not input_path.exists():
        print(f"❌ Cartella {INPUT_DIR} non trovata.")
        return

    out_path.mkdir(parents=True, exist_ok=True)
    
    # Pulizia preventiva per evitare conflitti
    for old_file in out_path.glob("*.md"):
        old_file.unlink()

    excel_files = list(input_path.glob("*.xlsx"))
    
    for file in excel_files:
        tech_name = file.stem.lower()
        print(f"🚀 Elaborazione: {tech_name}")
        
        xls = pd.ExcelFile(file)
        for sheet_name in xls.sheet_names:
            df = pd.read_excel(file, sheet_name=sheet_name)
            df.columns = [str(c).strip().upper() for c in df.columns]
            
            for idx, row in df.iterrows():
                titolo = str(row.get('TITOLO', f'Topic-{idx}'))
                # Il nome file DEVE avere la data per Jekyll
                date_prefix = pd.Timestamp.now().strftime('%Y-%m-%d')
                filename = f"{date_prefix}-{sanitize_filename(titolo)}.md"
                
                # Campi per il Front Matter
                sintesi_raw = clean_excel_text(row.get('SINTESI DEL PROBLEMA', ''))
                sintesi = sintesi_raw.replace("\n", " ").strip()[:250]
                
                # Campi per il corpo
                esigenza = clean_excel_text(row.get('ESIGENZA REALE', ''))
                analisi = clean_excel_text(row.get('ANALISI TECNICA', ''))
                
                # Gestione Codice
                code_cols = [col for col in df.columns if 'ESEMPIO' in col and pd.notna(row[col])]
                raw_code = "\n".join([clean_excel_text(row[col]) for col in code_cols])
                formatted_code = format_code_tech(raw_code, tech_name)
                
                tags = [tech_name, sheet_name.lower().replace("_", " ")]

                # SCRITTURA DEL FILE MD
                with open(out_path / filename, "w", encoding="utf-8") as f:
                    f.write("---\n")
                    f.write(f"layout: post\n")
                    f.write(f"title: \"{titolo}\"\n")
                    f.write(f"date: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S %z')}\n")
                    f.write(f"sintesi: \"{sintesi}\"\n")
                    f.write(f"tech: {tech_name}\n")
                    f.write(f"tags: {tags}\n")
                    f.write("---\n\n")
                    
                    # Sezioni nel corpo (Markdown)
                    if esigenza:
                        f.write(f"## Esigenza Reale\n{esigenza}\n\n")
                    
                    if analisi:
                        f.write(f"## Analisi Tecnica\n{analisi}\n\n")
                    
                    if formatted_code:
                        f.write(f"## Esempio Implementativo\n\n")
                        f.write(f"```{tech_name}\n")
                        f.write(f"{formatted_code}\n")
                        f.write(f"```\n")
                
                print(f"  ✅ Generato: {filename}")

if __name__ == "__main__":
    process_excels()