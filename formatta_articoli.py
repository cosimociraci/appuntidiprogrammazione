import os
import re

def process_articles(directory):
    # Pattern aggiornati:
    # \b assicura che siano parole isolate e non parti di altre parole
    # Il flag re.IGNORECASE è opzionale, ma utile se scrivi 'PROBLEMA:'
    problema_regex = re.compile(r'\bProblema:', re.IGNORECASE)
    perche_regex = re.compile(r'\bPerch[eéè]:', re.IGNORECASE)

    if not os.path.exists(directory):
        print(f"Errore: La cartella '{directory}' non esiste.")
        return

    for filename in os.listdir(directory):
        if filename.endswith(".md"):
            filepath = os.path.join(directory, filename)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            # Verifico se siamo nella sezione corretta
            if "## Analisi Tecnica" in content:
                # Sostituzione globale nel testo
                new_content = problema_regex.sub(r'**Problema:**', content)
                new_content = perche_regex.sub(r'**Perché:**', new_content)

                if new_content != content:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    print(f"Aggiornato: {filename}")

if __name__ == "__main__":
    # Assicurati che lo script sia nella cartella superiore a _articoli 
    # o cambia il percorso qui sotto
    target_dir = "_articoli"
    process_articles(target_dir)