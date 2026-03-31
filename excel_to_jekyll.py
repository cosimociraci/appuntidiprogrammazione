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

def clean_excel_text(text):
    """Normalizza i ritorni a capo da Excel"""
    if pd.isna(text):
        return ""
    # Trasforma i '\\n' letterali di Excel in veri ritorni a capo
    return str(text).replace("\\n", "\n").replace("\r", "")

def process_excels():
    out_path = Path(OUTPUT_DIR)
    out_path.mkdir(parents=True, exist_ok=True)
    
    # Pulizia articoli vecchi
    for old_file in out_path.glob("*.md"):
        old_file.unlink()

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
            df.columns = [str(c).strip().upper() for c in df.columns]
            
            for idx, row in df.iterrows():
                titolo = str(row.get('TITOLO', f'Topic-{idx}'))
                date_str = pd.Timestamp.now().strftime('%Y-%m-%d')
                filename = f"{date_str}-{sanitize_filename(titolo)}.md"
                
                # 1. Raccolta Codice (Concatena tutte le colonne ESEMPIO_X)
                code_cols = [col for col in df.columns if 'ESEMPIO' in col and pd.notna(row[col])]
                # Puliamo e uniamo preservando i ritorni a capo
                raw_code = "\n".join([str(row[col]) for col in code_cols])
                full_code = clean_excel_text(raw_code)
                
                # 2. Formattazione Analisi Tecnica e Sintesi (Markdown-friendly)
                # NOTA: L'analisi tecnica va nel CORPO del file, non nel frontmatter
                analisi = clean_excel_text(row.get('ANALISI TECNICA', ''))
                sintesi = clean_excel_text(row.get('SINTESI DEL PROBLEMA', ''))
                esigenza = clean_excel_text(row.get('ESIGENZA REALE', ''))
                
                # 3. Preparazione Tag (Base)
                tags = [tech_name, sheet_name.lower().replace("_", " ")]

                # 4. Costruzione Frontmatter con YAML sicuro
                frontmatter_data = {
                    "layout": "post",
                    "title": titolo,
                    "date": pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S %z'),
                    "sintesi": sintesi[:250], # Manteniamo sintesi e esigenza brevi nel frontmatter
                    "esigenza": esigenza,
                    "tech": tech_name,
                    "tags": tags,
                    "codice": full_code.strip() # Il codice VA nel frontmatter
                }

                # 5. Scrittura File
                with open(out_path / filename, "w", encoding="utf-8") as f:
                    f.write("---\n")
                    yaml.dump(frontmatter_data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
                    f.write("---\n\n")
                    # Il corpo dell'articolo contiene l'Analisi Tecnica (Markdown)
                    f.write(analisi)
                
                print(f"  ✅ {filename}")

if __name__ == "__main__":
    process_excels()