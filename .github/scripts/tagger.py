import os
import time
import glob
import frontmatter
# Cambio la libreria come suggerito dal warning
from google import genai
from google.api_core import exceptions

# Inizializzo il nuovo client
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
MODEL_ID = "gemini-2.5-flash"

def get_ai_tags(content, existing_tags):
    # Preparo il prompt
    prompt = f"""
    Analizza questo articolo tecnico e restituisci una lista di tag appropriati.
    Tag attualmente suggeriti o esistenti nel sito: {existing_tags}
    
    Regole:
    1. Usa i tag esistenti se pertinenti.
    2. Aggiungi nuovi tag solo se strettamente necessari (max 2 nuovi).
    3. Restituisci SOLO una lista di stringhe separate da virgola, senza spiegazioni.
    
    Articolo:
    {content}
    """
    
    max_retries = 5
    for attempt in range(max_retries):
        try:
            # Uso la nuova sintassi del client per generare contenuti
            response = client.models.generate_content(
                model=MODEL_ID,
                contents=prompt
            )
            # Estraggo il testo dalla risposta (la nuova libreria usa .text)
            return [t.strip().lower() for t in response.text.split(',')]
            
        except exceptions.ResourceExhausted:
            # Se ricevo un 429, aspetto in modo esponenziale
            wait_time = (2 ** attempt) + 10 
            print(f"Limite raggiunto. Attesa di {wait_time} secondi...")
            time.sleep(wait_time)
        except Exception as e:
            print(f"Errore imprevisto: {e}")
            return []
            
    return []

# Processo i file
for filepath in glob.glob("_articoli/*.md"):
    print(f"Elaborazione: {filepath}")
    
    with open(filepath, 'r+', encoding='utf-8') as f:
        post = frontmatter.load(f)
        
        original_tags = post.get('tags', [])
        new_tags = get_ai_tags(post.content, original_tags)
        
        if new_tags:
            # Unisco e pulisco i duplicati
            final_tags = list(set(original_tags + new_tags))
            post['tags'] = final_tags
            
            # Sovrascrivo il file
            f.seek(0)
            f.write(frontmatter.dumps(post))
            f.truncate()
            
    # Aggiungo un piccolo delay di sicurezza per non saturare i 5 RPM del tier free
    # 12 secondi tra un file e l'altro garantiscono di stare sotto la soglia
    time.sleep(12)