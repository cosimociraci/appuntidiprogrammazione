import os
import pandas as pd
import re
import subprocess
from pathlib import Path

INPUT_DIR = "excel_input"
OUTPUT_DIR = "_articoli"

# Configurazione per Prettier
TECH_MAP = {
    "java": {"parser": "java", "plugin": "prettier-plugin-java"},
    "js": {"parser": "babel", "plugin": ""},
    "db": {"parser": "sql", "plugin": ""},
    "thymeleaf": {"parser": "html", "plugin": ""}
}

def format_code(code_text, tech):
    """Formatta il codice usando npx prettier"""
    code = str(code_text).replace("\\n", "\n").strip()
    conf = TECH_MAP.get(tech.lower(), {"parser": "babel", "plugin": ""})
    
    try:
        cmd = ['npx', 'prettier', '--parser', conf["parser"], '--tab-width', '4']
        if conf["plugin"]:
            cmd.extend(['--plugin', conf["plugin"]])
        
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        stdout, _ = p.communicate(input=code)
        return stdout.strip() if p.returncode == 0 else code
    except:
        return code

def sanitize_filename(text):
    s = str(text).lower()
    s = re.sub(r'[^a-z0-9\s-]', '', s)
    return re.sub(r'[\s-]+', '-', s).strip('-')

def clean_excel_text(text):
    if pd.isna(text): return ""
    return str(text).replace("\\n", "\n").replace("\r", "")

def process_excels():
    out_path = Path(OUTPUT_DIR)
    out_path.mkdir(parents=True, exist_ok=True)
    
    for old_file in out_path.glob("*.md"):
        old_file.unlink()

    excel_files = list(Path(INPUT_DIR).glob("*.xlsx"))
    
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
                time_str = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S %z')
                filename = f"{date_str}-{sanitize_filename(titolo)}.md"
                
                analisi = clean_excel_text(row.get('ANALISI TECNICA', ''))
                esigenza = clean_excel_text(row.get('ESIGENZA REALE', ''))
                sintesi_raw = clean_excel_text(row.get('SINTESI DEL PROBLEMA', ''))
                sintesi = sintesi_raw.replace("\n", " ").strip()[:250]
                
                code_cols = [col for col in df.columns if 'ESEMPIO' in col and pd.notna(row[col])]
                raw_code = "\n".join([clean_excel_text(row[col]) for col in code_cols])
                
                # FORMATTAZIONE ATTIVA
                full_code = format_code(raw_code, tech_name)
                
                tags = [tech_name, sheet_name.lower().replace("_", " ")]
                pdf_name = f"{sanitize_filename(titolo)}.pdf"

                with open(out_path / filename, "w", encoding="utf-8") as f:
                    f.write("---\n")
                    f.write(f"layout: post\n")
                    f.write(f"title: \"{titolo}\"\n")
                    f.write(f"date: {time_str}\n")
                    f.write(f"sintesi: \"{sintesi}\"\n")
                    f.write(f"tech: {tech_name}\n")
                    f.write(f"tags: {tags}\n")
                    f.write(f"pdf_file: \"{pdf_name}\"\n")
                    f.write("---\n\n")
                    
                    if esigenza: f.write(f"## Esigenza Reale\n{esigenza}\n\n")
                    if analisi: f.write(f"## Analisi Tecnica\n{analisi}\n\n")
                    if full_code:
                        f.write(f"## Esempio Implementativo\n\n")
                        f.write(f"```{tech_name}\n")
                        f.write(f"{full_code}\n")
                        f.write(f"```\n")
                
                print(f"  ✅ {filename}")

if __name__ == "__main__":
    process_excels()