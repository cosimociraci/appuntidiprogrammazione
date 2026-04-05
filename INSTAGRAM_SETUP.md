# Guida: Pubblicazione automatica caroselli Instagram

## Struttura dei file

```
repo/
├── publish.py                          ← script di pubblicazione
├── generazione_slide/
│   └── calendario_instagram.csv        ← calendario post
│   └── 2026-04-05-argon2/              ← esempio cartella carosello
│       ├── 1.png
│       ├── 2.png
│       └── 3.png
└── .github/
    └── workflows/
        └── instagram.yml               ← workflow automatico
```

---

## 1. Formato del CSV

Il file `generazione_slide/calendario_instagram.csv` deve avere
questa intestazione esatta (la prima riga):

```csv
data,folder,caption,tags
```

Esempio di righe valide:

```csv
data,folder,caption,tags
2026-04-05,generazione_slide/2026-04-05-argon2,Argon2 è l'algoritmo giusto per hashare le password. Ecco perché MD5 e SHA256 non bastano contro le GPU moderne.,"#java #security #backend #springboot #programmazione"
2026-04-07,generazione_slide/2026-04-07-jvm,Come funziona la JVM internamente? Thread, heap e garbage collector spiegati con codice reale.,"#java #jvm #backend #dev"
```

**Note importanti sul CSV:**
- Il formato della colonna `data` deve essere `YYYY-MM-DD`
- La colonna `folder` contiene il path relativo alla root del repo
- Se `caption` o `tags` contengono virgole, racchiudili tra `"virgolette doppie"`
- I tag vanno nella colonna `tags`, separati da spazi, con il `#`

---

## 2. Aggiungere i secrets GitHub

I secrets sono credenziali cifrate che GitHub inietta come variabili
d'ambiente durante i workflow, senza mai mostrarle nei log.

### Procedura passo per passo

**1.** Vai sul tuo repository su GitHub

**2.** Clicca su **Settings** (tab in alto a destra della repo)

**3.** Nel menu laterale sinistro, sotto **Security**, clicca su
   **Secrets and variables** → **Actions**

**4.** Clicca su **New repository secret** (pulsante verde in alto a destra)

**5.** Aggiungi il primo secret:
   - **Name:** `IG_USERNAME`
   - **Secret:** il tuo username Instagram (senza la @)
   - Clicca **Add secret**

**6.** Clicca di nuovo **New repository secret** e aggiungi:
   - **Name:** `IG_PASSWORD`
   - **Secret:** la tua password Instagram
   - Clicca **Add secret**

Al termine vedrai entrambi i secrets nella lista. GitHub non mostra
mai il valore dopo il salvataggio — se devi cambiare una password
puoi sovrascrivere il secret con **Update**.

---

## 3. Abilitare il workflow

Il file `.github/workflows/instagram.yml` viene rilevato
automaticamente da GitHub Actions al primo push.

Verifica che Actions sia abilitato per il tuo repo:
**Settings** → **Actions** → **General** → seleziona
**Allow all actions and reusable workflows** → **Save**

---

## 4. Test prima di andare live

Prima di aspettare le 09:00 UTC, testa manualmente:

**1.** Vai su **Actions** nella tab del tuo repo

**2.** Nel menu laterale, clicca su **Pubblica Carosello Instagram**

**3.** Clicca su **Run workflow** (pulsante grigio a destra)

**4.** Nelle opzioni che appaiono, imposta **Dry run** su `true`

**5.** Clicca **Run workflow**

Il workflow girerà e nei log vedrai cosa avrebbe pubblicato,
senza effettuare nessuna chiamata reale a Instagram.

Quando sei soddisfatto del test, esegui di nuovo con **Dry run = false**
per la pubblicazione reale.

---

## 5. Risoluzione problemi comuni

| Problema | Causa probabile | Soluzione |
|---|---|---|
| `Login fallito` | Password errata o 2FA attivo | Disabilita 2FA sull'account IG o usa una password per app |
| `Cartella non trovata` | Path errato nel CSV | Verifica che il `folder` nel CSV corrisponda esattamente al path nel repo |
| `Solo 1 immagine trovata` | Manca il secondo file | Instagram richiede min 2 slide per un carosello |
| `Nessun post pianificato` | Data nel CSV non coincide | Controlla che il formato sia `YYYY-MM-DD` senza spazi |
| Workflow non parte | Actions disabilitato | Vedi sezione 3 sopra |

---

## 6. Account con autenticazione a due fattori (2FA)

Se il tuo account Instagram ha il 2FA attivo, il login da script
fallirà. Le opzioni sono:

- **Opzione A (consigliata):** Crea un account Instagram secondario
  dedicato alla pubblicazione automatica, senza 2FA.
- **Opzione B:** Disabilita temporaneamente il 2FA, esegui il login
  con lo script, e riattivalo. instagrapi salva la sessione in locale
  ma in un ambiente CI stateless come GitHub Actions la sessione
  non persiste tra un run e l'altro.
