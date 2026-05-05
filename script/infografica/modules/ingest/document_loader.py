# modules/ingest/document_loader.py

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class DocumentLoader:
    """
    Cosa: Carica il contenuto grezzo da PDF o Markdown.
    Come: Dispatch sul suffisso del file; per i PDF uso pdfplumber
          che gestisce bene testo multi-colonna senza introdurre
          artefatti da line-break come PyPDF2.
    Perché: Ho preferito pdfplumber a pypdf per la qualità
            dell'estrazione su documenti con tabelle e layout misti,
            che sono i più comuni nei documenti tecnici.
    """

    SUPPORTED_EXTENSIONS = {".pdf", ".md", ".txt"}

    def load(self, file_path: str) -> str:
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File non trovato: {file_path}")

        if path.suffix not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Formato non supportato: '{path.suffix}'. "
                f"Supportati: {self.SUPPORTED_EXTENSIONS}"
            )

        logger.info(f"[DocumentLoader] Carico '{path.name}' ({path.suffix})")

        if path.suffix == ".pdf":
            return self._load_pdf(path)
        else:
            # Per .md e .txt la lettura è diretta
            return self._load_text(path)

    def _load_pdf(self, path: Path) -> str:
        # Importo qui e non a livello di modulo per rendere pdfplumber
        # una dipendenza opzionale: se l'utente carica solo Markdown,
        # non ha bisogno di installarlo.
        try:
            import pdfplumber
        except ImportError:
            raise ImportError(
                "pdfplumber non installato. Esegui: pip install pdfplumber"
            )

        full_text_parts = []

        with pdfplumber.open(path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text()
                if text and text.strip():
                    full_text_parts.append(text)
                else:
                    # Pagina vuota o solo immagini: la salto con log
                    logger.debug(
                        f"[DocumentLoader] Pagina {page_num} senza testo estraibile, saltata."
                    )

        if not full_text_parts:
            raise ValueError(
                "Il PDF non contiene testo estraibile. "
                "Potrebbe essere un documento scansionato (immagine)."
            )

        # Unisco le pagine con doppio newline per preservare
        # la separazione visiva tra sezioni, utile al chunker
        # per riconoscere i boundary naturali del testo.
        return "\n\n".join(full_text_parts)

    def _load_text(self, path: Path) -> str:
        # Provo UTF-8 prima, poi latin-1 come fallback per documenti
        # italiani/europei con caratteri accentati non-UTF8.
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            logger.warning(
                f"[DocumentLoader] UTF-8 fallito per '{path.name}', "
                f"riprovo con latin-1."
            )
            return path.read_text(encoding="latin-1")