from __future__ import annotations

import io
import logging

import pdfplumber

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_bytes: bytes, label: str = "PDF") -> str:
    if not pdf_bytes:
        raise ValueError(f"Il file {label} e vuoto.")

    pages: list[str] = []

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        logger.info("[%s] %d pagine trovate.", label, len(pdf.pages))

        for i, page in enumerate(pdf.pages, 1):
            text = page.extract_text(x_tolerance=3, y_tolerance=3)
            if text:
                pages.append(f"--- Pagina {i} ---\n{text.strip()}")
            else:
                logger.warning("[%s] Pagina %d: nessun testo trovato.", label, i)

    if not pages:
        raise ValueError(f"Nessun testo estraibile da {label}.")

    result = "\n\n".join(pages)
    logger.info("[%s] Estratti %d caratteri.", label, len(result))
    return result
