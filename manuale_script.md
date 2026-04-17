Manuale d'Uso: Pipeline Generazione Notizie e Formattazione Codice
Questo documento descrive gli script Python e Bash utilizzati per la raccolta automatizzata di notizie tecnologiche, la generazione di articoli e la formattazione professionale del codice sorgente.

Indice degli Script
avvia_generazione_notizie.sh (Entry point)

genera_notizie.py (Core Engine)

code_formatter.py (Motore di formattazione)

excel_to_articoli.py (Importatore Excel)

formatta_articoli.py (Refactoring testo)

formatta_codice_articoli.py (Refactoring blocchi codice)

debug_formatter.py (Utility di test)

avvia_generazione_notizie.sh
Descrizione: Script Bash di automazione principale. Gestisce l'ambiente di esecuzione: verifica che Ollama sia attivo, controlla la presenza dei modelli LLM necessari (mistral, qwen2.5-coder), configura il buffering di Python e avvia la pipeline principale salvando i log.

Come si usa:

Bash
./avvia_generazione_notizie.sh
Parametri: Nessuno. Le configurazioni (percorsi, nomi modelli) sono cablate all'interno delle variabili PROJECT_DIR e LOG_FILE.

genera_notizie.py
Descrizione:
Il cuore del sistema. Esegue lo scraping di siti tecnologici, trascrive video (tramite Whisper), analizza i contenuti tramite LLM e genera articoli in formato Markdown pronti per Jekyll. Include logiche per la creazione di palette colori tech e gestione della cache degli URL.

Come si usa:

Bash
pipenv run python genera_notizie.py [opzioni]
Parametri Facoltativi:

--date YYYY-MM-DD: Specifica una data di sessione (default: oggi).

--regenerate: Rigenera le immagini per i file MD esistenti senza scaricare nuove notizie.

--fix-frontmatter: Aggiorna solo i metadati YAML dei file.

--libri: Modalità speciale per generare slide "consigli di lettura" da file in _libri/.

code_formatter.py
Descrizione:
Formattatore multi-linguaggio (Java, JS, SQL, HTML). Utilizza una logica mista: regole regex custom per l'indentazione, integrazione con Prettier per la rifinitura estetica e supporto a Ollama (LLM) per risolvere ambiguità strutturali (es. codice attaccato ai commenti).

Come si usa:

Bash
python code_formatter.py <file_input>
Parametri Obbligatori:

<file_input>: Percorso del file di testo/codice da formattare.

Output: Stampa a video il codice formattato secondo gli standard definiti.

excel_to_articoli.py
Descrizione:
Converte dataset esportati in Excel (.xlsx) in articoli Markdown per il blog. Gestisce la pulizia dei caratteri speciali di Excel, mappa i linguaggi di programmazione e utilizza code_formatter.py per formattare gli esempi di codice trovati nelle celle.

Come si usa:

Bash
python excel_to_articoli.py
Prerequisiti: I file devono essere presenti nella cartella excel_input/.

Output: Genera file .md nella cartella _articoli/.

formatta_articoli.py
Descrizione:
Script di rifinitura per i testi degli articoli. Cerca le parole chiave "Problema:" e "Perché:", le normalizza (rimuovendo formattazioni errate o grassetti multipli) e le riformatta correttamente con grassetti standard e spaziature (newline) adeguate.

Come si usa:

Bash
python formatta_articoli.py
Parametri: Agisce automaticamente sulla cartella _articoli/.

formatta_codice_articoli.py
Descrizione:
Esegue un refactoring massivo di tutti i blocchi di codice contenuti nei file Markdown. Estrae il codice tra i tag ```, lo passa al motore di code_formatter.py e sovrascrive il file con la versione indentata e pulita.

Come si usa:

Bash
python formatta_codice_articoli.py
Configurazione: Legge da _articoli/ e scrive i risultati in _nuovi_articoli/.

debug_formatter.py
Descrizione:
Strumento di diagnostica per lo sviluppo del formattatore. Mostra il processo di trasformazione del codice in tre step: input grezzo, scomposizione in token/linee (debug lista) e output finale.

Come si usa:

Bash
python debug_formatter.py <file_input> [linguaggio]
Parametri Obbligatori:

<file_input>: Il file di test.

Parametri Facoltativi:

[linguaggio]: Specifica la tecnologia (es. java, sql, html). Default: java.