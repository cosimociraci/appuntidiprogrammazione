"""
publish.py — Pubblicazione automatica caroselli Instagram.

Legge il CSV calendario_instagram.csv, controlla se oggi c'è un post
da pubblicare e lo carica su Instagram tramite instagrapi.

Variabili d'ambiente richieste:
    IG_USERNAME  → username Instagram (senza @)
    IG_PASSWORD  → password Instagram

Uso:
    python publish.py
    python publish.py --dry-run   # Simula senza pubblicare
"""

import os
import sys
import csv
import glob
import argparse
import logging
from datetime import date
from pathlib import Path

# ---------------------------------------------------------------
# Configurazione logging: voglio output leggibile nei log
# di GitHub Actions, con timestamp e livello ben visibili.
# ---------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------
# Costanti
# ---------------------------------------------------------------
CSV_PATH     = Path("generazione_slide/calendario_instagram.csv")
DATE_FORMAT  = "%Y-%m-%d"   # Formato atteso nella colonna `data`
IMG_PATTERN  = "*.png"       # Cerco PNG; estendo a JPG se serve


def parse_args() -> argparse.Namespace:
    """
    Definisco --dry-run per poter testare il workflow senza
    effettuare login o chiamate reali alle API di Instagram.
    """
    parser = argparse.ArgumentParser(
        description="Pubblica il carosello Instagram pianificato per oggi."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simula l'esecuzione senza pubblicare nulla su Instagram.",
    )
    return parser.parse_args()


def leggi_csv(percorso: Path) -> list[dict]:
    """
    Leggo il CSV e restituisco una lista di dizionari.
    Uso DictReader per accedere alle colonne per nome, così
    l'ordine delle colonne nel file non è rilevante.
    """
    if not percorso.exists():
        log.error(f"CSV non trovato: {percorso}")
        sys.exit(1)

    with open(percorso, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        righe = list(reader)

    log.info(f"CSV letto: {len(righe)} righe trovate.")
    return righe


def trova_post_di_oggi(righe: list[dict]) -> dict | None:
    """
    Cerco la riga il cui campo `data` corrisponde a oggi.
    Converto la stringa in oggetto date per un confronto robusto
    (evito problemi con spazi o zeri iniziali mancanti).
    """
    oggi = date.today()
    log.info(f"Data odierna: {oggi.isoformat()}")

    for riga in righe:
        try:
            data_post = date.fromisoformat(riga["data"].strip())
        except (ValueError, KeyError) as e:
            log.warning(f"Riga ignorata (data non valida): {riga} — {e}")
            continue

        if data_post == oggi:
            log.info(f"Post trovato per oggi: folder='{riga['folder']}'")
            return riga

    return None


def raccogli_immagini(folder: str) -> list[Path]:
    """
    Cerco le immagini nella cartella indicata nel CSV.
    Le ordino numericamente per nome file (1.png, 2.png, …)
    usando il numero estratto dal nome come chiave di ordinamento.
    Instagram richiede almeno 2 immagini per un carosello
    e accetta al massimo 10.

    Supporto sia PNG che JPG per flessibilità futura.
    """
    cartella = Path(folder)
    if not cartella.is_dir():
        log.error(f"Cartella immagini non trovata: {cartella}")
        sys.exit(1)

    # Raccolgo PNG e JPG, poi ordino per numero nel nome file
    immagini = sorted(
        [p for p in cartella.iterdir() if p.suffix.lower() in (".png", ".jpg", ".jpeg")],
        # Estraggo la parte numerica dal nome (es. "2" da "2.png")
        # Se il nome non è numerico lo metto in fondo con float('inf')
        key=lambda p: int(p.stem) if p.stem.isdigit() else float("inf"),
    )

    if len(immagini) < 2:
        log.error(
            f"Trovate solo {len(immagini)} immagini in '{folder}'. "
            "Instagram richiede almeno 2 slide per un carosello."
        )
        sys.exit(1)

    if len(immagini) > 10:
        log.warning(
            f"Trovate {len(immagini)} immagini: Instagram accetta max 10. "
            "Uso solo le prime 10."
        )
        immagini = immagini[:10]

    log.info(f"Immagini da pubblicare ({len(immagini)}): {[str(i) for i in immagini]}")
    return immagini


def costruisci_caption(caption: str, tags: str) -> str:
    """
    Concateno caption e hashtag con una riga vuota di separazione.
    Pulisco gli spazi in eccesso da entrambi i campi.
    """
    testo   = caption.strip()
    hashtag = tags.strip()

    if hashtag:
        testo = f"{testo}\n\n{hashtag}"

    # Instagram ha un limite di 2200 caratteri per la caption
    if len(testo) > 2200:
        log.warning(
            f"Caption troppo lunga ({len(testo)} caratteri). "
            "Verrà troncata a 2200."
        )
        testo = testo[:2200]

    return testo


def pubblica_carosello(
    immagini: list[Path],
    caption: str,
    dry_run: bool = False,
) -> None:
    """
    Esegue login su Instagram e pubblica il carosello.

    Uso instagrapi invece dell'API ufficiale di Meta perché
    l'API ufficiale richiede un account Business verificato
    e un processo di approvazione; instagrapi simula il client
    mobile e non ha questi requisiti.

    Leggo le credenziali dalle variabili d'ambiente per non
    averle mai scritte nel codice o nel repo.
    """
    username = os.environ.get("IG_USERNAME", "").strip()
    password = os.environ.get("IG_PASSWORD", "").strip()

    if not username or not password:
        log.error(
            "Variabili d'ambiente IG_USERNAME e/o IG_PASSWORD mancanti. "
            "Configura i secrets nel repository GitHub."
        )
        sys.exit(1)

    if dry_run:
        log.info("=== DRY RUN: nessuna chiamata reale a Instagram ===")
        log.info(f"Username:   {username}")
        log.info(f"Immagini:   {[str(i) for i in immagini]}")
        log.info(f"Caption:\n{caption}")
        return

    # ---------------------------------------------------------------
    # Import instagrapi solo quando serve: se non è installato
    # e siamo in dry-run non voglio un ImportError fuorviante.
    # ---------------------------------------------------------------
    try:
        from instagrapi import Client
    except ImportError:
        log.error("instagrapi non installato. Esegui: pip install instagrapi")
        sys.exit(1)

    cl = Client()

    # Imposto un delay tra le azioni per ridurre il rischio di
    # blocchi da parte dei sistemi anti-bot di Instagram.
    cl.delay_range = [2, 5]

    log.info(f"Login come @{username}…")
    try:
        cl.login(username, password)
    except Exception as e:
        log.error(f"Login fallito: {e}")
        sys.exit(1)

    log.info("Login riuscito. Carico le immagini…")

    # album_upload accetta una lista di Path e gestisce
    # internamente il caricamento in sequenza ordinata.
    try:
        media = cl.album_upload(
            paths=immagini,
            caption=caption,
        )
        log.info(f"Carosello pubblicato con successo! Media ID: {media.pk}")
    except Exception as e:
        log.error(f"Pubblicazione fallita: {e}")
        sys.exit(1)
    finally:
        # Logout esplicito: libero la sessione sul server Instagram
        # per evitare sessioni zombie che possono triggerare blocchi.
        try:
            cl.logout()
            log.info("Logout completato.")
        except Exception:
            pass  # Il logout può fallire se la sessione è già scaduta


def main() -> None:
    args    = parse_args()
    dry_run = args.dry_run

    if dry_run:
        log.info("Modalità DRY RUN attiva.")

    # 1. Leggo il CSV
    righe = leggi_csv(CSV_PATH)

    # 2. Cerco il post di oggi
    post = trova_post_di_oggi(righe)

    if post is None:
        log.info("Nessun post pianificato per oggi. Uscita.")
        # Esco con codice 0: non è un errore, è il comportamento atteso
        sys.exit(0)

    # 3. Raccolgo le immagini nell'ordine corretto
    immagini = raccogli_immagini(post["folder"])

    # 4. Costruisco la caption completa
    caption = costruisci_caption(post["caption"], post["tags"])

    # 5. Pubblico il carosello (o simulo in dry-run)
    pubblica_carosello(immagini, caption, dry_run=dry_run)


if __name__ == "__main__":
    main()