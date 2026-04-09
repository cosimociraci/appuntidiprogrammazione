import os
import re

def process_articles(directory):
    if not os.path.exists(directory):
        print(f"Errore: La cartella '{directory}' non esiste.")
        return

    # Pattern per trovare "Problema:" e "Perché:" ignorando asterischi e spazi extra
    # Cerchiamo: (eventuali non-alfabetici) + Parola + : + (eventuali non-alfabetici)
    re_problema = re.compile(r'[^a-zA-Z\s]*Problema:[^a-zA-Z\s]*', re.IGNORECASE)
    re_perche = re.compile(r'[^a-zA-Z\s]*Perch[eéè]:[^a-zA-Z\s]*', re.IGNORECASE)

    for filename in os.listdir(directory):
        if filename.endswith(".md"):
            filepath = os.path.join(directory, filename)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            new_lines = []
            modified = False
            in_analisi_tecnica = False

            for line in lines:
                # Attivo la logica solo dopo aver incontrato l'intestazione corretta
                if "## Analisi Tecnica" in line:
                    in_analisi_tecnica = True
                    new_lines.append(line)
                    continue
                
                # Se trovo un'altra sezione ##, smetto di processare in modo specifico
                if in_analisi_tecnica and line.startswith("## ") and "Analisi Tecnica" not in line:
                    in_analisi_tecnica = False

                if in_analisi_tecnica:
                    original_line = line
                    # 1. Pulizia e formattazione Problema:
                    if re_problema.search(line):
                        line = re_problema.sub(r'**Problema:**', line)
                    
                    # 2. Pulizia e formattazione Perché: con inserimento riga nuova
                    if re_perche.search(line):
                        # Se Perché: è sulla stessa linea di Problema:, lo sposto a capo
                        if "**Problema:**" in line:
                            line = line.replace("**Perché:**", "\n**Perché:**")
                            # Rimuovo eventuali spazi doppi creati dal rimpiazzo
                            line = line.replace("  ", " ")
                        else:
                            line = re_perche.sub(r'**Perché:**', line)

                    if line != original_line:
                        modified = True
                
                new_lines.append(line)

            if modified:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.writelines(new_lines)
                print(f"Sistemato: {filename}")

if __name__ == "__main__":
    process_articles("_articoli")