import os
import google.generativeai as genai
import frontmatter
import glob

# Configurazione Gemini
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-2.5-flash')

def get_ai_tags(content, existing_tags):
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
    response = model.generate_content(prompt)
    return [t.strip().lower() for t in response.text.split(',')]

# Processa gli ultimi file modificati
for filepath in glob.glob("_articoli/*.md"):
    with open(filepath, 'r+', encoding='utf-8') as f:
        post = frontmatter.load(f)
        
        # Se l'articolo ha pochi tag o vogliamo rinfrescarli
        original_tags = post.get('tags', [])
        new_tags = get_ai_tags(post.content, original_tags)
        
        # Uniamo e puliamo i duplicati
        final_tags = list(set(original_tags + new_tags))
        post['tags'] = final_tags
        
        # Salvataggio
        f.seek(0)
        f.write(frontmatter.dumps(post))
        f.truncate()