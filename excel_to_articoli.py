import os
import pandas as pd
import re
import textwrap
from pathlib import Path
import code_formatter as cf

# --- CONFIGURAZIONE ---
INPUT_DIR = "excel_input"
OUTPUT_DIR = "_articoli"
CALENDARIO_CSV = "generazione_slide/calendario_instagram.csv"
MAX_CHARS_WIDTH = 80

# Mappatura dei linguaggi per il rendering di Jekyll/Rouge
# Forza Thymeleaf e altri formati verso Java o HTML per attivare l'highlighting
LANG_MAP = {
    "thymeleaf": "java",  # Thymeleaf lato Java/Spring
    "db": "sql",
    "js": "javascript",
    "vanillajs": "javascript",
    "html": "html"
}

def normalize_for_match(text):
    if not isinstance(text, str):
        return ""
    text = re.sub(r'[^a-zA-Z0-9]', ' ', text)
    return " ".join(text.split()).lower().strip()


def load_calendar():
    calendar_dict = {}
    if os.path.exists(CALENDARIO_CSV):
        df_cal = pd.read_csv(CALENDARIO_CSV)
        df_cal.columns = [c.strip() for c in df_cal.columns]
        for _, row in df_cal.iterrows():
            data_val = str(row.iloc[0]).strip()
            chiave_csv = normalize_for_match(str(row.iloc[2]))
            calendar_dict[chiave_csv] = data_val
    return calendar_dict


def _sanitize_raw_code(code_text: str) -> str:
    """
    Normalizzo il codice grezzo che arriva da una cella Excel prima di
    passarlo al formatter. Gestisco tutti i formati che Excel può produrre:

    1. \r\n (Windows CRLF)        → collasso in \n
    2. \\n letterali (due char)   → converto in \n reali
    3. \xa0 (nbsp da Excel)       → spazio normale
    4. Marcatori ```lang```        → rimuovo
    5. Spazi multipli residui     → non tocco: ci pensa il formatter
    """
    code = str(code_text)

    # Passo 1: rimuovo il carattere null e nbsp di Excel
    code = code.replace('\x00', '').replace('\xa0', ' ')

    # Passo 2: normalizzo CRLF Windows in LF
    code = code.replace('\r\n', '\n').replace('\r', '\n')

    # Passo 3: converto i \n letterali (backslash + n) in newline reali.
    # BUG ORIGINALE: questo veniva fatto solo FUORI da format_code_pro,
    # quindi le celle con \\n letterali arrivavano piatte al formatter.
    code = code.replace('\\n', '\n')

    # Passo 4: rimuovo i marcatori di blocco codice tipo ```java o ```
    code = re.sub(r'```[a-zA-Z]*\n?', '', code).replace('```', '')

    return code.strip()


def format_code_pro(code_text, tech: str) -> str:
    """
    Formatta il codice usando code_formatter, con preprocessing robusto
    dell'input grezzo da Excel.

    Il flusso è:
      cella Excel → _sanitize_raw_code() → normalize_to_lines() → indent_lines()
      → wrap righe troppo lunghe → testo formattato
    """
    if not code_text or str(code_text).strip() in ('', 'nan'):
        return ""

    # Normalizzo il codice grezzo: gestisco tutti i formati Excel in un posto solo
    code = _sanitize_raw_code(code_text)

    if not code:
        return ""

    # Uso la LANG_MAP per decidere quale formatter usare internamente
    actual_tech = LANG_MAP.get(tech.lower(), tech.lower())

    try:
        lines         = cf.normalize_to_lines(code, actual_tech)
        indented_lines = cf.indent_lines(lines, actual_tech)

        final_lines = []
        for line in indented_lines:
            clean_line = line.rstrip()
            if not clean_line:
                continue

            if len(clean_line) <= MAX_CHARS_WIDTH:
                final_lines.append(clean_line)
            else:
                # La riga è troppo lunga (tipico nei commenti /* ... */):
                # la spezziamo preservando il livello di indentazione attuale.
                indent_len = len(clean_line) - len(clean_line.lstrip())
                sub_indent = " " * indent_len

                # ATTENZIONE: uso replace_whitespace=False e break_on_hyphens=False
                # per non rompere identificatori Java come "getAllowedPage-list"
                # e per preservare gli spazi interni alle stringhe.
                wrapped = textwrap.fill(
                    clean_line,
                    width=MAX_CHARS_WIDTH,
                    subsequent_indent=sub_indent + "    ",
                    expand_tabs=False,
                    replace_whitespace=False,
                    break_on_hyphens=False,
                )
                final_lines.append(wrapped)

        return "\n".join(final_lines)

    except Exception as e:
        print(f"⚠️  Errore nel formatter per tech='{actual_tech}': {e}")
        # Restituisco il codice grezzo sanificato come fallback
        return code


def sanitize_filename(text: str) -> str:
    s = str(text).lower()
    s = re.sub(r'[^a-z0-9\s-]', '', s)
    return re.sub(r'[\s-]+', '-', s).strip('-')


def process_excels():
    input_path = Path(INPUT_DIR)
    out_path   = Path(OUTPUT_DIR)

    if not input_path.exists():
        print(f"Directory di input '{INPUT_DIR}' non trovata.")
        return

    calendario = load_calendar()
    out_path.mkdir(parents=True, exist_ok=True)

    # Pulisco i file .md precedenti
    for old_file in out_path.glob("*.md"):
        old_file.unlink()

    for file in input_path.glob("*.xlsx"):
        tech_prefix = file.stem.capitalize()
        tech_name   = file.stem.lower()

        try:
            xls = pd.ExcelFile(file)
            for sheet_name in xls.sheet_names:
                df = pd.read_excel(file, sheet_name=sheet_name)
                df.columns = [str(c).strip().upper() for c in df.columns]

                for idx, row in df.iterrows():
                    titolo_originale = str(row.get('TITOLO', f'Topic-{idx}'))
                    chiave_ricerca   = normalize_for_match(f"{tech_prefix}: {titolo_originale}")
                    data_prefisso    = calendario.get(chiave_ricerca, "0000-00-00")

                    titolo_clean = (titolo_originale
                                    .replace('"', '')
                                    .replace("'", "")
                                    .encode('ascii', 'ignore')
                                    .decode('ascii'))
                    filename = f"{data_prefisso}-{sanitize_filename(titolo_clean)}.md"

                    # Per le sezioni testuali converto \\n in spazi (Markdown inline)
                    sintesi = (str(row.get('SINTESI DEL PROBLEMA', ''))
                               .replace("\\n", " ")
                               .replace("\n", " ")
                               .strip()[:250])

                    # Raccolgo le colonne ESEMPIO e le passo DIRETTAMENTE a format_code_pro.
                    # BUG ORIGINALE: il replace("\\n", "\n") veniva fatto qui fuori,
                    # ma format_code_pro non lo ripeteva internamente.
                    # FIX: _sanitize_raw_code() dentro format_code_pro gestisce tutto.
                    code_cols = [
                        col for col in df.columns
                        if 'ESEMPIO' in col and pd.notna(row[col])
                    ]
                    # Unisco le colonne con un newline e passo tutto in un colpo solo
                    raw_code = "\n".join(str(row[col]) for col in code_cols)

                    formatted_code = format_code_pro(raw_code, tech_name)
                    # Determino il tag del blocco di codice per il file Markdown
                    code_lang = LANG_MAP.get(tech_name, tech_name)

                    with open(out_path / filename, "w", encoding="utf-8") as f:
                        f.write("---\n")
                        f.write(f"layout: post\n"
                                f"title: \"{titolo_clean}\"\n"
                                f"date: {data_prefisso} 12:00:00\n")
                        f.write(f"sintesi: >\n  {sintesi}\n"
                                f"tech: \"{code_lang}\"\n")
                        f.write(f"tags: [\"{tech_name}\", \"{sheet_name.lower().strip()}\"]\n"
                                f"pdf_file: \"{sanitize_filename(titolo_clean)}.pdf\"\n"
                                f"---\n\n")

                        for section in ['ESIGENZA REALE', 'ANALISI TECNICA']:
                            # Per le sezioni testuali: \\n letterali → \n Markdown
                            content = str(row.get(section, '')).replace("\\n", "\n")
                            if content and content != 'nan':
                                f.write(f"## {section.title()}\n{content}\n\n")

                        if formatted_code:
                            f.write(f"## Esempio Implementativo\n\n"
                                    f"```{code_lang}\n{formatted_code}\n```\n")

                    print(f"✅ Generato: {filename}")

        except Exception as e:
            print(f"❌ Errore critico in {file.name}: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    process_excels()