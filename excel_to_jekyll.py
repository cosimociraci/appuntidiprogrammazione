import os
import pandas as pd
import re
import yaml
from pathlib import Path

# --- CONFIGURAZIONE ---
INPUT_DIR = "excel_input"
OUTPUT_DIR = "_articoli"

def sanitize_filename(text):
    """Genera un nome file pulito per Jekyll"""
    s = str(text).lower()
    s = re.sub(r'[^a-z0-9\s-]', '', s)
    return re.sub(r'[\s-]+', '-', s).strip('-')

def process_excels():
    # Creazione cartella output se non esiste
    out_path = Path(OUTPUT_DIR)
    out_path.mkdir(parents=True, exist_ok=True)
    
    # Pulizia articoli vecchi per evitare duplicati sporchi
    for old_file in out_path.glob("*.md"):
        old_file.unlink()

    # Scansione file Excel
    excel_files = list(Path(INPUT_DIR).glob("*.xlsx"))
    if not excel_files:
        print(f"⚠️ Nessun file trovato in {INPUT_DIR}")
        return

    for file in excel_files:
        tech_name = file.stem.lower()
        print(f"📦 Elaborazione: {tech_name}")
        
        xls = pd.ExcelFile(file)
        for sheet_name in xls.sheet_names:
            df = pd.read_excel(file, sheet_name=sheet_name)
            # Normalizzazione colonne in UPPERCASE
            df.columns = [str(c).strip().upper() for c in df.columns]
            
            for idx, row in df.iterrows():
                titolo = str(row.get('TITOLO', f'Topic-{idx}'))
                date_str = pd.Timestamp.now().strftime('%Y-%m-%d')
                filename = f"{date_str}-{sanitize_filename(titolo)}.md"
                
                # 1. Raccolta Codice (Concatena tutte le colonne ESEMPIO_X)
                code_cols = [col for col in df.columns if 'ESEMPIO' in col and pd.notna(row[col])]
                full_code = "\n".join([str(row[col]) for col in code_cols]).replace("\\n", "\n")
                
                # 2. Formattazione Analisi Tecnica (Markdown-friendly)
                analisi = str(row.get('ANALISI TECNICA', '')).replace("\\n", "\n")
                
                # 3. Preparazione Tag (Base)
                tags = [tech_name, sheet_name.lower().replace("_", " ")]

                # 4. Costruzione Frontmatter con YAML sicuro
                # Questo evita gli errori "did not find expected key" su GitHub
                frontmatter_data = {
                    "layout": "post",
                    "title": titolo,
                    "date": pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S %z'),
                    "sintesi": str(row.get('SINTESI DEL PROBLEMA', ''))[:200],
                    "esigenza": str(row.get('ESIGENZA REALE', 'N/A')),
                    "tech": tech_name,
                    "tags": tags,
                    "codice": full_code.strip()
                }

                # 5. Scrittura File
                with open(out_path / filename, "w", encoding="utf-8") as f:
                    f.write("---\n")
                    # allow_unicode=True permette di mantenere accenti e caratteri ITA
                    yaml.dump(frontmatter_data, f, allow_unicode=True, sort_keys=False)
                    f.write("---\n\n")
                    # Il corpo dell'articolo contiene solo l'Analisi Tecnica
                    # Il resto è gestito dal layout tramite i campi sopra
                    f.write(analisi)
                
                print(f"  ✅ {filename}")

if __name__ == "__main__":
    process_excels()