"""
Formattatore di codice multi-linguaggio v8.
Preserva le interfacce normalize_to_lines e indent_lines.
Aggiunge rifinitura tramite Prettier e post-processing per i commenti a blocco.
"""

import os
import re
import sys
import subprocess

# Indentazione standard 4 spazi per la logica custom
INDENT = "    "

CURLY_BRACE_LANGUAGES = {"java", "javascript", "js", "typescript", "ts", "c", "cpp", "csharp", "cs", "php", "kotlin"}
SQL_LANGUAGES = {"sql", "plpgsql"}
MARKUP_LANGUAGES = {"html", "xml", "thymeleaf", "svg"}

_CODE = 0
_STRING_DOUBLE = 1
_STRING_SINGLE = 2
_COMMENT_LINE = 3
_COMMENT_BLOCK = 4

_RE_BREAK_KEYWORDS = re.compile(r'^(public|protected|private|static|final|class|interface|enum|record|@|void|return|if|for|while)\b', re.IGNORECASE)

# ─────────────────────────────────────────────
# LOGICA DI POST-PROCESSING (Commenti)
# ─────────────────────────────────────────────

def enforce_comment_newlines(code: str) -> str:
    """
    Applica la regola ferrea:
    - Prima di /* ci deve essere \n
    - Dopo */ ci deve essere \n
    Gestisce anche la pulizia di eventuali spazi bianchi multipli creati.
    """
    # 1. Inserisco i newline intorno ai blocchi di commento
    # Uso lookahead/lookbehind per evitare di aggiungere newline se già presenti
    code = re.sub(r'(?<!\n)\s*/\*', r'\n\n/*', code)
    code = re.sub(r'\*/\s*(?!\n)', r'*/\n\n', code)
    
    # 2. Pulizia: rimuovo righe vuote eccessive create dal passaggio precedente
    # (Ad esempio se c'erano già spazi o tab prima/dopo)
    lines = [line.rstrip() for line in code.splitlines()]
    return "\n".join(lines)

# ─────────────────────────────────────────────
# INTEGRAZIONE PRETTIER
# ─────────────────────────────────────────────

def format_with_prettier(code_string: str, language: str) -> str:
    parser_map = {
        "java": "java",
        "javascript": "babel",
        "js": "babel",
        "typescript": "typescript",
        "ts": "typescript",
        "html": "html",
        "thymeleaf": "html",
        "xml": "html",
        "css": "css"
    }
    
    parser = parser_map.get(language.lower())
    if not parser:
        return code_string

    try:
        process = subprocess.Popen(
            ['npx', 'prettier', '--parser', parser, '--tab-width', '4'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=True if os.name == 'nt' else False
        )
        stdout, stderr = process.communicate(input=code_string)
        
        if process.returncode == 0:
            return stdout
        else:
            return f"/* Prettier Err: {stderr.strip()} */\n{code_string}"
            
    except FileNotFoundError:
        return f"/* Prettier non trovato nel sistema */\n{code_string}"

# ─────────────────────────────────────────────
# NORMALIZZAZIONE E INDENTAZIONE
# ─────────────────────────────────────────────

def _normalize_curly_logic(code: str) -> list:
    result = []
    buf = []
    state = _CODE
    i = 0
    n = len(code)

    def emit_buf():
        content = "".join(buf).strip()
        if content:
            result.append(" ".join(content.split()))
        buf.clear()

    while i < n:
        ch = code[i]
        next_ch = code[i+1] if i+1 < n else ""

        if state == _COMMENT_LINE:
            if ch == "\n":
                emit_buf(); state = _CODE; i += 1
            elif ch in "{};" or (ch == "r" and code[i:i+7] == "return "):
                emit_buf(); state = _CODE
            else:
                buf.append(ch); i += 1
            continue

        if state == _COMMENT_BLOCK:
            buf.append(ch)
            if ch == "*" and next_ch == "/":
                buf.append("/"); i += 2; state = _CODE; emit_buf()
            else: i += 1
            continue

        if state in (_STRING_DOUBLE, _STRING_SINGLE):
            quote = '"' if state == _STRING_DOUBLE else "'"
            buf.append(ch)
            if ch == "\\" and next_ch:
                buf.append(next_ch); i += 2
            elif ch == quote:
                state = _CODE; i += 1
            else: i += 1
            continue

        if ch == "/" and next_ch == "*":
            emit_buf(); buf.append("/*"); state = _COMMENT_BLOCK; i += 2
        elif ch == "/" and next_ch == "/":
            emit_buf(); buf.append("//"); state = _COMMENT_LINE; i += 2
        elif ch in ";{":
            buf.append(ch); emit_buf(); i += 1
        elif ch == "}":
            emit_buf(); result.append("}"); i += 1
        elif ch == "@":
            emit_buf(); buf.append("@"); i += 1
        elif ch.isspace():
            word = "".join(buf).strip()
            if word == "return" or _RE_BREAK_KEYWORDS.match(word):
                temp_word = word
                buf.clear()
                emit_buf()
                buf.append(temp_word + " ")
            else:
                buf.append(" ")
            i += 1
        else:
            buf.append(ch); i += 1

    emit_buf()
    return [l for l in result if l]

def normalize_to_lines(code: str, language: str) -> list:
    if language in CURLY_BRACE_LANGUAGES:
        return _normalize_curly_logic(code)
    if language in MARKUP_LANGUAGES:
        parts = re.split(r'(<[^>]+>|/\*.*?\*/|//.*?\n)', code, flags=re.DOTALL)
        return [p.strip() for p in parts if p.strip()]
    return [l.strip() for l in code.splitlines() if l.strip()]

def indent_lines(lines: list, language: str) -> list:
    formatted = []
    depth = 0
    
    if language in SQL_LANGUAGES:
        for l in lines:
            s = l.strip()
            if re.match(r'^(SELECT|INSERT|UPDATE|DELETE|FROM|WHERE|JOIN|GROUP|ORDER|LIMIT)', s, re.I):
                formatted.append(s)
            else:
                formatted.append(INDENT + s)
        return formatted

    for line in lines:
        s = line.strip()
        if not s: continue
        is_closing = s.startswith("}") or s.startswith("</") or s.endswith("]]>")
        if is_closing:
            depth = max(0, depth - 1)
        
        formatted.append(INDENT * depth + s)
        
        is_opening = (
            (s.endswith("{") or s == "{") or 
            (s.startswith("<") and not s.startswith("</") and not s.endswith("/>") and not s.startswith("<!"))
        )
        if is_opening:
            depth += 1
            
    return formatted

# ─────────────────────────────────────────────
# ESECUZIONE
# ─────────────────────────────────────────────

def detect_language(code: str) -> str:
    # Provo a dedurre il linguaggio dal contenuto
    if "@" in code or "public class" in code or "private " in code: return "java"
    if "th:" in code or "<html" in code or "</div>" in code: return "thymeleaf"
    if "const " in code or "let " in code or "function(" in code: return "javascript"
    if "SELECT " in code.upper(): return "sql"
    return "java"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python code_formatter.py <file_input>")
        sys.exit(1)

    with open(sys.argv[1], "r", encoding="utf-8") as f:
        raw_content = f.read()

    lang = detect_language(raw_content)

    # 1. Normalizzazione
    lines = normalize_to_lines(raw_content, lang)
    
    # 2. Prima Indentazione
    custom_formatted_list = indent_lines(lines, lang)
    custom_formatted_string = "\n".join(custom_formatted_list)
    
    # 3. Passaggio Prettier
    prettier_output = format_with_prettier(custom_formatted_string, lang)
    
    # 4. Post-processing commenti (Regola \n /* ... */ \n)
    final_output = enforce_comment_newlines(prettier_output)
    
    print(final_output)