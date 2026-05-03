import feedparser
import json
import os
import subprocess
import requests
from datetime import datetime, timedelta, timezone

# Configurazione
FEED_URLS = [
    "https://www.youtube.com/feeds/videos.xml?channel_id=UCKssZEARhK7TT_5DEZmtMpw",
]
DB_FILE = "download_history.json"
VIDEO_TO_TEXT_SCRIPT = "video_to_text.py"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def load_history():
    # Gestisco il file mancante o vuoto
    if not os.path.exists(DB_FILE) or os.path.getsize(DB_FILE) == 0:
        return {}
    try:
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        # Se il file è corrotto, restituisco un dizionario vuoto per ripartire
        return {}

def save_history(history):
    with open(DB_FILE, 'w') as f:
        json.dump(history, f, indent=4)

def parse_date(date_str):
    return datetime.fromisoformat(date_str.replace('Z', '+00:00'))

def run_video_to_text(video_url):
    print(f"--> Eseguo {VIDEO_TO_TEXT_SCRIPT} per: {video_url}")
    try:
        # Uso 'python' o 'python3' a seconda del tuo alias di sistema
        subprocess.run(["python3", VIDEO_TO_TEXT_SCRIPT, video_url], check=True)
        return True
    except Exception as e:
        print(f"Errore nell'esecuzione dello script esterno: {e}")
        return False

def main():
    history = load_history()
    now = datetime.now(timezone.utc)
    one_week_ago = now - timedelta(days=7)
    
    new_history = history.copy()

    for url in FEED_URLS:
        print(f"Controllo feed: {url}")
        
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            response.raise_for_status()
            feed = feedparser.parse(response.text)
            
            if not feed.entries:
                print(f"Attenzione: Nessun video trovato per {url}.")
                continue

            channel_id = url.split('=')[-1]
            last_date_str = history.get(channel_id)
            
            # Se non c'è nello storico, limitiamo all'ultima settimana
            limit_date = parse_date(last_date_str) if last_date_str else one_week_ago
            is_first_run = last_date_str is None

            videos_to_process = []
            for entry in feed.entries:
                pub_date = parse_date(entry.published)
                if pub_date > limit_date:
                    videos_to_process.append({
                        "link": entry.link,
                        "date": pub_date,
                        "date_str": entry.published
                    })

            if videos_to_process:
                # Ordino dal più vecchio al più recente
                videos_to_process.sort(key=lambda x: x['date'])
                
                for video in videos_to_process:
                    print(f"Nuovo video trovato: {video['link']} ({video['date_str']})")
                    
                    success = True
                    if is_first_run:
                        success = run_video_to_text(video['link'])
                    
                    # Aggiorno la data nello storico solo se l'operazione ha avuto successo
                    # o se non era prevista esecuzione script (per mantenere il cursore)
                    if success:
                        new_history[channel_id] = video['date_str']
                        # Salvo ad ogni passo per non perdere il progresso se crasha dopo
                        save_history(new_history)
            else:
                print("Nessun nuovo video da processare.")

        except Exception as e:
            print(f"Errore critico durante il processing di {url}: {e}")

    print("Aggiornamento completato.")

if __name__ == "__main__":
    main()