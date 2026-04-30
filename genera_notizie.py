# pipenv run python genera_notizie.py

# --date YYYY-MM-DD
# Imposta manualmente la “data di sessione”.
# 
# Serve per:
# nominare cartelle e file
# scrivere la data nel front matter
# Se omesso → usa la data odierna.
# 
# --regenerate
# Non scarica nulla.
# Non usa AI.
# Non fa scraping.
# Rigenera SOLO le immagini per tutti i file .md già presenti in output/.
# 
# --fix-frontmatter
# Non scarica nulla.
# Non genera immagini.
# Rigenera SOLO il front matter YAML dei file .md in output/.
# 
# --libri
# Non scarica nulla.
# Non genera articoli.
# Genera le slide “consigli di lettura” per ogni file .md in _libri/.

import os
import json
import asyncio
import re
import sys
import argparse
from datetime import datetime
from pathlib import Path
import requests
from bs4 import BeautifulSoup
import yt_dlp
import whisper
import ollama
from playwright.async_api import async_playwright

# --- CONFIGURAZIONE ---
TARGET_TOPICS = ["jdk", "java", "js", "javascript", "python", "postgresql", "postgis", "ai", "intelligenza artificiale", "machine learning", "llm", "big data", "news"]
BASE_URLS = [
    "https://techfromthenet.it/software/news-produttivita/",
    "https://www.infoq.com/java/news/",
    "https://inside.java/",
    "https://www.zeusnews.it/",
    "https://ainews.it/ultime-notizie/"
]

CACHE_FILE = "output/processed_urls.json"

TECH_PALETTE = {
    "java": {
        "accent": "#f89820",
        "bg": "#FFF9F2",
        "highlights": ["Java", "JVM", "Spring", "Maven", "Gradle"]
    },
    "js": {
        "accent": "#F7DF1E",
        "bg": "#FFFFF0",
        "highlights": ["JavaScript", "Node", "npm", "ES6", "async"]
    },
    "postgresql": {
        "accent": "#336791",
        "bg": "#F0F5F9",
        "highlights": ["PostgreSQL", "SQL", "query", "index", "PostGIS"]
    },
    "ia": {
        "accent": "#8E44AD",
        "bg": "#F8F4FB",
        "highlights": ["AI", "LLM", "modello", "training", "inferenza"]
    },
    "default": {
        "accent": "#2ECC71",
        "bg": "#F2FBF6",
        "highlights": []
    }
}

# Palette dedicata alle slide "consigli di lettura": toni caldi carta/inchiostro
# per evocare il mondo dei libri senza usare i colori tech della palette principale.
BOOK_PALETTE = {
    "accent":     "#B5541B",   # terracotta bruciata: visibile ma non aggressivo
    "bg":         "#FDF6EC",   # carta invecchiata
    "text_dark":  "#1A1208",   # quasi-nero caldo
    "text_muted": "#6B4F35",   # marrone medio per le voci secondarie
}

# URL del blog: costante condivisa tra le slide tech e le slide libro.
BLOG_URL = "icarocomix.github.io/appuntidiprogrammazione"


def log(message):
    """Stampo un log con timestamp dettagliato per monitorare i tempi di esecuzione."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{timestamp} - {message}")
    sys.stdout.flush()


def parse_arguments():
    """Configuro argparse per gestire tutte le modalità operative da terminale."""
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
        help='Itera su tutti i file .md in output/ e rigenera tutte le immagini. Non scarica nulla.'
    )
    parser.add_argument(
        '--fix-frontmatter',
        action='store_true',
        help='Rigenera il front matter YAML di tutti i file .md in output/. Non scarica nulla, non rigenera immagini.'
    )
    parser.add_argument(
        '--libri',
        type=str,
        nargs='?',
        const='_libri',   # se l’utente scrive solo --libri, usa la cartella come fallback
        help='Genera le slide "consigli di lettura" per un singolo file .md oppure per l’intera cartella _libri/.'
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
    return datetime.now().strftime("%Y-%m-%d")


log("Inizializzazione Whisper (modello base)...")
whisper_model = whisper.load_model("base")


# --- CACHE ---

def load_cache():
    """Carico il file di cache che mappa ogni URL processato al path del suo file .md."""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log(f"Cache corrotta o illeggibile, la azzero: {e}")
    return {}


def save_cache(cache):
    """Persisto la cache su disco dopo ogni nuovo URL processato."""
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

        for tag in soup(['nav', 'footer', 'header', 'aside', 'script', 'style']):
            tag.decompose()

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
    """Chiedo a Qwen di valutare se il contenuto è una notizia tecnica reale o materiale promozionale."""
    log("[Qwen] Analisi anti-promozionale in corso...")
    prompt = f"""
Ruolo: Agisci come un Senior Editor Tecnico con 20 anni di esperienza nel distinguere il giornalismo d'innovazione dal marketing aziendale.
Compito: Analizza il testo fornito e classificalo rigorosamente in una di queste due categorie:
NOTIZIA TECNICA RILEVANTE: (Esempi: Aggiornamenti core, standard open source, scoperte scientifiche, annunci infrastrutturali di Big Tech).
MATERIALE PROMOZIONALE: (Esempi: Marketing mascherato da news, comunicati stampa di prodotti commerciali, partnership commerciali, servizi a pagamento).
Procedura di analisi:
Identifica il soggetto principale: è una tecnologia o un prodotto commerciale?
Valuta il valore tecnico: apporta un beneficio alla comunità o richiede un acquisto?
Controlla il tono: è oggettivo o utilizza aggettivi entusiastici tipici del copywriting (es. "rivoluzionario", "leader di mercato")?

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
        return "PUBBLICITA" in answer
    except Exception as e:
        log(f"Errore nel filtro promozionale, assumo notizia valida: {e}")
        return False


# --- INTELLIGENZA ARTIFICIALE ---

def generate_article(full_context, source_url):
    """Mistral crea l'articolo tecnico in italiano partendo dal contesto raccolto."""
    log("[Mistral] Avvio stesura nuovo articolo tecnico...")
    prompt = f"""
Ruolo: Agisci come un Senior Developer che scrive sul proprio blog tecnico. Il tuo stile è diretto, esperto e pratico.
Compito: Riscrivi le informazioni fornite nel "CONTESTO SORGENTE" creando un post di approfondimento tecnico in ITALIANO e in PRIMA PERSONA.
DIRETTIVE LINGUISTICHE (CRITICHE):
 - Terminologia Tecnica: NON tradurre mai i termini tecnici che fanno parte del gergo standard della programmazione o di specifici linguaggi (es. Java).
    NO: "metodo finale", "spazzino della memoria", "filo d'esecuzione", "costruttore di versione".
    SÌ: "final method", "Garbage Collector", "thread", "build".

CONTESTO SORGENTE:
{full_context[:15000]}

REGOLE OBBLIGATORIE:
1. Formato output: Markdown (.md) puro. NON scrivere mai un titolo H1 (riga con "#").
   Il titolo è già gestito dal sistema: inizia direttamente con la prima sezione.
   - Le sezioni DEVONO iniziare con "## " (due cancelletti seguiti da spazio).
     ESEMPI CORRETTI:   ## Cosa cambia nel GC
     ESEMPI SBAGLIATI:  # Cosa cambia  |  ### Cosa cambia  |  Cosa cambia:
   - NON usare mai la parola "Titolo:" o "Sezione:" come prefisso.
2. Stile: Scrivi in prima persona singolare ("Ho testato", "Mi sono accorto", "Uso spesso"). Evita il "noi" o le forme impersonali ("si nota che"). Mai tono impersonale o accademico.
3. Privacy: Non citare mai nomi propri di persone fisiche. Usa espressioni come "il team di sviluppo", "gli autori", "i maintainer".
4. Lingua: Se il materiale sorgente è in inglese, traduci accuratamente tutti i concetti. I termini tecnici consolidati (es. "thread", "query", "build") restano in inglese.
5. Profondità: Approfondisci i concetti tecnici con esempi concreti. Non limitarti a riassumere: il "perché" dietro alle scelte tecnologiche e confrontale con possibili alternative, aggiungi contesto, confronti e implicazioni pratiche.
6. Chiusura: Termina l'articolo con una riga '---' seguita da 'Fonte originale: {source_url}'.
"""
    response = ollama.chat(model='mistral', messages=[{'role': 'user', 'content': prompt}])
    return sanitize_article_headings(response['message']['content'])


def sanitize_article_headings(article):
    """Normalizzo i titoli dell'articolo prodotto da Mistral correggendo i problemi
    ricorrenti di formattazione.

    Poiché il front matter contiene già il campo 'title' che il layout Jekyll
    renderizza come H1, il corpo del Markdown NON deve contenere nessun '#'.
    Tutta la gerarchia parte da '##' per le sezioni principali.

    Logica applicata riga per riga:
    - Righe "Titolo: ..." → rimosse: il titolo vive nel front matter.
    - Righe "# testo" (H1) → degradate a "## testo".
    - Righe "### testo" o più profondi → degradate a "## testo".
    - Righe "#testo" senza spazio → corrette in "## testo"."""
    lines = article.split('\n')
    result = []

    for line in lines:
        stripped = line.strip()

        # Rimuovo righe "Titolo: ..." con eventuale prefisso di cancelletti
        if re.match(r'^#{0,3}\s*[Tt]itolo:\s*.+', stripped):
            continue

        # Aggiungo spazio mancante dopo i cancelletti: "#Testo" → "# Testo"
        if re.match(r'^#{1,6}[^\s#]', stripped):
            stripped = re.sub(r'^(#{1,6})([^\s])', r'\1 \2', stripped)

        # H1 nel corpo → degrado a H2
        if re.match(r'^#\s', stripped):
            stripped = re.sub(r'^#\s', '## ', stripped)

        # H3 o più profondi → degrado a H2 per gerarchia piatta
        if re.match(r'^#{3,}\s', stripped):
            stripped = re.sub(r'^#{3,}\s', '## ', stripped)

        result.append(stripped)

    return '\n'.join(result)


def extract_slides(article):
    """Qwen estrae i punti chiave per il carosello grafico come array di oggetti JSON.

    Ho cambiato la struttura dell'output da array di stringhe ad array di oggetti
    {"title": "...", "text": "..."}: ogni slide porta ora il proprio titolo
    contestuale invece di ereditare l'etichetta generica del topic (es. "JAVA").
    Questo risolve il problema delle slide disomogenee che condividevano un unico
    titolo non rappresentativo per tutte le pillole."""
    log("[Qwen] Estrazione pillole carosello...")
    prompt = f"""
Ruolo: Sei un Senior Technical Content Designer esperto in sistemi distribuiti e linguaggi di programmazione.
Compito: Analizza il testo fornito ed estrai esattamente 10 pillole informative in ITALIANO. Ogni pillola deve essere un'unità di conoscenza tecnica autonoma e densa.

ARTICOLO:
{article}

REGOLE OBBLIGATORIE:
1. Contesto esplicito: ogni pillola deve menzionare esplicitamente il tema trattato.
2. Autonomia: ogni pillola deve essere comprensibile senza aver letto le altre.
3. Il campo "title" deve essere un titolo breve e specifico per quella pillola (max 5 parole),
   NON il nome generico della tecnologia. Deve rispecchiare esattamente il contenuto del campo "text".
   ESEMPI CORRETTI:   "JEP 500: Final diventa Final" | "Hibernate 8.2: cascade fix" | "HTTP/3 nel client Java"
   ESEMPI SBAGLIATI:  "JAVA" | "POSTGRESQL" | "Novità Java" | "Aggiornamento"
4. Il campo "text" ha circa 5 righe. Frasi brevi, dirette, dense di informazione tecnica. Ogni pillola deve contenere il nome della tecnologia o del contesto per essere autosufficiente.
5. Privilegia: numeri concreti, confronti tra versioni, impatti pratici, breaking change, casi d'uso reali.
6. NON usare markdown nel campo "text" (no asterischi, no #, no trattini iniziali). Solo testo piano.
7. Restituisci ESCLUSIVAMENTE un array JSON di 10 oggetti, senza alcun testo prima o dopo, senza backtick.
8. Terminologia: NON tradurre mai i termini tecnici, le keyword di linguaggio, i nomi di parametri o pattern (es. usa "Garbage Collector", non "spazzino"; "pattern matching", non "confronto di schemi"; "overhead", non "sovraccarico").
9. Dettaglio: Ogni pillola deve spiegare il perché o il come, non solo il "cosa". Evita generalità; usa dati, versioni e specifiche tecniche.

Formato atteso:
[
  {{"title": "Titolo specifico slide 1", "text": "Testo della pillola 1."}},
  {{"title": "Titolo specifico slide 2", "text": "Testo della pillola 2."}}
]
"""
    response = ollama.chat(model='qwen2.5-coder', messages=[{'role': 'user', 'content': prompt}])
    raw = response['message']['content']

    # Primo tentativo: parso il JSON grezzo cercando l'array di oggetti.
    match = re.search(r'\[.*\]', raw, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group())
            # Valido che ogni elemento abbia i campi attesi prima di restituire.
            # Se un oggetto manca di "title" o "text" lo normalizzo con un fallback
            # invece di scartare l'intera lista: meglio una slide con titolo generico
            # che perdere il contenuto estratto correttamente.
            slides = []
            for i, item in enumerate(data):
                if isinstance(item, dict):
                    slides.append({
                        "title": str(item.get("title", f"Slide {i + 1}")).strip(),
                        "text":  str(item.get("text",  "")).strip()
                    })
                elif isinstance(item, str):
                    # Compatibilità con eventuale output misto: stringa senza titolo
                    slides.append({"title": f"Slide {i + 1}", "text": item.strip()})
            return slides[:10]
        except json.JSONDecodeError as e:
            log(f"JSON grezzo non valido ({e}), avvio pulizia e secondo tentativo...")

    # Secondo tentativo: pulizia caratteri problematici e ri-parse.
    if match:
        cleaned = match.group()
        cleaned = re.sub(r'[\x00-\x1f\x7f]', ' ', cleaned)
        cleaned = cleaned.replace('…', '...').replace('\u2026', '...')
        try:
            data = json.loads(cleaned)
            slides = []
            for i, item in enumerate(data):
                if isinstance(item, dict):
                    slides.append({
                        "title": str(item.get("title", f"Slide {i + 1}")).strip(),
                        "text":  str(item.get("text",  "")).strip()
                    })
            return slides[:10]
        except json.JSONDecodeError as e:
            log(f"Pulizia insufficiente ({e}), avvio estrazione manuale...")

    # Terzo tentativo (fallback finale): il modello ha ignorato il formato oggetto
    # e ha restituito stringhe semplici. Estraggo le coppie "title"/"text" con regex
    # cercando pattern chiave-valore nel testo grezzo.
    # Se nemmeno questo funziona, costruisco slide senza titolo dalle stringhe trovate.
    title_text_pairs = re.findall(
        r'"title"\s*:\s*"((?:[^"\\]|\\.)*)".*?"text"\s*:\s*"((?:[^"\\]|\\.)*)"',
        raw, re.DOTALL
    )
    if title_text_pairs:
        log(f"Estrazione coppie title/text riuscita: {len(title_text_pairs)} slide recuperate.")
        return [{"title": t.strip(), "text": x.strip()} for t, x in title_text_pairs[:10]]

    # Fallback estremo: estraggo solo le stringhe e le uso come testo senza titolo.
    candidates = re.findall(r'"((?:[^"\\]|\\.)*)"', raw)
    slides_fallback = [s.strip() for s in candidates if len(s.strip()) > 20]
    if slides_fallback:
        log(f"Fallback estremo: recuperate {len(slides_fallback)} stringhe senza titolo.")
        return [{"title": f"Slide {i + 1}", "text": s} for i, s in enumerate(slides_fallback[:10])]

    log("Impossibile estrarre slide dal modello, la generazione grafica verrà saltata.")
    return []


# --- ENGINE GRAFICO (SLIDE TECH) ---

def highlight_keywords(text, keywords, accent_color):
    """Sostituisco ogni parola chiave del topic con la sua versione in grassetto colorato."""
    for keyword in keywords:
        pattern = re.compile(r'\b' + re.escape(keyword) + r'\b')
        replacement = f"<b style='color:{accent_color}'>{keyword}</b>"
        text = pattern.sub(replacement, text)
    return text


async def create_images(topic, slides, folder_path):
    """Rendering delle slide 1080x1080 con titolo per-slide, numerazione progressiva
    e watermark URL del blog in basso a sinistra."""
    log(f"Rendering grafico per topic: {topic} in {folder_path}...")

    for f in os.listdir(folder_path):
        if f.endswith(".png"):
            os.remove(os.path.join(folder_path, f))

    config = TECH_PALETTE.get(topic.lower(), TECH_PALETTE["default"])

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={'width': 1080, 'height': 1080})

        for i, slide in enumerate(slides[:10]):
            slide_title = slide.get("title", f"Slide {i + 1}")
            slide_text  = slide.get("text", "")
            formatted_text = highlight_keywords(slide_text, config['highlights'], config['accent'])

            html_content = f"""
            <html>
            <head>
                <link rel="preconnect" href="https://fonts.googleapis.com">
                <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
                <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@500;700;900&display=swap" rel="stylesheet">
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
                .slide-title {{
                    font-weight: 900;
                    color: {config['accent']};
                    text-transform: uppercase;
                    font-size: 22px;
                    margin-bottom: 28px;
                    letter-spacing: 1.5px;
                    line-height: 1.3;
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
                .blog-url {{
                    position: absolute;
                    bottom: 50px;
                    left: 80px;
                    font-size: 18px;
                    font-weight: 500;
                    color: #333;
                    opacity: 0.4;
                    letter-spacing: 0.3px;
                }}
            </style>
            <body>
                <div class="container">
                    <div class="slide-title">{slide_title}</div>
                    <div class="text">{formatted_text}</div>
                </div>
                <div class="blog-url">{BLOG_URL}</div>
            </body>
            </html>"""

#                <div class="page-num">{i + 1}/10</div>

            await page.set_content(html_content, wait_until="networkidle")
            await page.screenshot(path=os.path.join(folder_path, f"slide_{i + 1}.png"))

        await browser.close()


# --- ENGINE GRAFICO (SLIDE LIBRI) ---

def extract_book_title(content):
    """Estraggo il campo 'title:' dal front matter YAML del file .md del libro.

    Cerco la riga 'title: ...' dentro il blocco delimitato da '---'.
    Se il campo non è presente restituisco una stringa vuota: il chiamante
    gestirà il fallback con il nome del file."""
    fm_match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not fm_match:
        return ""
    for line in fm_match.group(1).splitlines():
        m = re.match(r'^title:\s*["\']?(.*?)["\']?\s*$', line.strip())
        if m:
            return m.group(1).strip()
    return ""

def extract_book_autore(content):
    """Estraggo il campo 'autore:' dal front matter YAML del file .md del libro.

    Cerco la riga 'autore: ...' dentro il blocco delimitato da '---'.
    Se il campo non è presente restituisco una stringa vuota: il chiamante
    gestirà il fallback con il nome del file."""
    fm_match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not fm_match:
        return ""
    for line in fm_match.group(1).splitlines():
        m = re.match(r'^autore:\s*["\']?(.*?)["\']?\s*$', line.strip())
        if m:
            return m.group(1).strip()
    return ""


def extract_chapter_titles(content):
    """Estraggo tutti i titoli preceduti da '#### ' (4 cancelletti) dal corpo del file .md.

    Salto il blocco front matter iniziale per evitare di catturare eventuale
    formattazione YAML, poi raccolgo ogni riga che inizia esattamente con '#### '.
    Restituisco una lista di stringhe già pulite dal prefisso Markdown."""
    # Rimuovo il front matter prima di cercare i titoli nel corpo
    body = re.sub(r'^---\n.*?\n---\n', '', content, count=1, flags=re.DOTALL)
    titles = []
    for line in body.splitlines():
        # Cerco esattamente 4 cancelletti seguiti da almeno uno spazio.
        # Uso la regex per essere robusto rispetto a spazi multipli dopo i cancelletti.
        m = re.match(r'^#{4}\s+(.+)$', line.strip())
        if m:
            titles.append(m.group(1).strip())
    return titles


def chunk_titles(titles, max_slides=9):
    """Distribuisco N titoli in al massimo max_slides gruppi omogenei.

    Ho scelto max_slides=9 perché la slide 1 è riservata alla copertina,
    e il totale non deve superare 10. Con divmod distribuisco i titoli in eccesso
    sui primi gruppi invece di creare un ultimo gruppo sproporzionato."""
    n = len(titles)
    if n == 0:
        return []
    num_slides = min(max_slides, n)
    base_size, remainder = divmod(n, num_slides)
    chunks = []
    start = 0
    for i in range(num_slides):
        # I primi 'remainder' gruppi ricevono un titolo in più
        end = start + base_size + (1 if i < remainder else 0)
        chunks.append(titles[start:end])
        start = end
    return chunks


async def render_book_cover(page, book_title, book_autore, output_path):
    """Renderizzo la slide di copertina con la scritta 'Consigli di lettura' e il titolo del libro.

    Ho scelto un layout centrato con cornice decorativa e font serif (Playfair Display)
    per evocare la copertina di un libro piuttosto che una slide informativa tech."""
    p = BOOK_PALETTE
    html = f"""
    <html>
    <head>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=Poppins:wght@400;500&display=swap" rel="stylesheet">
    </head>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background: {p['bg']};
            width: 1080px;
            height: 1080px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            position: relative;
            padding: 100px;
        }}
        /* Cornice decorativa interna: richiama la grafica dei libri d'epoca */
        .frame {{
            position: absolute;
            inset: 40px;
            border: 3px solid {p['accent']};
            opacity: 0.25;
        }}
        .eyebrow {{
            font-family: 'Poppins', sans-serif;
            font-size: 20px;
            font-weight: 500;
            letter-spacing: 5px;
            text-transform: uppercase;
            color: {p['accent']};
            margin-bottom: 36px;
        }}
        /* Linea ornamentale tra eyebrow e titolo: richiamo tipografico classico */
        .divider {{
            width: 80px;
            height: 3px;
            background: {p['accent']};
            margin: 0 auto 48px;
        }}
        .book-title {{
            font-family: 'Playfair Display', serif;
            font-size: 64px;
            font-weight: 900;
            color: {p['text_dark']};
            text-align: center;
            line-height: 1.2;
            max-width: 800px;
        }}
        .book-autore {{
            font-family: 'Playfair Display', serif;
            font-size: 30px;
            font-weight: 900;
            color: {p['text_dark']};
            text-align: center;
            line-height: 1.2;
            max-width: 800px;
        }}
        .blog-url {{
            position: absolute;
            bottom: 50px;
            left: 50%;
            transform: translateX(-50%);
            font-family: 'Poppins', sans-serif;
            font-size: 18px;
            font-weight: 400;
            color: {p['text_muted']};
            opacity: 0.5;
            letter-spacing: 0.3px;
            white-space: nowrap;
        }}
    </style>
    <body>
        <div class="frame"></div>
        <div class="eyebrow">Consigli di lettura</div>
        <div class="divider"></div>
        <div class="book-title">{book_title}</div>
        <div class="book-autore">{book_autore}</div>
        <div class="blog-url">{BLOG_URL}</div>
    </body>
    </html>"""
    await page.set_content(html, wait_until="networkidle")
    await page.screenshot(path=output_path)


async def render_book_content_slide(page, slide_num, total_slides, titles_chunk, output_path):
    """Renderizzo una slide di contenuto con la lista dei titoli del chunk corrente.

    Il font size si adatta dinamicamente al numero di voci nel chunk: più titoli
    ci sono, più il testo si restringe per mantenere tutto leggibile nel riquadro.
    Il range 34-54px copre da 1 a 5 titoli per slide."""
    p = BOOK_PALETTE

    # Costruisco gli item HTML per ogni titolo nel chunk.
    # Uso un quadratino (&#9632;) come bullet per coerenza grafica cross-browser:
    # i list-style CSS non sono sempre affidabili nel rendering Playwright headless.
    items_html = ""
    for title in titles_chunk:
        items_html += f"""
        <div class="item">
            <span class="bullet">&#9632;</span>
            <span class="item-text">{title}</span>
        </div>"""

    item_count = len(titles_chunk)
    font_size  = max(34, 54 - (item_count * 4))

    html = f"""
    <html>
    <head>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Poppins:wght@400;500&display=swap" rel="stylesheet">
    </head>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background: {p['bg']};
            font-family: 'Poppins', sans-serif;
            width: 1080px;
            height: 1080px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            position: relative;
            padding: 100px 110px;
        }}
        /* Barra verticale sinistra: coerente con il layout tech ma con colore libro */
        .sidebar {{
            position: absolute;
            left: 0;
            top: 0;
            bottom: 0;
            width: 18px;
            background: {p['accent']};
        }}
        .items-container {{
            display: flex;
            flex-direction: column;
            gap: 32px;
        }}
        .item {{
            display: flex;
            align-items: flex-start;
            gap: 24px;
        }}
        .bullet {{
            color: {p['accent']};
            font-size: {int(font_size * 0.45)}px;
            line-height: {int(font_size * 1.3)}px;
            flex-shrink: 0;
            margin-top: 4px;
        }}
        .item-text {{
            font-family: 'Playfair Display', serif;
            font-size: {font_size}px;
            font-weight: 700;
            color: {p['text_dark']};
            line-height: 1.25;
        }}
        .page-num {{
            position: absolute;
            bottom: 50px;
            right: 80px;
            font-size: 28px;
            font-weight: 500;
            color: {p['accent']};
            opacity: 0.55;
            font-family: 'Poppins', sans-serif;
        }}
        .blog-url {{
            position: absolute;
            bottom: 50px;
            left: 110px;
            font-family: 'Poppins', sans-serif;
            font-size: 18px;
            font-weight: 400;
            color: {p['text_muted']};
            opacity: 0.4;
            letter-spacing: 0.3px;
        }}
    </style>
    <body>
        <div class="sidebar"></div>
        <div class="items-container">
            {items_html}
        </div>
        <div class="page-num">{slide_num}/{total_slides}</div>
        <div class="blog-url">{BLOG_URL}</div>
    </body>
    </html>"""
    await page.set_content(html, wait_until="networkidle")
    await page.screenshot(path=output_path)


async def generate_book_slides_for_file(md_path, output_dir):
    """Pipeline completa per un singolo file .md: estraggo metadati, distribuisco
    i titoli #### in chunk e renderizzo tutte le slide nella cartella di output.

    Ho separato cover e contenuto in due funzioni di rendering distinte perché
    i due layout hanno strutture HTML abbastanza diverse: un template unificato
    con troppa logica condizionale sarebbe più difficile da manutenere."""
    log(f"Elaborazione libro: {md_path}")

    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    book_title = extract_book_title(content)
    if not book_title:
        # Fallback: uso il nome del file senza estensione, con spazi al posto dei trattini
        book_title = os.path.splitext(os.path.basename(md_path))[0].replace("-", " ").title()
        log(f"  Titolo non trovato nel front matter, uso nome file: '{book_title}'")

    book_autore = extract_book_autore(content)

    chapter_titles = extract_chapter_titles(content)
    if not chapter_titles:
        log(f"  Nessun titolo '####' trovato in {md_path}, salto.")
        return

    log(f"  Trovati {len(chapter_titles)} titoli ####. Libro: '{book_title}'")

    os.makedirs(output_dir, exist_ok=True)

    # Pulisco eventuali slide precedenti per evitare residui da esecuzioni passate
    for fname in os.listdir(output_dir):
        if fname.endswith(".png"):
            os.remove(os.path.join(output_dir, fname))

    chunks = chunk_titles(chapter_titles, max_slides=9)
    total_content_slides = len(chunks)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={'width': 1080, 'height': 1080})

        # Slide 1: copertina con titolo del libro
        cover_path = os.path.join(output_dir, "slide_1.png")
        await render_book_cover(page, book_title, book_autore, cover_path)
        log(f"  Copertina generata: {cover_path}")

        # Slide 2..N: chunk di titoli con numerazione visibile 1/M .. M/M
        for i, chunk in enumerate(chunks):
            slide_num  = i + 1       # numerazione visibile: parte da 1
            slide_file = i + 2       # nome file: parte da slide_2.png
            out_path   = os.path.join(output_dir, f"slide_{slide_file}.png")
            await render_book_content_slide(page, slide_num, total_content_slides, chunk, out_path)
            log(f"  Slide {slide_file} generata ({len(chunk)} titoli)")

        await browser.close()

    log(f"  Completato: {total_content_slides + 1} slide totali in {output_dir}")


async def process_libri_folder(libri_root):
    """Itero su tutti i file .md nella cartella _libri/ e genero le slide per ognuno.

    La sottocartella di output ha lo stesso nome del file .md senza estensione,
    come da specifica: '_libri/<nome-file>/slide_N.png'."""
    log(f"--- MODALITÀ LIBRI: elaborazione cartella {libri_root} ---")

    if not os.path.isdir(libri_root):
        log(f"ERRORE: la cartella '{libri_root}' non esiste. Crearla e popolarla con file .md.")
        return

    # Considero solo i file .md diretti nella root di _libri, non quelli nelle sottocartelle
    md_files = sorted([
        f for f in os.listdir(libri_root)
        if f.endswith(".md") and os.path.isfile(os.path.join(libri_root, f))
    ])

    if not md_files:
        log(f"Nessun file .md trovato in {libri_root}.")
        return

    log(f"Trovati {len(md_files)} file .md da elaborare.")

    for md_filename in md_files:
        md_path  = os.path.join(libri_root, md_filename)
        subfolder = os.path.splitext(md_filename)[0]
        out_dir   = os.path.join(libri_root, subfolder)
        try:
            await generate_book_slides_for_file(md_path, out_dir)
        except Exception as e:
            log(f"Errore su {md_filename}: {e}")

    log("--- MODALITÀ LIBRI COMPLETATA ---")


# --- FRONT MATTER ---

def generate_frontmatter(article, source_url, date_str):
    """Chiedo a Qwen di estrarre i metadati dell'articolo in JSON strutturato,
    poi assemblo il blocco YAML front matter da anteporre al file .md."""
    valid_tech_keys = list(TECH_PALETTE.keys())

    # Trasformo la lista globale in una stringa formattata JSON per il prompt
    # In questo modo Qwen vede un elenco chiaro: ["jdk", "java", ...]
    formatted_topics = json.dumps(TARGET_TOPICS)

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
- "tags": array JSON di 2-5 stringhe lowercase che identificano i temi principali tra i seguenti: {formatted_topics}

Esempio formato atteso:
{{"title": "Titolo esempio", "sintesi": "Breve riassunto senza newline.", "tech": "java", "tags": ["java", "jvm", "news"]}}
"""
    try:
        response = ollama.chat(model='qwen2.5-coder', messages=[{'role': 'user', 'content': prompt}])
        raw = response['message']['content'].strip()

        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if not match:
            raise ValueError("Nessun oggetto JSON trovato nella risposta del modello.")

        data = json.loads(match.group())

        tech = data.get("tech", "default").lower()
        if tech not in TECH_PALETTE:
            log(f"[FrontMatter] Tech '{tech}' non riconosciuto, uso 'default'.")
            tech = "default"

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
    La funzione è idempotente: se il file non ha frontmatter restituisce il contenuto invariato."""
    match = re.match(r'^---\n.*?\n---\n', content, re.DOTALL)
    if match:
        return content[match.end():]
    return content


# --- MODALITÀ RIGENERAZIONE MASSIVA ---

async def regenerate_all(output_root):
    """Itero su tutte le cartelle di output e rigenero le immagini per ogni file .md trovato."""
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


def fix_frontmatter_all(output_root):
    """Itero su tutte le cartelle di output e rigenero il frontmatter di ogni .md trovato."""
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

            body = strip_existing_frontmatter(raw_content)
            body = sanitize_article_headings(body)

            source_url = ""
            url_match = re.search(r'Fonte originale:\s*(https?://\S+)', body)
            if url_match:
                source_url = url_match.group(1).rstrip('/')
            else:
                log(f"  Link sorgente non trovato in {md_files[0]}, campo link sarà vuoto.")

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


async def process_single_book(md_path):
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    book_title  = extract_book_title(content)  or Path(md_path).stem
    book_autore = extract_book_autore(content) or ""
    chapter_titles = extract_chapter_titles(content)
    chunks = chunk_titles(chapter_titles)

    out_dir = os.path.join("_libri", Path(md_path).stem)
    os.makedirs(out_dir, exist_ok=True)

    # Rendering Playwright
    await render_book_slides(book_title, book_autore, chunks, out_dir)

async def render_book_slides(book_title, book_autore, chunks, out_dir):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={'width': 1080, 'height': 1080})

        # Slide 1: copertina
        await render_book_cover(page, book_title, book_autore, os.path.join(out_dir, "slide_01.png"))

        # Slide 2..N: contenuti
        for i, chunk in enumerate(chunks, start=2):
            await render_book_content_slide(
                page,
                slide_num=i,
                total_slides=len(chunks) + 1,
                titles_chunk=chunk,
                output_path=os.path.join(out_dir, f"slide_{i:02d}.png")
            )

        await browser.close()


# --- MAIN ENGINE ---

async def main():
    args = parse_arguments()
    session_date = resolve_session_date(args.date)

    log(f"--- START SESSION: {session_date} (Regenerate: {args.regenerate}, Fix-frontmatter: {args.fix_frontmatter}, Libri: {args.libri}) ---")

    output_root = "output_news"
    if not os.path.exists(output_root):
        os.makedirs(output_root)

    if args.libri:
        libri_path = args.libri

        # Caso 1: è un singolo file
        if os.path.isfile(libri_path):
            await process_single_book(libri_path)
            return

        # Caso 2: è una cartella (fallback)
        if os.path.isdir(libri_path):
            for fname in os.listdir(libri_path):
                if fname.endswith(".md"):
                    await process_single_book(os.path.join(libri_path, fname))
            return

        log(f"ERRORE: il path passato a --libri non esiste: {libri_path}")
        return


    if args.regenerate:
        await regenerate_all(output_root)
        return

    if args.fix_frontmatter:
        fix_frontmatter_all(output_root)
        return

    cache = load_cache()

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

        page_text, video_urls = extract_article_data(link)

        video_text = ""
        for v_url in video_urls:
            video_text += "\n" + transcribe_video(v_url)

        full_context = page_text + "\n" + video_text

        if len(full_context) < 300:
            log(f"Contenuto troppo povero per '{title}'. Salto.")
            continue

        if is_promotional(full_context):
            log(f"Contenuto promozionale rilevato, scarto: {title}")
            continue

        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        article_md = generate_article(full_context, link)

        frontmatter, topic_key = generate_frontmatter(article_md, link, session_date)

        final_md = frontmatter + article_md
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(final_md)

        cache[link] = md_path
        save_cache(cache)

        slides = extract_slides(article_md)
        await create_images(topic_key, slides, folder_path)

        processed_count += 1
        log(f"Notizia completata con successo: {folder_path}")


if __name__ == "__main__":
    asyncio.run(main())