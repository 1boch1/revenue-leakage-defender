"""Unit tests for pdf_parser service."""

from pathlib import Path

import pytest

from services.pdf_parser import extract_text_from_pdf

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_extract_text_from_invoice():
    text = extract_text_from_pdf((FIXTURES_DIR / "fattura_test.pdf").read_bytes(), label="Fattura")
    assert "FATTURA" in text
    assert "INV-2024-1042" in text
    assert "TechConsult" in text
    assert "ACME Italia" in text
    assert "Consulenza Senior" in text
    assert "Formazione Team" in text
    assert "20.496,00 EUR" in text


def test_extract_text_from_contract():
    text = extract_text_from_pdf((FIXTURES_DIR / "contratto_test.pdf").read_bytes(), label="Contratto")
    assert "CONTRATTO QUADRO DI SERVIZI" in text
    assert "MSA-2023-ACME-001" in text
    assert "Art. 2 - Tariffe e corrispettivi" in text
    assert "Consulenza Senior" in text
    assert "500,00 EUR" in text
    assert "60 (sessanta) giorni" in text


def test_extract_text_empty_bytes():
    with pytest.raises(ValueError, match="vuoto"):
        extract_text_from_pdf(b"", label="Vuoto")
