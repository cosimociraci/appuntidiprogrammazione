import os
import re
from yt_dlp import YoutubeDL
from faster_whisper import WhisperModel

video_links = [
    # "https://www.youtube.com/watch?v=74I1htx_Xqg", # Aglio, olio e agopuntura - con Salvo Di Grazia
    # "https://www.youtube.com/watch?v=JqPnRPiP8Sk", # CRISPR - la stagione dell'editing - con Anna Meldolesi
    # "https://www.youtube.com/watch?v=_Qy7jDBZPaM", # A proposito di genetica e dintorni - con Guido Barbujani
    # "https://www.youtube.com/watch?v=Qab0YDj9DbI" # Malattie, prevenzione, abitudini di vita: impariamo a trovare le risposte ai dubbi usando la rete
    # "https://www.youtube.com/watch?v=0MJBuSARFgE", # Risvegliare le nostre difese contro i tumori
    # "https://www.youtube.com/watch?v=gy3573lrnD0", # Sotto controllo. Gli screening oncologici ieri e oggi
    # "https://www.youtube.com/watch?v=66hW0oVXOsU", # Geni che curano: la sfida delle terapie avanzate
    # "https://www.youtube.com/watch?v=538slWFiaPI", # Tutta la verità (e qualche falso mito) sulla trombosi
    # "https://www.youtube.com/watch?v=W7qWVN4moEY", # La rivoluzione dell’immunoterapia nei tumori ematologici
    # "https://www.youtube.com/watch?v=Zf9VCcYqEmo", # mRNA da Nobel: dai vaccini anti-covid alla lotta ai tumori
    # "https://www.youtube.com/watch?v=UBVOtB-HFbs", # Tumori femminili e trombosi: quanto ne sappiamo?
    # "https://www.youtube.com/watch?v=LwkfpcAzIEk", # Trapianto d'organi: da dove siamo partiti e dove vorremmo (forse) arrivare
    # "https://www.youtube.com/watch?v=GCTtHIvT_OU"  # Le parole per dirlo: raccontare la malattia
]

# Configurazione del modello ottimizzata per CPU
model_size = "medium"
model = WhisperModel(
    model_size, 
    device="cpu", 
    compute_type="int8", 
    cpu_threads=8, 
    num_workers=4
)

def sanitize_filename(name):
    """
    Sostituisce spazi e caratteri non validi con underscore.
    Contrae underscore multipli in uno solo e pulisce i bordi.
    """
    # 1. Sostituisco tutto ciò che non è alfanumerico con "_"
    # Commento in prima persona: Uso \w così mantengo anche le lettere accentate 
    # che su Linux non danno problemi, ma elimino tutto il resto (parentesi, punti, ecc.)
    name = re.sub(r'[^\w]', '_', name)
    
    # 2. Sostituisco sequenze di più underscore con uno solo
    # Commento in prima persona: Questa regex cerca i duplicati consecutivi 
    # e li 'schiaccia' in un unico carattere per pulizia estetica.
    name = re.sub(r'_+', '_', name)
    
    # 3. Rimuovo eventuali underscore rimasti ai bordi (es. se il titolo iniziava con una parentesi)
    return name.strip('_')

def process_interviews(links):
    for idx, url in enumerate(links):
        print(f"\n--- Elaborazione Video {idx+1}/{len(links)} ---")
        
        # 1. Estraggo i metadati per ottenere il titolo
        ydl_opts_info = {'quiet': True, 'noplaylist': True}
        with YoutubeDL(ydl_opts_info) as ydl:
            try:
                info_dict = ydl.extract_info(url, download=False)
                video_title = info_dict.get('title', f"video_{idx}")
                # Sanitizzazione del titolo per il nome del file
                clean_title = sanitize_filename(video_title)
            except Exception as e:
                print(f"Errore nel recupero metadati: {e}")
                clean_title = f"video_fallback_{idx}"

        base_filename = f"audio_temp_{idx}"
        final_mp3 = f"{base_filename}.mp3"
        
        # 2. Download audio
        ydl_opts_dl = {
            'format': 'bestaudio/best',
            'outtmpl': base_filename,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '128',
            }],
            'noplaylist': True,
            'quiet': True,
            'sleep_interval': 5,          # Aspetta 5 secondi prima di ogni download
            'max_sleep_interval': 10,     # Fino a un massimo di 10
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }

        try:
            with YoutubeDL(ydl_opts_dl) as ydl:
                ydl.download([url])
            
            # 3. Trascrizione
            print(f"Trascrizione: {video_title}")
            segments, info = model.transcribe(
                final_mp3, 
                beam_size=1, 
                language="it",
                vad_filter=True
            )
            
            # 4. Salvataggio con il titolo pulito
            output_file = f"{clean_title}.txt"
            with open(output_file, "w", encoding="utf-8") as f:
                # Commento in prima persona: Scrivo il testo riga per riga 
                # per evitare di saturare la memoria con stringhe giganti.
                for segment in segments:
                    f.write(f"{segment.text.strip()} ")
            
            print(f"Completato! File creato: {output_file}")
            os.remove(final_mp3)
            
        except Exception as e:
            print(f"Errore critico durante il processo: {e}")

if __name__ == "__main__":
    process_interviews(video_links)