import os
from yt_dlp import YoutubeDL
from faster_whisper import WhisperModel

# 1. Definisco i link da processare
video_links = [
    "https://www.youtube.com/watch?v=74I1htx_Xqg",
    "https://www.youtube.com/watch?v=JqPnRPiP8Sk",
    "https://www.youtube.com/watch?v=_Qy7jDBZPaM",
    "https://www.youtube.com/watch?v=Qab0YDj9DbI"
    # Aggiungi qui gli altri link...
]

# Configurazione modello
model_size = "large-v3"
# Su Linux, se non hai configurato CUDA, "cpu" con "int8" è la scelta migliore
model = WhisperModel(model_size, device="cpu", compute_type="int8")

def process_interviews(links):
    for idx, url in enumerate(links):
        print(f"\n--- Inizio elaborazione Video {idx+1} ---")
        
        # Uso un nome base senza estensione per evitare il doppio .mp3.mp3
        base_filename = f"audio_temp_{idx}"
        final_mp3 = f"{base_filename}.mp3"
        
        ydl_opts = {
            'format': 'bestaudio/best',
            # outtmpl definisce il nome del file scaricato inizialmente
            'outtmpl': base_filename, 
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            # Forza la pulizia dei file intermedi
            'noplaylist': True,
        }
        
        try:
            # 1. Download ed estrazione audio
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            # Verifico se il file esiste (yt-dlp aggiunge .mp3 dopo la conversione)
            if not os.path.exists(final_mp3):
                print(f"Errore: il file {final_mp3} non è stato trovato!")
                continue

            # 2. Trascrizione
            print(f"Trascrizione in corso per: {url}...")
            segments, info = model.transcribe(final_mp3, beam_size=5, language="it")
            
            # 3. Salvataggio
            output_file = f"Intervista_{idx+1}.txt"
            with open(output_file, "w", encoding="utf-8") as f:
                for segment in segments:
                    # Ho rimosso i timestamp per darti un testo pulito come richiesto
                    # Ma puoi riaggiungerli se ti servono
                    f.write(f"{segment.text.strip()} ")
            
            print(f"Completato! Documento salvato: {output_file}")
            
            # 4. Pulizia
            os.remove(final_mp3)
            
        except Exception as e:
            print(f"Si è verificato un errore con il video {idx+1}: {e}")

if __name__ == "__main__":
    process_interviews(video_links)