import os
import pandas as pd
import re
import subprocess
from pathlib import Path

# --- CONFIGURAZIONE PERCORSI ---
INPUT_DIR = "excel_input"
OUTPUT_DIR = "_articoli"
MAX_CHARS_WIDTH = 100

# --- CONFIGURAZIONE PRETTIER (Parser e Plugin) ---
# Nota: Assicurati di aver lanciato: npm install prettier prettier-plugin-java
TECH_MAP = {
    "java": {"parser": "java", "plugin": "prettier-plugin-java"},
    "js": {"parser": "babel", "plugin": ""},
    "javascript": {"parser": "babel", "plugin": ""},
    "thymeleaf": {"parser": "html", "plugin": ""},
    "html": {"parser": "html", "plugin": ""},
    "db": {"parser": "sql", "plugin": ""},
    "sql": {"parser": "sql", "plugin": ""}
}

def format_code_with_prettier(code_text, tech):
    # 1. TRASFORMAZIONE FONDAMENTALE: trasforma i \\n di Excel in veri invii
    # Questo garantisce che, anche se Prettier fallisce, il file MD sia leggibile
    code = str(code_text).replace("\\n", "\n").replace("\r", "").strip()
    
    # Pulizia rapida per snippet incompleti
    code = re.sub(r"```[a-zA-Z]*\n?", "", code).replace("```", "")
    
    config = TECH_MAP.get(tech.lower(), {"parser": "babel", "plugin": ""})
    target_parser = config["parser"]
    target_plugin = config["plugin"]

    try:
        cmd = [
            'npx', 'prettier', 
            '--parser', target_parser, 
            '--tab-width', '4', 
            '--print-width', str(MAX_CHARS_WIDTH)
        ]
        
        if target_plugin:
            cmd.extend(['--plugin', target_plugin])

        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8'
        )
        
        stdout, stderr = process.communicate(input=code)

        if process.returncode == 0 and stdout.strip():
            return stdout
        else:
            # --- IL SEGRETO DEL PANDA ---
            # Se arriviamo qui, Prettier ha fallito. 
            # Restituiamo 'code' che ha già subito il replace("\\n", "\n")
            # Quindi il file MD sarà comunque MULTI-RIGA.
            return code 
    except Exception:
        return code

def sanitize_filename(text):
    """Genera uno slug pulito per il nome del file .md"""
    s = str(text).lower()
    s = re.sub(r'[^a-z0-9\s-]', '', s)
    return re.sub(r'[\s-]+', '-', s).strip('-')

def clean_excel_text(text):
    """Pulisce il testo generico dalle anomalie di Excel"""
    if pd.isna(text): return ""
    return str(text).replace("\\n", "\n").replace("\r", "")

def process_excels():
    input_path = Path(INPUT_DIR)
    out_path = Path(OUTPUT_DIR)
    
    if not input_path.exists():
        print(f"❌ Cartella di input '{INPUT_DIR}' non trovata!")
        return

    out_path.mkdir(parents=True, exist_ok=True)
    
    # Pulizia vecchi file per evitare duplicati orfani
    for old_file in out_path.glob("*.md"):
        old_file.unlink()

    excel_files = list(input_path.glob("*.xlsx"))
    print(f"🔍 Trovati {len(excel_files)} file Excel.")

    for file in excel_files:
        tech_name = file.stem.lower()
        print(f"📦 Elaborazione tecnologia: {tech_name.upper()}")
        
        try:
            xls = pd.ExcelFile(file)
            for sheet_name in xls.sheet_names:
                df = pd.read_excel(file, sheet_name=sheet_name)
                df.columns = [str(c).strip().upper() for c in df.columns]
                
                for idx, row in df.iterrows():
                    titolo = str(row.get('TITOLO', f'Topic-{idx}'))
                    date_now = pd.Timestamp.now()
                    filename = f"{date_now.strftime('%Y-%m-%d')}-{sanitize_filename(titolo)}.md"
                    
                    # Estrazione e pulizia dati
                    esigenza = clean_excel_text(row.get('ESIGENZA REALE', ''))
                    analisi = clean_excel_text(row.get('ANALISI TECNICA', ''))
                    sintesi = clean_excel_text(row.get('SINTESI DEL PROBLEMA', '')).replace("\n", " ").strip()[:250]
                    
                    # Gestione Codice (Concatena tutte le colonne ESEMPIO)
                    code_cols = [col for col in df.columns if 'ESEMPIO' in col and pd.notna(row[col])]
                    raw_code = "\n".join([str(row[col]) for col in code_cols])
                    
                    # Chiamata alla formattazione
                    formatted_code = format_code_with_prettier(raw_code, tech_name)
                    
                    # Scrittura File Markdown
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
                    
        except Exception as e:
            print(f"  ❌ Errore nel file {file.name}: {e}")

if __name__ == "__main__":
    process_excels()