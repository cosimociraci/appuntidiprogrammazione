# appuntidiprogrammazione
https://icarocomix.github.io/appuntidiprogrammazione/

# INSTALLAZIONE LOCALE
python3 -m http.server 8000
npx decap-server

http://0.0.0.0:8000/admin/#/

# 🏗️ Architettura e Pipeline di Pubblicazione: DevLog

Questo documento descrive il flusso tecnico che permette di trasformare i dati grezzi da Excel in un blog professionale su GitHub Pages.

---

## 0. Processi attivi
tagger.py: Il "cervello" Python. Usa il nuovo client google-genai per leggere i tuoi articoli, confrontarli con i tag esistenti e aggiungerne di nuovi (senza esagerare) usando Gemini. Ho notato la gestione intelligente del rate limiting (i 12 secondi di pausa e il backoff esponenziale).

ai-tagger.yml: Il braccio meccanico. Si attiva ogni volta che carichi qualcosa nella cartella _articoli, lancia lo script Python e fa il commit automatico dei tag aggiornati direttamente nel repository.

jekyll.yml: Il workflow standard di GitHub per compilare e pubblicare il sito su Pages usando gli artifact.

daily-publish.yml: Una ridondanza utile che assicura che il sito venga compilato ogni sera alle 22:05, gestendo così i post programmati per il futuro.

---

## 1. Il Ciclo di Vita dell'Informazione

Il processo si divide in tre "mondi" distinti che comunicano tra loro:

### A. Il Mondo Locale (Generazione)
Qui operano lo script Python e gli strumenti di formattazione.
* **Sorgente**: I file `.xlsx` nella cartella `excel_input/`.
* **Motore**: Lo script `excel_to_jekyll.py` estrae i dati.
* **Il Formattatore**: Lo script chiama `npx prettier` (per Java/HTML) o `sql-formatter`. Questo è il passaggio critico: il codice viene "abbellito" (indentazione, a capo, spazi) **prima** di essere scritto nel file finale.
* **Output**: Vengono creati file `.md` nella cartella `_articoli/`. Ogni file ha un **Front Matter** (metadati per Jekyll) e un **Corpo** (il contenuto vero e proprio).

### B. Il Mondo GitHub (Compilazione)
Una volta fatto il `git push`, GitHub attiva un workflow automatico.
* **Compilatore (Jekyll)**: Legge il file `_config.yml` per capire le regole del sito.
* **Iniezione (Liquid)**: Jekyll prende il contenuto del file `.md` e lo "inietta" dentro i layout HTML (`_layouts/post.html`). 
    * Il testo dell'articolo sostituisce il tag `{{ content }}`.
    * I metadati (titolo, data, tags) sostituiscono i tag come `{{ page.title }}`.
* **Syntax Highlighting (Rouge)**: Jekyll analizza i blocchi di codice (es. ` ```java `) e aggiunge le classi CSS per colorare le parole chiave (public, class, String, ecc.).

### C. Il Mondo Web (Rendering)
* **Hosting**: GitHub Pages serve i file HTML statici finali.
* **Visualizzazione**: Il browser scarica l'HTML e applica il CSS (larghezza 1500px, font, ecc.), rendendo l'articolo leggibile all'utente finale.

---

## 2. Tabella delle Responsabilità

| Componente | Chi è? | Cosa fa esattamente? |
| :--- | :--- | :--- |
| **Pandas (Python)** | Estrattore | Legge le celle dell'Excel e le trasforma in stringhe Python. |
| **Prettier (Node/NPX)** | Estetista | Prende il codice Java/JS e lo formatta con regole standard (es. tab 4). |
| **Front Matter** | Etichetta | Dice a Jekyll: "Usa questo layout e metti questo titolo". |
| **Jekyll** | Architetto | Costruisce l'intera struttura del sito unendo pezzi diversi. |
| **Liquid** | Connettore | Il linguaggio `{{ ... }}` che incolla i dati md dentro l'HTML. |
| **GitHub Pages** | Server | Distribuisce il sito online all'URL pubblico. |

---

## 3. Schema del Flusso Tecnico

1.  **EXCEL** (Dati grezzi) 
2.  ➔ `python excel_to_jekyll.py` (Logica di estrazione)
3.  ➔ `npx prettier` (Formattazione codice "al volo")
4.  ➔ **FILE .MD** (Creati in `_articoli/`)
5.  ➔ `git push` (Upload su GitHub)
6.  ➔ **JEKYLL** (Compilazione automatica su server GitHub)
7.  ➔ **HTML FINALE** (Visibile sul browser)

---

## 4. Note di Manutenzione

* **Perché il 404?** Se Jekyll trova una data futura nel file `.md`, non genera la pagina. Abbiamo risolto impostando `future: true` nel `_config.yml`.
* **Perché il codice era su una riga?** Perché veniva salvato come variabile YAML (`codice: '...'`). Spostandolo nel **Corpo** del file Markdown dopo il secondo `---`, Jekyll lo tratta come testo pre-formattato.
* **Perché la sintesi è importante?** Viene usata nell'homepage (`index.html`) per mostrare l'anteprima prima del "Leggi tutto".
