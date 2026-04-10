# pipenv run python genera_notizie_2.py

import os
import json
import asyncio
import re
import sys
import argparse
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import yt_dlp
import whisper
import ollama
from playwright.async_api import async_playwright

# --- CONFIGURAZIONE ---
TARGET_TOPICS = ["java", "js", "javascript", "postgresql", "postgis", "ai", "ia", "intelligenza artificiale"]
BASE_URLS = [
    "https://techfromthenet.it/software/news-produttivita/",
    "https://www.infoq.com/java/news/",
    "https://inside.java/",
    "https://www.zeusnews.it/"
]

# Ho spostato il path della cache qui in configurazione per averlo in un posto solo
CACHE_FILE = "news/processed_urls.json"

TECH_PALETTE = {
    "java": {
        "accent": "#f89820",
        "bg": "#FFF9F2",
        "label": "JAVA",
        "highlights": ["Java", "JVM", "Spring", "Maven", "Gradle"]
    },
    "js": {
        "accent": "#F7DF1E",
        "bg": "#FFFFF0",
        "label": "JAVASCRIPT",
        "highlights": ["JavaScript", "Node", "npm", "ES6", "async"]
    },
    "postgresql": {
        "accent": "#336791",
        "bg": "#F0F5F9",
        "label": "POSTGRESQL",
        "highlights": ["PostgreSQL", "SQL", "query", "index", "PostGIS"]
    },
    "ia": {
        "accent": "#8E44AD",
        "bg": "#F8F4FB",
        "label": "AI & INNOVATION",
        "highlights": ["AI", "LLM", "modello", "training", "inferenza"]
    },
    "default": {
        "accent": "#2ECC71",
        "bg": "#F2FBF6",
        "label": "TECH NEWS",
        "highlights": []
    }
}


def log(message):
    """Stampo un log con timestamp dettagliato per monitorare i tempi di esecuzione."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{timestamp} - {message}")
    sys.stdout.flush()


def parse_arguments():
    """Configuro argparse per gestire tutte le modalità operative da terminale.
    Ho aggiunto --date come parametro opzionale: se non specificato il valore
    viene calcolato a runtime come data odierna, così non devo più modificare
    il sorgente ad ogni esecuzione."""
    parser = argparse.ArgumentParser(description="Sistema di generazione articoli e slide tecniche.")
    parser.add_argument(
        '--date',
        type=str,
        default=None,
        help='Data di sessione nel formato YYYY-MM-DD (es: 2026-04-09). Se omessa usa la data odierna.'
    )
    parser.add_argument(
        '--regenerate',
        action='store_true',
        help='Itera su tutti i file .md in news/ e rigenera tutte le immagini. Non scarica nulla.'
    )
    parser.add_argument(
        '--cta-only',
        action='store_true',
        help='Rigenera solo la slide CTA finale (icarocomix) in ogni cartella di news. Non scarica nulla.'
    )
    parser.add_argument(
        '--fix-frontmatter',
        action='store_true',
        help='Rigenera il front matter YAML di tutti i file .md in news/. Non scarica nulla, non rigenera immagini.'
    )
    return parser.parse_args()


def resolve_session_date(date_arg):
    """Risolvo la data di sessione dal parametro CLI oppure dalla data odierna.
    Valido il formato YYYY-MM-DD con uno strptime: se il formato è errato sollevo
    un errore esplicito invece di procedere con una data malformata che
    corromperebbe i nomi delle cartelle e i front matter dei file .md."""
    if date_arg is not None:
        try:
            datetime.strptime(date_arg, "%Y-%m-%d")
            return date_arg
        except ValueError:
            log(f"ERRORE: --date '{date_arg}' non è nel formato YYYY-MM-DD. Esempio corretto: 2026-04-09")
            sys.exit(1)
    # Nessun parametro fornito: uso la data odierna calcolata a runtime.
    # Questo evita di dover modificare il sorgente ad ogni nuova esecuzione giornaliera.
    return datetime.now().strftime("%Y-%m-%d")


log("Inizializzazione Whisper (modello base)...")
whisper_model = whisper.load_model("base")


# --- CACHE ---

def load_cache():
    """Carico il file di cache che mappa ogni URL processato al path del suo file .md.
    Se il file non esiste lo inizializzo come dizionario vuoto: questo accade solo
    alla prima esecuzione, dopodiché la cache persiste tra una sessione e l'altra."""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log(f"Cache corrotta o illeggibile, la azzero: {e}")
    return {}


def save_cache(cache):
    """Persisto la cache su disco dopo ogni nuovo URL processato.
    Scrivo subito invece di farlo solo a fine sessione per non perdere
    dati in caso di crash durante elaborazioni successive."""
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


# --- UTILS ---

def slugify(text):
    """Converto il titolo in un formato adatto ai nomi delle cartelle."""
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    return re.sub(r'[-\s]+', '-', text).strip('-')


def find_youtube_links(soup):
    """Identifico link YouTube nel corpo della pagina, escludendo duplicati."""
    yt_links = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        if "youtube.com/watch" in href or "youtu.be/" in href:
            clean_url = href.split('&')[0]
            yt_links.append(clean_url)
    return list(set(yt_links))


def extract_article_data(url):
    """Recupero il testo dell'articolo e identifico link video tramite scraping BeautifulSoup."""
    try:
        log(f"Analisi testuale (Scraping): {url}")
        resp = requests.get(url, timeout=15)
        soup = BeautifulSoup(resp.text, 'html.parser')

        video_links = find_youtube_links(soup)

        # Pulisco il DOM dagli elementi di disturbo
        for tag in soup(['nav', 'footer', 'header', 'aside', 'script', 'style']):
            tag.decompose()

        # Cerco il contenitore principale del testo
        article_body = (soup.find('article') or
                        soup.find('main') or
                        soup.find('div', id=re.compile('entry|content|post')))

        text = article_body.get_text(separator='\n', strip=True) if article_body else soup.get_text(separator='\n', strip=True)
        return text, video_links
    except Exception as e:
        log(f"Errore durante lo scraping di {url}: {e}")
        return "", []


def transcribe_video(url):
    """Scarico l'audio del video con yt-dlp e lo trascrivo con Whisper."""
    log(f"Elaborazione video rilevato: {url}")
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'temp_audio.%(ext)s',
        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'}],
        'quiet': True, 'no_warnings': True
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        log("Whisper sta elaborando la trascrizione...")
        result = whisper_model.transcribe("temp_audio.mp3")

        if os.path.exists("temp_audio.mp3"):
            os.remove("temp_audio.mp3")

        return result['text']
    except Exception as e:
        log(f"Errore download/trascrizione: {e}")
        return ""


# --- FILTRO CONTENUTO PROMOZIONALE ---

def is_promotional(full_context):
    """Chiedo a Qwen di valutare se il contenuto è una notizia tecnica reale o materiale promozionale.
    Ho scelto un modello leggero come Qwen per questo filtro rapido, riservando Mistral solo
    alla generazione dell'articolo completo. La risposta attesa è solo 'NOTIZIA' o 'PUBBLICITA'
    per poterla parsare in modo affidabile senza ambiguità."""
    log("[Qwen] Analisi anti-promozionale in corso...")
    prompt = f"""
Sei un editor di una rivista tecnica. Analizza il testo seguente e rispondi a questa domanda:
si tratta di una notizia su una novità tecnologica rilevante (nuova versione di software, scoperta, 
standard, ricerca, aggiornamento di un progetto open source, annuncio di un colosso IT come Google, 
Microsoft, Oracle, Meta, Apple, Amazon, Red Hat) OPPURE è materiale promozionale/pubblicitario 
(comunicato stampa aziendale, lancio di prodotto commerciale di azienda non nota, integrazione di 
servizi a pagamento, annuncio di partnership senza valore tecnico)?

TESTO:
{full_context[:5000]}

Rispondi con una sola parola:
- NOTIZIA se è una novità tecnica genuina
- PUBBLICITA se è materiale promozionale

Non aggiungere nulla altro. Solo una parola.
"""
    try:
        response = ollama.chat(model='qwen2.5-coder', messages=[{'role': 'user', 'content': prompt}])
        answer = response['message']['content'].strip().upper()
        # Cerco la parola chiave nella risposta per tollerare piccole variazioni del modello
        return "PUBBLICITA" in answer
    except Exception as e:
        log(f"Errore nel filtro promozionale, assumo notizia valida: {e}")
        return False


# --- INTELLIGENZA ARTIFICIALE ---
def generate_article(full_context, source_url):
    """Mistral crea l'articolo tecnico in italiano partendo dal contesto raccolto."""
    log("[Mistral] Avvio stesura nuovo articolo tecnico...")
    prompt = f"""
Sei un programmatore senior che scrive un articolo per il proprio blog tecnico personale.
Scrivi in ITALIANO, in PRIMA PERSONA, come se stessi condividendo ciò che hai appreso e sperimentato direttamente.

CONTESTO SORGENTE:
{full_context[:15000]}

REGOLE OBBLIGATORIE:
1. Formato output: Markdown (.md) puro. NON scrivere mai un titolo H1 (riga con "#").
   Il titolo è già gestito dal sistema: inizia direttamente con la prima sezione.
   - Le sezioni DEVONO iniziare con "## " (due cancelletti seguiti da spazio).
     ESEMPI CORRETTI:   ## Cosa cambia nel GC
     ESEMPI SBAGLIATI:  # Cosa cambia  |  ### Cosa cambia  |  Cosa cambia:
   - NON usare mai la parola "Titolo:" o "Sezione:" come prefisso.
2. Stile: Prima persona singolare ("Ho analizzato...", "Ho scoperto che...", "A mio avviso..."). Mai tono impersonale o accademico.
3. Privacy: Non citare mai nomi propri di persone fisiche. Usa espressioni come "il team di sviluppo", "gli autori", "i maintainer".
4. Lingua: Se il materiale sorgente è in inglese, traduci accuratamente tutti i concetti. I termini tecnici consolidati (es. "thread", "query", "build") restano in inglese.
5. Profondità: Approfondisci i concetti tecnici con esempi concreti. Non limitarti a riassumere: aggiungi contesto, confronti e implicazioni pratiche.
6. Chiusura: Termina l'articolo con una riga '---' seguita da 'Fonte originale: {source_url}'.
"""
    response = ollama.chat(model='mistral', messages=[{'role': 'user', 'content': prompt}])
    # Sanificare sempre l'output: Mistral ignora le istruzioni di formato
    # in modo non deterministico, quindi non mi fido del solo prompt.
    return sanitize_article_headings(response['message']['content'])


def sanitize_article_headings(article):
    """Normalizzo i titoli dell'articolo prodotto da Mistral correggendo i problemi
    ricorrenti di formattazione.

    Poiché il front matter contiene già il campo 'title' che il layout Jekyll
    renderizza come H1, il corpo del Markdown NON deve contenere nessun '#'.
    Tutta la gerarchia parte da '##' per le sezioni principali.

    Logica applicata riga per riga:
    - Righe "Titolo: ..." o "# Titolo: ..." → rimosse completamente perché
      il titolo è già nel front matter, duplicarlo nel corpo è un errore.
    - Righe "# testo" (H1 nel corpo) → degradate a "## testo".
    - Righe "### testo" o livelli più profondi → degradate a "## testo"
      per mantenere la gerarchia piatta attesa dal CSS.
    - Righe "#testo" senza spazio → corrette in "## testo".
    - Tutte le altre righe → invariate."""

    lines = article.split('\n')
    result = []

    for line in lines:
        stripped = line.strip()

        # Caso 1: riga "Titolo: ..." con eventuale prefisso di cancelletti.
        # La rimuovo del tutto: il titolo vive nel front matter, non nel corpo.
        if re.match(r'^#{0,3}\s*[Tt]itolo:\s*.+', stripped):
            continue

        # Caso 2: riga che inizia con "#" ma senza spazio separatore
        # es: "#Introduzione" → normalizzo prima di valutare il livello.
        if re.match(r'^#{1,6}[^\s#]', stripped):
            stripped = re.sub(r'^(#{1,6})([^\s])', r'\1 \2', stripped)

        # Caso 3: H1 nel corpo ("# testo") → degrado a H2.
        # Il titolo H1 è responsabilità del layout, non del Markdown.
        if re.match(r'^#\s', stripped):
            stripped = re.sub(r'^#\s', '## ', stripped)

        # Caso 4: H3 o più profondi ("### testo", "#### testo" ...) → degrado a H2
        # per mantenere la struttura piatta a un solo livello di sezione.
        if re.match(r'^#{3,}\s', stripped):
            stripped = re.sub(r'^#{3,}\s', '## ', stripped)

        result.append(stripped)

    return '\n'.join(result)

def extract_slides(article):
    """Qwen estrae i punti chiave per il carosello grafico in formato JSON.
    Ho reso le istruzioni più esigenti sul livello di dettaglio: ogni pillola deve
    contenere abbastanza contesto da essere comprensibile anche senza leggere l'articolo,
    che è il caso reale d'uso sui social dove lo slide è l'unico touchpoint."""
    log("[Qwen] Estrazione pillole carosello...")
    prompt = f"""
Sei un content designer tecnico specializzato in divulgazione per sviluppatori.
Analizza l'articolo seguente ed estrai esattamente 9 pillole informative in ITALIANO.

ARTICOLO:
{article}

REGOLE OBBLIGATORIE:
1. Contesto esplicito: ogni pillola deve menzionare esplicitamente il tema dell'articolo
   (es: non scrivere "il nuovo sistema riduce la latenza del 40%" ma 
   "PostgreSQL 17 introduce il connection pooling nativo, riducendo la latenza del 40%").
2. Autonomia: ogni pillola deve essere comprensibile senza aver letto l'articolo o le altre pillole.
3. Massimo 5 righe per pillola. Frasi brevi, dirette, dense di informazione tecnica.
4. Privilegia: numeri concreti, confronti tra versioni, impatti pratici, breaking change, casi d'uso reali.
5. NON usare markdown (no asterischi, no simboli #, no trattini iniziali). Solo testo piano.
6. Restituisci ESCLUSIVAMENTE un array JSON di 9 stringhe, senza alcun testo prima o dopo, senza backtick.

Esempio formato atteso:
["Pillola uno con contesto esplicito.", "Pillola due con contesto esplicito.", ...]
"""
    response = ollama.chat(model='qwen2.5-coder', messages=[{'role': 'user', 'content': prompt}])
    raw = response['message']['content']

    # Primo tentativo: cerco il blocco JSON grezzo e lo parso direttamente.
    match = re.search(r'\[.*\]', raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError as e:
            log(f"JSON grezzo non valido ({e}), avvio pulizia e secondo tentativo...")

    # Secondo tentativo: il modello ha restituito JSON malformato (ellissi, virgolette
    # non escapate, caratteri speciali). Provo a risanarlo prima di abbandonare.
    if match:
        cleaned = match.group()
        # Rimuovo caratteri di controllo non stampabili che rompono il parser JSON
        cleaned = re.sub(r'[\x00-\x1f\x7f]', ' ', cleaned)
        # Normalizzo le ellissi tipografiche in punti semplici
        cleaned = cleaned.replace('…', '...').replace('\u2026', '...')
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            log(f"Pulizia insufficiente ({e}), avvio estrazione manuale delle stringhe...")

    # Terzo tentativo (fallback finale): estraggo le stringhe una ad una con regex
    # ignorando completamente la struttura JSON. Funziona anche se il modello ha
    # restituito un array parziale o con delimitatori corrotti.
    candidates = re.findall(r'"((?:[^"\\]|\\.)*)"', raw)
    # Filtro stringhe troppo corte che sono probabilmente artefatti del formato JSON
    slides_fallback = [s.strip() for s in candidates if len(s.strip()) > 20]
    if slides_fallback:
        log(f"Estrazione manuale riuscita: recuperate {len(slides_fallback)} stringhe su 9 attese.")
        return slides_fallback[:9]

    # Nessun recupero possibile: restituisco lista vuota per non bloccare il flusso
    log("Impossibile estrarre slide dal modello, la generazione grafica verrà saltata.")
    return []


# --- ENGINE GRAFICO ---

def highlight_keywords(text, keywords, accent_color):
    """Sostituisco ogni parola chiave del topic con la sua versione in grassetto colorato.
    Uso word boundary \b per evitare sostituzioni parziali e re.escape per gestire
    eventuali caratteri speciali nei termini della palette."""
    for keyword in keywords:
        pattern = re.compile(r'\b' + re.escape(keyword) + r'\b')
        replacement = f"<b style='color:{accent_color}'>{keyword}</b>"
        text = pattern.sub(replacement, text)
    return text


async def create_images(topic, slides, folder_path):
    """Rendering delle slide 1080x1080 con numerazione progressiva."""
    log(f"Rendering grafico per topic: {topic} in {folder_path}...")

    # Rimuovo eventuali slide precedenti prima di rigenerare
    for f in os.listdir(folder_path):
        if f.endswith(".png"):
            os.remove(os.path.join(folder_path, f))

    config = TECH_PALETTE.get(topic.lower(), TECH_PALETTE["default"])

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={'width': 1080, 'height': 1080})

        for i, text in enumerate(slides[:9]):
            formatted_text = highlight_keywords(text, config['highlights'], config['accent'])

            # Ho aggiunto l'import di Google Fonts Poppins nel <head> perché Playwright
            # opera in un browser headless che non eredita i font di sistema.
            # wait_until="networkidle" garantisce che il font sia scaricato prima dello screenshot.
            html_content = f"""
            <html>
            <head>
                <link rel="preconnect" href="https://fonts.googleapis.com">
                <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
                <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@500;900&display=swap" rel="stylesheet">
            </head>
            <style>
                body {{
                    background: {config['bg']};
                    font-family: 'Poppins', sans-serif;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    height: 100vh;
                    margin: 0;
                    padding: 100px;
                    box-sizing: border-box;
                    position: relative;
                }}
                .container {{
                    width: 100%;
                    border-left: 20px solid {config['accent']};
                    padding-left: 60px;
                }}
                .label {{
                    font-weight: 900;
                    color: {config['accent']};
                    text-transform: uppercase;
                    font-size: 26px;
                    margin-bottom: 25px;
                    letter-spacing: 2px;
                }}
                .text {{
                    font-size: 42px;
                    line-height: 1.4;
                    color: #111;
                    font-weight: 500;
                }}
                .page-num {{
                    position: absolute;
                    bottom: 50px;
                    right: 80px;
                    font-size: 32px;
                    font-weight: 900;
                    color: {config['accent']};
                    opacity: 0.6;
                }}
            </style>
            <body>
                <div class="container">
                    <div class="label">{config['label']}</div>
                    <div class="text">{formatted_text}</div>
                </div>
                <div class="page-num">{i + 1}/9</div>
            </body>
            </html>"""

            await page.set_content(html_content, wait_until="networkidle")
            await page.screenshot(path=os.path.join(folder_path, f"slide_{i + 1}.png"))

        # Uso la funzione dedicata passando la page già aperta: evito di aprire
        # un secondo contesto Playwright all'interno dello stesso blocco async.
        cta_output_path = os.path.join(folder_path, "slide_11.png")
        await render_cta_slide(page, config['accent'], cta_output_path)
        await browser.close()


async def render_cta_slide(page, accent_color, output_path):
    """Genero la slide CTA icarocomix e la salvo nel path indicato.
    Ho separato questa logica da create_images per poterla richiamare anche in modalità
    --cta-only senza dover rieseguire l'intera pipeline di rendering delle slide contenuto.
    Il font-size è 45px come da specifica."""
    cta_html = f"""
    <html>
    <head>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@900&display=swap" rel="stylesheet">
    </head>
    <body style="background:{accent_color}; display:flex; align-items:center; justify-content:center;
                 height:100vh; color:white; font-family:'Poppins',sans-serif; text-align:center;
                 padding:50px; margin:0; box-sizing:border-box;">
        <h1 style="font-size:45px; font-weight:900;">icarocomix.github.io/<br>appuntidiprogrammazione</h1>
    </body>
    </html>"""
    await page.set_content(cta_html, wait_until="networkidle")
    await page.screenshot(path=output_path)


# --- FRONT MATTER ---

def generate_frontmatter(article, source_url, date_str):
    """Chiedo a Qwen di estrarre i metadati dell'articolo in JSON strutturato,
    poi assemblo il blocco YAML front matter da anteporre al file .md.

    Ho scelto Qwen per questo compito per coerenza con gli altri task di estrazione
    strutturata: è più veloce di Mistral e sufficiente per produrre campi brevi.
    Separo la generazione del front matter da quella dell'articolo per due ragioni:
    1. Mistral non produce YAML affidabile quando mescolato con testo libero lungo.
    2. Posso ritentare solo questo step senza rieseguire tutta la pipeline."""

    valid_tech_keys = list(TECH_PALETTE.keys())

    prompt = f"""
Analizza l'articolo tecnico seguente ed estrai i metadati richiesti.
Rispondi ESCLUSIVAMENTE con un oggetto JSON valido, senza backtick, senza testo prima o dopo.

ARTICOLO:
{article[:8000]}

CAMPI RICHIESTI:
- "title": titolo descrittivo dell'articolo in italiano (max 12 parole)
- "sintesi": riassunto dell'articolo in italiano, massimo 60 parole, max 3 righe,
             senza virgolette interne, senza newline
- "tech": una sola stringa tra queste esatte opzioni: {json.dumps(valid_tech_keys)}
- "tags": array JSON di 2-5 stringhe lowercase che identificano i temi principali

Esempio formato atteso:
{{"title": "Titolo esempio", "sintesi": "Breve riassunto senza newline.", "tech": "java", "tags": ["java", "jvm", "performance"]}}
"""
    try:
        response = ollama.chat(model='qwen2.5-coder', messages=[{'role': 'user', 'content': prompt}])
        raw = response['message']['content'].strip()

        # Estraggo il blocco JSON anche se il modello ha aggiunto testo
        # prima o dopo: cerco le parentesi graffe più esterne.
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if not match:
            raise ValueError("Nessun oggetto JSON trovato nella risposta del modello.")

        data = json.loads(match.group())

        # Normalizzo il campo tech: se il modello restituisce un valore non previsto
        # dalla palette, faccio fallback su "default" per non rompere il rendering grafico.
        tech = data.get("tech", "default").lower()
        if tech not in TECH_PALETTE:
            log(f"[FrontMatter] Tech '{tech}' non riconosciuto, uso 'default'.")
            tech = "default"

        # I tag li normalizzo tutti lowercase e rimuovo eventuali duplicati
        # preservando l'ordine di estrazione.
        raw_tags = data.get("tags", [tech])
        seen = set()
        tags = []
        for t in raw_tags:
            t_clean = str(t).lower().strip()
            if t_clean and t_clean not in seen:
                seen.add(t_clean)
                tags.append(t_clean)

        title    = str(data.get("title", "Articolo Tecnico")).replace('"', "'")
        sintesi  = str(data.get("sintesi", "")).replace('"', "'").replace('\n', ' ').strip()
        tags_yaml = json.dumps(tags, ensure_ascii=False)

        # Assemblo il front matter: uso la data della sessione con orario fisso 12:00:00
        # perché non ho un timestamp preciso di pubblicazione.
        # Il campo layout è sempre "post" per compatibilità con Jekyll/GitHub Pages.
        frontmatter = f"""---
layout: post
title: "{title}"
sintesi: >
  {sintesi}
date: {date_str} 12:00:00
tech: "{tech}"
tags: {tags_yaml}
link: "{source_url}"
---
"""
        return frontmatter, tech

    except Exception as e:
        log(f"[FrontMatter] Errore generazione metadati, uso front matter minimale: {e}")
        # Front matter di emergenza: non blocco la pipeline per un errore di metadati
        fallback = f"""---
layout: post
title: "Articolo Tecnico"
sintesi: >
  Articolo generato automaticamente.
date: {date_str} 12:00:00
tech: "default"
tags: ["tech"]
link: "{source_url}"
---
"""
        return fallback, "default"


def strip_existing_frontmatter(content):
    """Rimuovo il blocco frontmatter YAML iniziale se presente, restituendo il solo corpo .md.
    Il frontmatter Jekyll è delimitato da '---' in apertura e '---' in chiusura,
    entrambi su righe proprie. Uso una regex che consuma l'intera sezione inclusi i delimitatori,
    così il corpo che restituisco inizia direttamente con il titolo H1 dell'articolo.
    Se il file non ha frontmatter restituisco il contenuto invariato: la funzione è idempotente."""
    # Cerco il pattern ^---\n...\n---\n solo a inizio file con re.DOTALL per il corpo multi-riga
    match = re.match(r'^---\n.*?\n---\n', content, re.DOTALL)
    if match:
        return content[match.end():]
    return content


# --- MODALITÀ RIGENERAZIONE MASSIVA ---

async def regenerate_all(output_root):
    """Itero su tutte le cartelle di output e rigenero le immagini per ogni file .md trovato.
    Questa modalità non scarica nulla: legge solo file locali già presenti su disco.
    Ho separato questa logica dal main per tenere il flusso normale ben distinto
    dalla modalità di manutenzione."""
    log("--- MODALITÀ RIGENERAZIONE MASSIVA: nessun download verrà eseguito ---")
    for folder_name in sorted(os.listdir(output_root)):
        folder_path = os.path.join(output_root, folder_name)
        if not os.path.isdir(folder_path):
            continue
        md_files = [f for f in os.listdir(folder_path) if f.endswith(".md")]
        if not md_files:
            log(f"Nessun .md trovato in {folder_name}, salto.")
            continue
        md_path = os.path.join(folder_path, md_files[0])
        log(f"Rigenerazione: {md_path}")
        try:
            with open(md_path, "r", encoding="utf-8") as f:
                content = f.read()
            slides = extract_slides(content)
            topic_key = next((k for k in TECH_PALETTE if k in content.lower()), "default")
            await create_images(topic_key, slides, folder_path)
            log(f"Completato: {folder_name}")
        except Exception as e:
            log(f"Errore durante la rigenerazione di {folder_name}: {e}")
    log("--- RIGENERAZIONE MASSIVA COMPLETATA ---")


async def regenerate_cta_all(output_root):
    """Itero su tutte le cartelle di output e rigenero solo l'ultima slide (CTA icarocomix).
    Per trovare l'ultima slide non mi fido del numero fisso 11: conto i PNG presenti nella
    cartella e prendo quello con l'indice più alto, perché in sessioni precedenti Qwen potrebbe
    aver restituito meno di 9 pillole, spostando la CTA a un numero inferiore.
    Apro un unico browser Playwright per tutta la sessione e lo chiudo solo alla fine,
    evitando il costo di avvio/shutdown per ogni cartella."""
    log("--- MODALITÀ CTA-ONLY: rigenero solo la slide finale in ogni cartella ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={'width': 1080, 'height': 1080})

        for folder_name in sorted(os.listdir(output_root)):
            folder_path = os.path.join(output_root, folder_name)
            if not os.path.isdir(folder_path):
                continue

            # Raccolgo tutti i PNG con nome slide_N.png e li ordino per N numerico
            # per trovare l'ultimo indipendentemente da quanti ce ne siano.
            png_files = [
                f for f in os.listdir(folder_path)
                if re.match(r'^slide_\d+\.png$', f)
            ]
            if not png_files:
                log(f"Nessuna slide trovata in {folder_name}, salto.")
                continue

            last_slide = max(png_files, key=lambda f: int(re.search(r'\d+', f).group()))
            last_slide_path = os.path.join(folder_path, last_slide)

            # Determino il colore accent leggendo il file .md per applicare la palette corretta.
            # Se non trovo il .md uso il default verde: preferisco un colore sbagliato
            # a un crash che interrompe il batch su decine di cartelle.
            md_files = [f for f in os.listdir(folder_path) if f.endswith(".md")]
            accent_color = TECH_PALETTE["default"]["accent"]
            if md_files:
                try:
                    with open(os.path.join(folder_path, md_files[0]), "r", encoding="utf-8") as f:
                        md_content = f.read()
                    topic_key = next((k for k in TECH_PALETTE if k in md_content.lower()), "default")
                    accent_color = TECH_PALETTE[topic_key]["accent"]
                except Exception as e:
                    log(f"Impossibile leggere il topic da {folder_name}, uso default: {e}")

            try:
                await render_cta_slide(page, accent_color, last_slide_path)
                log(f"CTA rigenerata: {last_slide_path}")
            except Exception as e:
                log(f"Errore CTA su {folder_name}: {e}")

        await browser.close()
    log("--- CTA-ONLY COMPLETATA ---")


def fix_frontmatter_all(output_root):
    """Itero su tutte le cartelle di output e rigenero il frontmatter di ogni .md trovato.
    Per ogni file: strip del frontmatter esistente, chiamata a generate_frontmatter sul corpo
    pulito, riscrittura del file con il nuovo frontmatter anteposto.

    Ho scelto di non riscrivere il corpo dell'articolo: Mistral non viene reinvocato,
    solo Qwen estrae di nuovo titolo/sintesi/tech/tags dal testo già presente su disco.
    Questa modalità è veloce e non distruttiva sul contenuto."""
    log("--- MODALITÀ FIX-FRONTMATTER: rigenero le intestazioni di tutti i file .md ---")

    fixed_count = 0
    error_count = 0

    for folder_name in sorted(os.listdir(output_root)):
        folder_path = os.path.join(output_root, folder_name)
        if not os.path.isdir(folder_path):
            continue

        md_files = [f for f in os.listdir(folder_path) if f.endswith(".md")]
        if not md_files:
            log(f"Nessun .md in {folder_name}, salto.")
            continue

        md_path = os.path.join(folder_path, md_files[0])
        log(f"Fix frontmatter: {md_path}")

        try:
            with open(md_path, "r", encoding="utf-8") as f:
                raw_content = f.read()

            # Separo il corpo dal vecchio frontmatter (se presente).
            # strip_existing_frontmatter è idempotente: se il file non ha frontmatter
            # restituisce il contenuto invariato, quindi questa modalità è rieseguibile
            # più volte sullo stesso file senza duplicare l'intestazione.
            body = strip_existing_frontmatter(raw_content)
            body = sanitize_article_headings(body)

            # Estraggo il link sorgente dal corpo dell'articolo: Mistral lo scrive
            # sempre nell'ultima riga come "Fonte originale: <url>".
            # Se non lo trovo uso stringa vuota: preferisco campo link vuoto a un crash
            # che interrompe il batch su decine di file.
            source_url = ""
            url_match = re.search(r'Fonte originale:\s*(https?://\S+)', body)
            if url_match:
                source_url = url_match.group(1).rstrip('/')
            else:
                log(f"  Link sorgente non trovato in {md_files[0]}, campo link sarà vuoto.")

            # La data la ricavo dal nome della cartella che ha sempre il formato
            # YYYY-MM-DD-slug: prendo i primi 10 caratteri.
            # Se il nome non rispetta il pattern uso la data odierna come fallback.
            if re.match(r'^\d{4}-\d{2}-\d{2}', folder_name):
                date_str = folder_name[:10]
            else:
                date_str = datetime.now().strftime("%Y-%m-%d")
                log(f"  Pattern data non trovato in '{folder_name}', uso data odierna: {date_str}")

            frontmatter, _ = generate_frontmatter(body, source_url, date_str)
            final_md = frontmatter + body

            with open(md_path, "w", encoding="utf-8") as f:
                f.write(final_md)

            log(f"  Completato: {md_files[0]}")
            fixed_count += 1

        except Exception as e:
            log(f"  Errore su {folder_name}: {e}")
            error_count += 1

    log(f"--- FIX-FRONTMATTER COMPLETATO: {fixed_count} file aggiornati, {error_count} errori ---")


# --- MAIN ENGINE ---

async def main():
    args = parse_arguments()

    # Risolvo la data di sessione: da parametro CLI oppure data odierna.
    # Tutta la pipeline usa session_date invece della costante DEBUG_DATE
    # che ho rimosso per evitare di dover modificare il sorgente ogni giorno.
    session_date = resolve_session_date(args.date)

    log(f"--- START SESSION: {session_date} (Regenerate: {args.regenerate}, CTA-only: {args.cta_only}, Fix-frontmatter: {args.fix_frontmatter}) ---")

    output_root = "news"
    if not os.path.exists(output_root):
        os.makedirs(output_root)

    # Le modalità di manutenzione sono mutualmente esclusive con il flusso normale.
    # --cta-only ha precedenza su --regenerate che ha precedenza su --fix-frontmatter:
    # l'ordine riflette la distruttività decrescente sulle risorse (PNG vs .md).
    if args.cta_only:
        await regenerate_cta_all(output_root)
        return

    if args.regenerate:
        await regenerate_all(output_root)
        return

    if args.fix_frontmatter:
        # fix_frontmatter_all è sincrona: non usa Playwright né operazioni async.
        # La chiamo direttamente senza await.
        fix_frontmatter_all(output_root)
        return

    # Carico la cache degli URL già processati all'inizio della sessione.
    # La cache è un dizionario { url: md_path } che mi permette di saltare
    # scraping e AI per articoli già elaborati, anche se chiamati con slug diversi.
    cache = load_cache()

    # Raccolta link dai feed configurati
    news_links = set()
    for url in BASE_URLS:
        try:
            resp = requests.get(url, timeout=10)
            soup = BeautifulSoup(resp.text, 'html.parser')
            for a in soup.find_all('a', href=True):
                if any(t in a.text.lower() for t in TARGET_TOPICS) and len(a.text.strip()) > 15:
                    full_link = a['href']
                    if full_link.startswith('/'):
                        full_link = "/".join(url.split('/')[:3]) + full_link
                    news_links.add((full_link, a.text.strip()))
        except:
            continue

    processed_count = 0
    for link, title in news_links:
        if processed_count >= 5:
            break

        slug = slugify(title[:50])
        folder_path = os.path.join(output_root, f"{session_date}-{slug}")
        md_filename = f"{session_date}-{slug}.md"
        md_path = os.path.join(folder_path, md_filename)

        # VERIFICA CACHE: se l'URL è già in cache, non scarico né analizzo nulla.
        # Rigenero solo le immagini leggendo il file .md già su disco, poi passo avanti.
        if link in cache:
            existing_md_path = cache[link]
            log(f"URL già in cache: {link} -> {existing_md_path}")
            if os.path.exists(existing_md_path):
                with open(existing_md_path, "r", encoding="utf-8") as f:
                    content = f.read()
                slides = extract_slides(content)
                topic_key = next((k for k in TECH_PALETTE if k in content.lower()), "default")
                await create_images(topic_key, slides, os.path.dirname(existing_md_path))
            else:
                log(f"File .md in cache non trovato su disco ({existing_md_path}), salto.")
            continue

        # L'URL non è in cache: procedo con scraping e analisi
        page_text, video_urls = extract_article_data(link)

        video_text = ""
        for v_url in video_urls:
            video_text += "\n" + transcribe_video(v_url)

        full_context = page_text + "\n" + video_text

        if len(full_context) < 300:
            log(f"Contenuto troppo povero per '{title}'. Salto.")
            continue

        # FILTRO PROMOZIONALE: scarto l'articolo prima di sprecare risorse su Mistral.
        # Il controllo avviene qui, dopo aver verificato la cache, perché non ha senso
        # filtrare URL che non avremmo comunque riscaricato.
        if is_promotional(full_context):
            log(f"Contenuto promozionale rilevato, scarto: {title}")
            continue

        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        # Generazione Articolo
        article_md = generate_article(full_context, link)

        # Genero il front matter separatamente: Qwen estrae titolo, sintesi,
        # tech e tag dall'articolo già scritto da Mistral, così ha il testo
        # completo su cui lavorare invece del solo contesto grezzo.
        frontmatter, topic_key = generate_frontmatter(article_md, link, session_date)

        # Scrivo final_md e non article_md: article_md contiene solo il corpo,
        # final_md è il risultato dell'assemblaggio frontmatter + corpo.
        # Scrivere article_md era il bug originale che causava l'assenza dell'intestazione.
        final_md = frontmatter + article_md
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(final_md)

        # Salvo subito in cache prima di generare le immagini: in questo modo,
        # anche se il rendering grafico fallisce, l'URL risulta già processato
        # e alla prossima esecuzione salto il costoso scraping/AI.
        cache[link] = md_path
        save_cache(cache)

        # Uso il topic_key estratto dal front matter invece di fare una seconda
        # ricerca full-text sull'articolo: è già normalizzato e validato.
        slides = extract_slides(article_md)
        await create_images(topic_key, slides, folder_path)

        processed_count += 1
        log(f"Notizia completata con successo: {folder_path}")


if __name__ == "__main__":
    asyncio.run(main())