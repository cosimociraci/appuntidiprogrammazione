import os
import re
import argparse
import sys
from yt_dlp import YoutubeDL
from faster_whisper import WhisperModel

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
    # Mi assicuro di gestire i caratteri accentati ma pulisco il resto per evitare problemi al file system
    name = re.sub(r'[^\w]', '_', name)
    # Riduco le sequenze di underscore per una questione di pulizia estetica del nome file
    name = re.sub(r'_+', '_', name)
    return name.strip('_')

def process_single_video(url):
    """
    Gestisce l'intero workflow per un singolo URL passato da terminale.
    """
    print(f"\n--- Inizio elaborazione: {url} ---")
    
    # 1. Recupero metadati per il titolo
    ydl_opts_info = {'quiet': True, 'noplaylist': True}
    with YoutubeDL(ydl_opts_info) as ydl:
        try:
            info_dict = ydl.extract_info(url, download=False)
            video_title = info_dict.get('title', "video_output")
            clean_title = sanitize_filename(video_title)
        except Exception as e:
            print(f"Errore nel recupero metadati: {e}")
            clean_title = "video_fallback"

    # Uso un nome temporaneo univoco basato sul PID per evitare collisioni se lanciato in parallelo
    base_filename = f"audio_temp_{os.getpid()}"
    final_mp3 = f"{base_filename}.mp3"
    
    # 2. Configurazione e download audio
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
        'sleep_interval': 2,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }

    try:
        with YoutubeDL(ydl_opts_dl) as ydl:
            ydl.download([url])
        
        # 3. Trascrizione con Whisper
        print(f"Inizio trascrizione: {video_title}")
        segments, info = model.transcribe(
            final_mp3, 
            beam_size=1, 
            language="it",
            vad_filter=True
        )
        
        # 4. Scrittura del file di testo
        output_file = f"{clean_title}.txt"
        with open(output_file, "w", encoding="utf-8") as f:
            # Scrivo i segmenti man mano che vengono generati per ottimizzare l'uso della RAM
            for segment in segments:
                f.write(f"{segment.text.strip()} ")
        
        print(f"Processo completato con successo!")
        print(f"File generato: {output_file}")
        
    except Exception as e:
        print(f"Errore durante l'elaborazione del video: {e}")
    finally:
        # Mi assicuro di pulire il file audio temporaneo anche in caso di errore nella trascrizione
        if os.path.exists(final_mp3):
            os.remove(final_mp3)

if __name__ == "__main__":
    # Configuro il parser per leggere l'URL direttamente dal terminale
    # Scelgo 'url' come argomento posizionale obbligatorio
    parser = argparse.ArgumentParser(description="Scarica l'audio di un video YouTube e lo trascrive usando Faster Whisper.")
    parser.add_argument("url", help="L'URL del video YouTube da elaborare")
    
    args = parser.parse_args()
    
    # Controllo se l'utente ha fornito un URL minimo, altrimenti stampo l'help
    if args.url:
        process_single_video(args.url)
    else:
        parser.print_help()